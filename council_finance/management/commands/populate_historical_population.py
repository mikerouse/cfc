"""
Management command to populate historical population data from latest_population.

This creates FinancialFigure records for population for each year where they don't exist,
using the council's latest_population as the initial value.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from council_finance.models import Council, DataField, FinancialFigure, FinancialYear
from council_finance.utils.population_year import set_population_for_year


class Command(BaseCommand):
    help = 'Populate historical population data for all councils and years'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--council',
            type=str,
            help='Process only specific council by slug'
        )
        parser.add_argument(
            '--year',
            type=str,
            help='Process only specific year by label'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing population data'
        )
    
    def handle(self, *args, **options):
        """
        Populate historical population data where missing.
        Initially copies latest_population to all years as starting point.
        """
        dry_run = options['dry_run']
        overwrite = options['overwrite']
        
        # Ensure population field exists
        pop_field, created = DataField.objects.get_or_create(
            slug='population',
            defaults={
                'name': 'Population',
                'content_type': 'integer',
                'category': 'characteristic',
                'description': 'Number of residents in the council area'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created population DataField')
            )
        
        # Filter councils if specified
        councils = Council.objects.all()
        if options['council']:
            councils = councils.filter(slug=options['council'])
        
        # Filter years if specified
        years = FinancialYear.objects.all().order_by('start_date')
        if options['year']:
            years = years.filter(label=options['year'])
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for council in councils:
                if not council.latest_population:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {council.name} - no latest_population"
                        )
                    )
                    continue
                
                for year in years:
                    # Check if population already exists for this year
                    existing = FinancialFigure.objects.filter(
                        council=council,
                        year=year,
                        field=pop_field
                    ).first()
                    
                    if existing and not overwrite:
                        skipped_count += 1
                        continue
                    
                    if dry_run:
                        if existing:
                            self.stdout.write(
                                f"Would update population for {council.name} "
                                f"{year.label} from {existing.value} to "
                                f"{council.latest_population}"
                            )
                            updated_count += 1
                        else:
                            self.stdout.write(
                                f"Would create population for {council.name} "
                                f"{year.label}: {council.latest_population}"
                            )
                            created_count += 1
                    else:
                        # Create or update the population figure
                        if existing:
                            existing.value = str(council.latest_population)
                            existing.save()
                            updated_count += 1
                            self.stdout.write(
                                f"Updated population for {council.name} "
                                f"{year.label} to {council.latest_population}"
                            )
                        else:
                            set_population_for_year(
                                council, year, council.latest_population
                            )
                            created_count += 1
                            self.stdout.write(
                                f"Created population for {council.name} "
                                f"{year.label}: {council.latest_population}"
                            )
            
            if dry_run:
                # Rollback the transaction in dry run mode
                transaction.set_rollback(True)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"Created: {created_count}\n"
                f"Updated: {updated_count}\n"
                f"Skipped: {skipped_count}\n"
                f"{'(DRY RUN - no changes made)' if dry_run else ''}"
            )
        )