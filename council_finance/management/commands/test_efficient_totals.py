"""
Test the efficient site totals calculation approach.

Usage:
    python manage.py test_efficient_totals                    # Just test the efficient approach
    python manage.py test_efficient_totals --replace          # Test and replace if successful
    python manage.py test_efficient_totals --debt-per-capita  # Test debt per capita calculation
"""

import time
from django.core.management.base import BaseCommand
from council_finance.agents.efficient_site_totals import EfficientSiteTotalsAgent


class Command(BaseCommand):
    help = 'Test the efficient site totals calculation (old school SQL approach)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace the old SiteTotalsAgent if test is successful'
        )
        parser.add_argument(
            '--debt-per-capita',
            action='store_true', 
            help='Test debt per capita calculation specifically'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing Efficient Site Totals Agent - The Old School Way')
        )
        self.stdout.write('=' * 70)
        
        if options['debt_per_capita']:
            self._test_debt_per_capita()
            return
        
        # Test the efficient approach
        start_time = time.time()
        
        try:
            agent = EfficientSiteTotalsAgent()
            count = agent.run()
            elapsed = time.time() - start_time
            
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'SUCCESS SUCCESS: Calculated {count} counters in {elapsed:.2f} seconds')
            )
            
            # Show the efficiency gain
            estimated_old_time = count * 5  # Old approach ~5 seconds per counter
            if elapsed < estimated_old_time:
                speedup = estimated_old_time / elapsed
                self.stdout.write(
                    self.style.SUCCESS(f'SPEEDUP Estimated speedup: {speedup:.0f}x faster than old approach')
                )
            
            # Test debt per capita as well
            self.stdout.write('')
            self._test_debt_per_capita()
            
            # Offer to replace if requested
            if options['replace']:
                self._replace_old_agent()
            else:
                self.stdout.write('')
                self.stdout.write('TIP To replace the old agent, run with --replace flag')
                
        except Exception as e:
            elapsed = time.time() - start_time
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(f'FAILED FAILED after {elapsed:.2f}s: {e}')
            )
            
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('COMPLETE Test complete')

    def _test_debt_per_capita(self):
        """Test debt per capita calculation specifically."""
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('DEBT Testing Debt Per Capita Calculation')
        )
        self.stdout.write('-' * 50)
        
        try:
            agent = EfficientSiteTotalsAgent()
            
            # Test the calculation
            debt_per_capita = agent._total_debt_per_capita_calculation()
            
            if debt_per_capita > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'SUCCESS UK Council Debt Per Capita: £{debt_per_capita:,.0f} per person')
                )
                
                # Some context
                if debt_per_capita > 10000:
                    self.stdout.write('INFO That\'s quite high - over £10k per person!')
                elif debt_per_capita > 5000:
                    self.stdout.write('INFO Significant debt burden - over £5k per person')
                else:
                    self.stdout.write('INFO Relatively manageable debt levels')
                    
            else:
                self.stdout.write(
                    self.style.WARNING('WARNING  Debt per capita calculation returned 0 - check population data')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'FAILED Debt per capita test failed: {e}')
            )

    def _replace_old_agent(self):
        """Replace the old SiteTotalsAgent with the efficient version."""
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('REPLACE Replacing old SiteTotalsAgent with efficient version...')
        )
        
        try:
            # Import and replace
            import council_finance.agents.site_totals_agent as old_module
            old_module.SiteTotalsAgent = EfficientSiteTotalsAgent
            
            self.stdout.write(
                self.style.SUCCESS('SUCCESS Successfully replaced SiteTotalsAgent!')
            )
            self.stdout.write('SUCCESS The homepage should now load much faster!')
            self.stdout.write('TIP Run: python manage.py warmup_counter_cache')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'FAILED Failed to replace agent: {e}')
            )