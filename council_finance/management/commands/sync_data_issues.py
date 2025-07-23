"""
Management command to synchronize DataIssue records for missing data.

This command ensures that every council has appropriate DataIssue records
for missing characteristic and financial data, enabling the contribution
queues to work properly.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from council_finance.models import (
    Council, DataField, CouncilCharacteristic, FinancialFigure, 
    FinancialYear, DataIssue
)


class Command(BaseCommand):
    help = 'Synchronize DataIssue records for missing data to enable contribution queues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records'
        )
        parser.add_argument(
            '--council-slug',
            type=str,
            help='Only process a specific council by slug'
        )
        parser.add_argument(
            '--field-category',
            choices=['characteristic', 'financial', 'all'],
            default='all',
            help='Only process specific field category'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        council_slug = options['council_slug']
        field_category = options['field_category']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get councils to process
        councils_qs = Council.objects.all()
        if council_slug:
            councils_qs = councils_qs.filter(slug=council_slug)
            if not councils_qs.exists():
                raise CommandError(f'Council with slug "{council_slug}" not found')
        
        councils = list(councils_qs.order_by('name'))
        self.stdout.write(f'Processing {len(councils)} councils...')
        
        # Get fields to process
        fields_qs = DataField.objects.all()
        if field_category != 'all':
            fields_qs = fields_qs.filter(category=field_category)
        
        # Split into characteristic and financial fields
        characteristic_fields = list(fields_qs.filter(category='characteristic'))
        financial_fields = list(fields_qs.exclude(category='characteristic'))
        
        # Get current financial year for financial data issues
        current_year = FinancialYear.objects.filter(
            label__icontains='2024'  # Adjust as needed
        ).first()
        
        if not current_year and financial_fields:
            # Create a default current year if none exists
            current_year = FinancialYear.objects.create(label='2024-25')
            self.stdout.write(
                self.style.WARNING(f'Created default financial year: {current_year.label}')
            )
        
        total_created = 0
        total_found = 0
        
        with transaction.atomic():
            for council in councils:
                council_created = 0
                
                # Process characteristic fields
                if field_category in ['characteristic', 'all']:
                    for field in characteristic_fields:
                        # Check if council has this characteristic
                        has_characteristic = CouncilCharacteristic.objects.filter(
                            council=council, field=field
                        ).exists()
                        
                        if not has_characteristic:
                            # Check if DataIssue already exists
                            existing_issue = DataIssue.objects.filter(
                                council=council,
                                field=field,
                                issue_type='missing'
                            ).exists()
                            
                            if not existing_issue:
                                if not dry_run:
                                    DataIssue.objects.create(
                                        council=council,
                                        field=field,
                                        issue_type='missing',
                                        value=''  # Empty value for missing data
                                    )
                                council_created += 1
                                total_created += 1
                                
                                if dry_run:
                                    self.stdout.write(
                                        f'  Would create: {council.name} - {field.name} (characteristic)'
                                    )
                            else:
                                total_found += 1
                
                # Process financial fields
                if field_category in ['financial', 'all'] and current_year:
                    for field in financial_fields:
                        # Check if council has this financial figure for current year
                        has_figure = FinancialFigure.objects.filter(
                            council=council, field=field, year=current_year
                        ).exists()
                        
                        if not has_figure:
                            # Check if DataIssue already exists for this field/year
                            existing_issue = DataIssue.objects.filter(
                                council=council,
                                field=field,
                                year=current_year,
                                issue_type='missing'
                            ).exists()
                            
                            if not existing_issue:
                                if not dry_run:
                                    DataIssue.objects.create(
                                        council=council,
                                        field=field,
                                        year=current_year,
                                        issue_type='missing',
                                        value=''  # Empty value for missing data
                                    )
                                council_created += 1
                                total_created += 1
                                
                                if dry_run:
                                    self.stdout.write(
                                        f'  Would create: {council.name} - {field.name} ({current_year.label})'
                                    )
                            else:
                                total_found += 1
                
                if council_created > 0:
                    action = 'Would create' if dry_run else 'Created'
                    self.stdout.write(
                        f'{action} {council_created} DataIssues for {council.name}'
                    )
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nSummary:'))
        action = 'Would create' if dry_run else 'Created'
        self.stdout.write(f'{action}: {total_created} new DataIssue records')
        self.stdout.write(f'Already existed: {total_found} DataIssue records')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nTo actually create these records, run without --dry-run')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nDataIssue synchronization complete!')
            )