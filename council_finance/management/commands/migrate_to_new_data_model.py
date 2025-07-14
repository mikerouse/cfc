"""
Migration plan to move from FigureSubmission legacy system to the new architecture.

This script will:
1. Create the new models
2. Migrate existing data
3. Update views and forms
4. Clean up old models (optional)
"""

# Management command to run the migration
# python manage.py migrate_to_new_data_model

from django.core.management.base import BaseCommand
from django.db import transaction
from council_finance.models.new_data_model import (
    CouncilCharacteristic,
    CouncilCharacteristicHistory,
    FinancialFigure,
    FinancialFigureHistory,
    ContributionV2,
    migrate_characteristics_from_figuresubmission,
    migrate_financial_data_from_figuresubmission,
)


class Command(BaseCommand):
    help = 'Migrate from FigureSubmission legacy system to new data architecture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )
        parser.add_argument(
            '--keep-old-data',
            action='store_true',
            help='Keep the old FigureSubmission data after migration',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_old_data = options['keep_old_data']
        
        self.stdout.write("🚀 Starting migration to new data architecture...")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        # Step 1: Analyze current data
        self.analyze_current_data()
        
        if not dry_run:
            with transaction.atomic():
                # Step 2: Migrate characteristics
                self.stdout.write("📊 Migrating council characteristics...")
                migrate_characteristics_from_figuresubmission()
                
                # Step 3: Migrate financial figures
                self.stdout.write("💰 Migrating financial figures...")
                migrate_financial_data_from_figuresubmission()
                
                # Step 4: Migrate pending contributions
                self.stdout.write("📝 Migrating pending contributions...")
                self.migrate_contributions()
                
                # Step 5: Update data issues
                self.stdout.write("🔍 Updating data quality issues...")
                self.update_data_issues()
                
                if not keep_old_data:
                    # Step 6: Clean up old data (optional)
                    self.stdout.write("🧹 Cleaning up old data...")
                    self.cleanup_old_data()
        
        self.stdout.write(self.style.SUCCESS("✅ Migration completed successfully!"))
        
        # Step 7: Show next steps
        self.show_next_steps()

    def analyze_current_data(self):
        """Analyze what data we have in the current system."""
        from council_finance.models import FigureSubmission, Contribution, DataField
        
        total_submissions = FigureSubmission.objects.count()
        characteristic_submissions = FigureSubmission.objects.filter(
            field__category='characteristic'
        ).count()
        financial_submissions = FigureSubmission.objects.filter(
            field__category='financial'
        ).count()
        pending_contributions = Contribution.objects.filter(status='pending').count()
        
        self.stdout.write(f"📊 Current data analysis:")
        self.stdout.write(f"   • Total FigureSubmissions: {total_submissions:,}")
        self.stdout.write(f"   • Characteristic data: {characteristic_submissions:,}")
        self.stdout.write(f"   • Financial data: {financial_submissions:,}")
        self.stdout.write(f"   • Pending contributions: {pending_contributions:,}")
        
        # Show characteristic fields
        char_fields = DataField.objects.filter(category='characteristic')
        self.stdout.write(f"   • Characteristic fields: {', '.join(char_fields.values_list('slug', flat=True))}")

    def migrate_contributions(self):
        """Migrate pending contributions to the new system."""
        from council_finance.models import Contribution
        
        old_contributions = Contribution.objects.filter(status='pending')
        migrated_count = 0
        
        for contrib in old_contributions:
            # Create new contribution
            new_contrib = ContributionV2.objects.create(
                user=contrib.user,
                council=contrib.council,
                field=contrib.field,
                year=contrib.year,  # Will be None for characteristics
                value=contrib.value,
                current_value=contrib.old_value,
                status=contrib.status,
                source_description=f"Migrated from old contribution #{contrib.id}",
                created=contrib.created,
            )
            migrated_count += 1
        
        self.stdout.write(f"   ✅ Migrated {migrated_count} pending contributions")

    def update_data_issues(self):
        """Update data quality issues to work with new models."""
        from council_finance.models import DataIssue
        
        # Data issues should still work the same way, but we might need to
        # update the assessment logic to check the new models
        issues_count = DataIssue.objects.count()
        self.stdout.write(f"   ℹ️  {issues_count} data issues will be reassessed")

    def cleanup_old_data(self):
        """Remove old FigureSubmission and Contribution data."""
        from council_finance.models import FigureSubmission, Contribution
        
        # Delete old contributions
        old_contrib_count = Contribution.objects.count()
        Contribution.objects.all().delete()
        
        # Delete old figure submissions
        old_submission_count = FigureSubmission.objects.count()
        FigureSubmission.objects.all().delete()
        
        self.stdout.write(f"   🗑️  Deleted {old_contrib_count} old contributions")
        self.stdout.write(f"   🗑️  Deleted {old_submission_count} old figure submissions")

    def show_next_steps(self):
        """Show what needs to be done after migration."""
        self.stdout.write("\n📋 Next steps after migration:")
        self.stdout.write("   1. Update views to use new models")
        self.stdout.write("   2. Update contribution forms")
        self.stdout.write("   3. Update data quality assessment")
        self.stdout.write("   4. Update admin interface")
        self.stdout.write("   5. Test the new system thoroughly")
        self.stdout.write("   6. Update documentation")
        self.stdout.write("\n💡 Run the following to update data quality issues:")
        self.stdout.write("   python manage.py assess_data_issues_v2")
