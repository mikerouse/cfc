"""
Management command to check leaderboard data health and populate missing calculated fields.

This command validates that all required data exists for leaderboard functionality,
including checking field mappings, financial year settings, and calculated field values.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import logging

from council_finance.models import (
    DataField, 
    FinancialYear, 
    FinancialFigure, 
    Council,
    CouncilCharacteristic
)
from council_finance.services.leaderboard_service import LeaderboardService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check leaderboard data health and fix common issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix detected issues',
        )
        parser.add_argument(
            '--populate-calculated',
            action='store_true',
            help='Populate missing calculated fields like total-debt',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        self.fix_mode = options['fix']
        self.populate_calculated = options['populate_calculated']
        self.verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('Leaderboard Health Check')
        )
        self.stdout.write('=' * 50)
        
        issues_found = 0
        issues_fixed = 0
        
        # 1. Check financial year settings
        year_issues, year_fixes = self.check_financial_years()
        issues_found += year_issues
        issues_fixed += year_fixes
        
        # 2. Check DataField mappings
        field_issues, field_fixes = self.check_field_mappings()
        issues_found += field_issues
        issues_fixed += field_fixes
        
        # 3. Check population data for per capita calculations
        pop_issues, pop_fixes = self.check_population_data()
        issues_found += pop_issues
        issues_fixed += pop_fixes
        
        # 4. Check calculated fields
        calc_issues, calc_fixes = self.check_calculated_fields()
        issues_found += calc_issues
        issues_fixed += calc_fixes
        
        # 5. Test all leaderboard categories
        test_issues = self.test_leaderboard_categories()
        issues_found += test_issues
        
        # Summary
        self.stdout.write('\n' + '=' * 50)
        if issues_found == 0:
            self.stdout.write(
                self.style.SUCCESS('All leaderboard health checks passed!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Found {issues_found} issues')
            )
            if self.fix_mode:
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed {issues_fixed} issues')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Run with --fix to automatically resolve issues')
                )

    def check_financial_years(self):
        """Check financial year configuration."""
        self.stdout.write('\n1. Checking financial year settings...')
        
        issues = 0
        fixes = 0
        
        # Check if any year is marked as current
        current_year = FinancialYear.objects.filter(is_current=True).first()
        
        if not current_year:
            issues += 1
            self.stdout.write(
                self.style.WARNING('  [X] No financial year is marked as current')
            )
            
            if self.fix_mode:
                # Set the most recent year as current
                latest_year = FinancialYear.objects.order_by('-start_date').first()
                if latest_year:
                    latest_year.is_current = True
                    latest_year.save()
                    fixes += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] Set {latest_year.label} as current year')
                    )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'  [OK] Current year: {current_year.label}')
            )
            
        return issues, fixes

    def check_field_mappings(self):
        """Check that all required DataField slugs exist."""
        self.stdout.write('\n2. Checking DataField mappings...')
        
        issues = 0
        fixes = 0
        
        # Required fields for leaderboards
        required_fields = {
            'total-debt': 'Total Debt',
            'interest-paid': 'Interest Paid', 
            'current-liabilities': 'Current Liabilities',
            'long-term-liabilities': 'Long-term Liabilities',
            'usable-reserves': 'Usable Reserves',
            'council-tax-income': 'Council Tax Income',
            'finance-leases-pfi-liabilities': 'Finance Leases / PFI Liabilities',
            'population': 'Population'
        }
        
        for slug, expected_name in required_fields.items():
            field = DataField.objects.filter(slug=slug).first()
            
            if not field:
                issues += 1
                self.stdout.write(
                    self.style.WARNING(f'  [X] Missing field: {slug}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] Found: {slug} -> {field.name}')
                )
                
        return issues, fixes

    def check_population_data(self):
        """Check population data availability for per capita calculations."""
        self.stdout.write('\n3. Checking population data...')
        
        issues = 0
        fixes = 0
        
        try:
            pop_field = DataField.objects.get(slug='population')
            councils_with_pop = CouncilCharacteristic.objects.filter(
                field=pop_field,
                value__isnull=False
            ).count()
            
            total_councils = Council.objects.count()
            
            if councils_with_pop < total_councils:
                issues += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  [X] Only {councils_with_pop}/{total_councils} councils have population data'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [OK] All {councils_with_pop} councils have population data'
                    )
                )
                
        except DataField.DoesNotExist:
            issues += 1
            self.stdout.write(
                self.style.WARNING('  [X] Population field not found')
            )
            
        return issues, fixes

    def check_calculated_fields(self):
        """Check and optionally populate calculated fields."""
        self.stdout.write('\n4. Checking calculated fields...')
        
        issues = 0
        fixes = 0
        
        try:
            total_debt_field = DataField.objects.get(slug='total-debt')
            current_year = FinancialYear.objects.filter(is_current=True).first()
            
            if not current_year:
                self.stdout.write(
                    self.style.WARNING('  [X] No current year set, skipping calculated fields')
                )
                return 1, 0
                
            # Check each council
            councils = Council.objects.all()
            missing_count = 0
            
            for council in councils:
                total_debt_exists = FinancialFigure.objects.filter(
                    council=council,
                    year=current_year,
                    field=total_debt_field
                ).exists()
                
                if not total_debt_exists:
                    missing_count += 1
                    
                    if self.populate_calculated or self.fix_mode:
                        # Calculate total debt
                        total = self.calculate_total_debt(council, current_year)
                        
                        if total > 0:
                            FinancialFigure.objects.create(
                                council=council,
                                year=current_year,
                                field=total_debt_field,
                                value=total
                            )
                            fixes += 1
                            if self.verbose:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'    [OK] Created total debt for {council.name}: £{total:,}'
                                    )
                                )
            
            if missing_count > 0:
                issues += missing_count
                if not (self.populate_calculated or self.fix_mode):
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [X] {missing_count} councils missing total debt calculations'
                        )
                    )
                    self.stdout.write(
                        '    Run with --populate-calculated to fix'
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS('  [OK] All councils have total debt calculations')
                )
                
        except DataField.DoesNotExist:
            issues += 1
            self.stdout.write(
                self.style.WARNING('  [X] Total debt field not found')
            )
            
        return issues, fixes

    def calculate_total_debt(self, council, year):
        """Calculate total debt for a council using the formula."""
        total = Decimal('0')
        
        # Formula: current-liabilities + long-term-liabilities + finance-leases-pfi-liabilities
        component_slugs = [
            'current-liabilities',
            'long-term-liabilities', 
            'finance-leases-pfi-liabilities'
        ]
        
        for slug in component_slugs:
            figure = FinancialFigure.objects.filter(
                council=council,
                year=year,
                field__slug=slug
            ).first()
            
            if figure and figure.value:
                total += figure.value
                
        return total

    def test_leaderboard_categories(self):
        """Test all leaderboard categories to ensure they work."""
        self.stdout.write('\n5. Testing leaderboard categories...')
        
        issues = 0
        service = LeaderboardService()
        
        for category_key, category_info in service.CATEGORIES.items():
            try:
                data = service.get_leaderboard(category_key)
                
                if data is None:
                    issues += 1
                    self.stdout.write(
                        self.style.WARNING(f'  [X] {category_key}: No data returned')
                    )
                elif len(data.entries) == 0:
                    # This might be OK for some categories
                    self.stdout.write(
                        self.style.WARNING(f'  [WARN] {category_key}: No entries (may be expected)')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  [OK] {category_key}: {len(data.entries)} entries'
                        )
                    )
                    
            except Exception as e:
                issues += 1
                self.stdout.write(
                    self.style.ERROR(f'  [X] {category_key}: Error - {str(e)}')
                )
                
        return issues