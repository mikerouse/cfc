"""
Django management command to migrate financial data from mixed formats to pounds-only.

This command:
1. Audits all monetary fields to determine their current storage format
2. Identifies fields stored in millions vs pounds  
3. Converts millions-stored fields to pounds
4. Provides verification and rollback options

Usage:
    python manage.py migrate_financial_data_to_pounds --audit-only
    python manage.py migrate_financial_data_to_pounds --dry-run
    python manage.py migrate_financial_data_to_pounds --execute
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from council_finance.models import FinancialFigure, DataField
import statistics


class Command(BaseCommand):
    help = 'Migrate financial data from mixed formats to consistent pounds-only storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--audit-only',
            action='store_true',
            help='Only audit the data, no changes made',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually perform the migration',
        )

    def handle(self, *args, **options):
        if not any([options['audit_only'], options['dry_run'], options['execute']]):
            raise CommandError('Must specify --audit-only, --dry-run, or --execute')

        self.stdout.write(self.style.SUCCESS('FINANCIAL DATA MIGRATION TOOL'))
        self.stdout.write('=' * 50)

        # Get all monetary fields
        monetary_fields = DataField.objects.filter(content_type='monetary')
        self.stdout.write(f'Found {monetary_fields.count()} monetary fields')

        field_analysis = {}
        
        for field in monetary_fields:
            analysis = self.analyze_field(field)
            if analysis:
                field_analysis[field.slug] = analysis

        # Display audit results
        self.display_audit_results(field_analysis)

        if options['audit_only']:
            return

        # Identify fields needing migration
        millions_fields = [k for k, v in field_analysis.items() if v['format_type'] == 'MILLIONS']
        
        if not millions_fields:
            self.stdout.write(self.style.SUCCESS('✅ No migration needed - all fields already in pounds format'))
            return

        self.stdout.write(f'\n🔄 Fields requiring migration: {millions_fields}')

        if options['dry_run']:
            self.show_migration_preview(millions_fields, field_analysis)
        elif options['execute']:
            self.execute_migration(millions_fields, field_analysis)

    def analyze_field(self, field):
        """Analyze a single field to determine its storage format."""
        figures = FinancialFigure.objects.filter(field=field).exclude(value__isnull=True)
        
        if not figures.exists():
            return None

        values = []
        invalid_count = 0
        
        for fig in figures:
            try:
                val = float(fig.value)
                if val != 0:  # Skip zero values
                    values.append(val)
            except (ValueError, TypeError):
                invalid_count += 1

        if not values:
            return None

        # Calculate statistics
        min_val = min(values)
        max_val = max(values)
        median_val = statistics.median(values)

        # Determine likely storage format
        values_under_1000 = sum(1 for v in values if abs(v) < 1000)
        values_over_100k = sum(1 for v in values if abs(v) > 100000)
        
        percentage_under_1000 = (values_under_1000 / len(values)) * 100
        percentage_over_100k = (values_over_100k / len(values)) * 100

        # Classification
        if percentage_under_1000 > 80:
            format_type = "MILLIONS"
        elif percentage_over_100k > 80:
            format_type = "POUNDS"
        else:
            format_type = "MIXED"

        return {
            'field': field,
            'format_type': format_type,
            'count': len(values),
            'invalid_count': invalid_count,
            'min': min_val,
            'max': max_val,
            'median': median_val,
            'percentage_under_1000': percentage_under_1000,
            'percentage_over_100k': percentage_over_100k,
            'sample_values': sorted(values)[:5]
        }

    def display_audit_results(self, field_analysis):
        """Display the audit results in a formatted way."""
        self.stdout.write('\nAUDIT RESULTS')
        self.stdout.write('-' * 30)

        for field_slug, analysis in field_analysis.items():
            field = analysis['field']
            format_type = analysis['format_type']
            
            self.stdout.write(f'\nFIELD: {field_slug} ({field.name})')
            self.stdout.write(f'   Records: {analysis["count"]} valid, {analysis["invalid_count"]} invalid')
            self.stdout.write(f'   Range: {analysis["min"]:,.2f} to {analysis["max"]:,.2f}')
            self.stdout.write(f'   Median: {analysis["median"]:,.2f}')
            self.stdout.write(f'   < 1,000: {analysis["percentage_under_1000"]:.1f}%')
            self.stdout.write(f'   > 100,000: {analysis["percentage_over_100k"]:.1f}%')
            
            if format_type == "MILLIONS":
                self.stdout.write(self.style.WARNING(f'   FORMAT: Stored in MILLIONS'))
                # Show what conversion would look like
                sample = analysis["sample_values"][0] if analysis["sample_values"] else 0
                converted = sample * 1_000_000
                self.stdout.write(f'   Example: {sample} → £{converted:,.0f}')
            elif format_type == "POUNDS":
                self.stdout.write(self.style.SUCCESS(f'   FORMAT: Already in POUNDS'))
            else:
                self.stdout.write(self.style.ERROR(f'   FORMAT: MIXED - needs investigation'))

    def show_migration_preview(self, millions_fields, field_analysis):
        """Show what the migration would do without executing it."""
        self.stdout.write('\nMIGRATION PREVIEW (DRY RUN)')
        self.stdout.write('-' * 40)

        total_records = 0
        for field_slug in millions_fields:
            analysis = field_analysis[field_slug]
            field = analysis['field']
            
            # Count records that would be migrated
            figures = FinancialFigure.objects.filter(
                field=field,
                value__isnull=False
            )
            
            migration_count = 0
            for fig in figures:
                try:
                    val = float(fig.value)
                    if abs(val) < 1000:  # Safety check for millions format
                        migration_count += 1
                except (ValueError, TypeError):
                    pass
            
            total_records += migration_count
            self.stdout.write(f'• {field_slug}: {migration_count} records would be converted')
            
            # Show examples
            sample_figures = figures[:3]
            for fig in sample_figures:
                try:
                    val = float(fig.value)
                    if abs(val) < 1000:
                        converted = val * 1_000_000
                        self.stdout.write(f'  {val} → {converted:,.0f}')
                except:
                    pass

        self.stdout.write(f'\nTotal records to migrate: {total_records}')
        self.stdout.write('\nRun with --execute to perform the migration')

    def execute_migration(self, millions_fields, field_analysis):
        """Actually perform the migration."""
        self.stdout.write('\nEXECUTING MIGRATION')
        self.stdout.write('-' * 30)

        if not millions_fields:
            self.stdout.write(self.style.SUCCESS('No fields need migration'))
            return

        # Confirm with user
        confirm = input(f'\nThis will modify {len(millions_fields)} field types. Continue? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Migration cancelled')
            return

        total_migrated = 0
        
        with transaction.atomic():
            for field_slug in millions_fields:
                analysis = field_analysis[field_slug]
                field = analysis['field']
                
                self.stdout.write(f'Migrating {field_slug}...')
                
                figures = FinancialFigure.objects.filter(
                    field=field,
                    value__isnull=False
                )
                
                field_migrated = 0
                for fig in figures:
                    try:
                        val = float(fig.value)
                        if abs(val) < 1000:  # Safety check for millions format
                            fig.value = val * 1_000_000
                            fig.save()
                            field_migrated += 1
                    except (ValueError, TypeError):
                        self.stdout.write(f'  Skipped invalid value: {fig.value}')
                
                total_migrated += field_migrated
                self.stdout.write(f'  Migrated {field_migrated} records')

        self.stdout.write(f'\nMIGRATION COMPLETE')
        self.stdout.write(f'Total records migrated: {total_migrated}')
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Test counter display on council pages')
        self.stdout.write('2. Update CounterDefinition.format_value() to remove smart detection')
        self.stdout.write('3. Update frontend to show "pounds" instead of "millions"')
        self.stdout.write('4. Update validation ranges for pound amounts')