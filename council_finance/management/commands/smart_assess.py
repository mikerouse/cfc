"""
Management command for smart data quality assessment.

This command provides a way to run the enhanced data quality assessment 
that only flags realistic missing data based on relevant financial years.
"""

from django.core.management.base import BaseCommand
from council_finance.smart_data_quality import (
    smart_assess_data_issues, 
    get_data_collection_priorities,
    mark_financial_year_as_current
)
from council_finance.models import FinancialYear


class Command(BaseCommand):
    help = "Run smart data quality assessment that only flags realistic missing data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--set-current-year',
            type=str,
            help='Mark a specific financial year as current (e.g., "2024/25")'
        )
        parser.add_argument(
            '--show-priorities',
            action='store_true',
            help='Show data collection priorities without running assessment'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimize output'
        )

    def handle(self, *args, **options):
        if options['set_current_year']:
            year_label = options['set_current_year']
            success = mark_financial_year_as_current(year_label)
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Marked {year_label} as current financial year')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to mark {year_label} as current')
                )
                return

        if options['show_priorities']:
            priorities = get_data_collection_priorities()
            
            self.stdout.write(self.style.WARNING('📊 Data Collection Priorities:'))
            
            current_year = priorities.get('current_year')
            if current_year:
                self.stdout.write(f'Current Year: {current_year.label}')
            else:
                self.stdout.write('Current Year: None set')
            
            relevant_years = priorities.get('relevant_years', [])
            self.stdout.write(f'Relevant Years: {[y.label for y in relevant_years]}')
            
            year_stats = priorities.get('year_stats', [])
            if year_stats:
                self.stdout.write('\nYear Completeness:')
                for stat in year_stats:
                    completeness = stat['completeness']
                    submissions = stat['submissions']
                    potential = stat['potential']
                    current_flag = ' (CURRENT)' if stat['is_current'] else ''
                    self.stdout.write(
                        f'  {stat["year"].label}: {completeness:.1f}% '
                        f'({submissions}/{potential}){current_flag}'
                    )
            
            missing_chars = priorities.get('total_characteristics_missing', 0)
            missing_financial = priorities.get('total_financial_missing', 0)
            self.stdout.write(f'\nMissing Data:')
            self.stdout.write(f'  Characteristics: {missing_chars:,}')
            self.stdout.write(f'  Financial: {missing_financial:,}')
            
            if not options['quiet']:
                return  # Don't run assessment if just showing priorities

        # Run the smart assessment
        if not options['quiet']:
            self.stdout.write('🎯 Running smart data quality assessment...')
        
        count = smart_assess_data_issues()
        
        if not options['quiet']:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Smart assessment complete. Created {count:,} realistic data issues.')
            )
            
            # Show summary
            priorities = get_data_collection_priorities()
            missing_chars = priorities.get('total_characteristics_missing', 0)
            missing_financial = priorities.get('total_financial_missing', 0)
            
            self.stdout.write('\n📈 Summary:')
            self.stdout.write(f'  Missing characteristics: {missing_chars:,}')
            self.stdout.write(f'  Missing financial data: {missing_financial:,}')
            self.stdout.write(f'  Total issues: {count:,}')
            
            if missing_financial == 0 and count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        '\n💡 No financial data issues found. This means either:\n'
                        '   • No financial years are marked as "current"\n'
                        '   • All relevant years are fully populated\n'
                        '   • Only characteristic data is missing\n'
                        '\nUse --set-current-year to mark a year for data collection.'
                    )
                )
        else:
            self.stdout.write(f'{count}')
