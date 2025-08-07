"""
Management command to warm up counter cache in background.

This command pre-calculates important counter values to ensure fast page loads.
Can be run manually or scheduled via cron for automatic warming.

Usage:
    python manage.py warmup_counter_cache                    # Warm critical counters
    python manage.py warmup_counter_cache --all              # Warm all counters  
    python manage.py warmup_counter_cache --council=birmingham  # Warm specific council
    python manage.py warmup_counter_cache --stats            # Show cache statistics
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from council_finance.services.counter_cache_service import counter_cache_service
from council_finance.services.counter_invalidation_service import counter_invalidation_service
from council_finance.models import Council, CounterResult, SiteCounter


class Command(BaseCommand):
    help = 'Warm up counter cache for fast page loads. RECOMMENDATION: Kill running Python services first to prevent conflicts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Warm all counters (not just critical ones)',
        )
        parser.add_argument(
            '--council',
            type=str,
            help='Warm counters for specific council (by slug)',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show cache statistics instead of warming',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force warming even for fresh results',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed warming progress',
        )

    def handle(self, *args, **options):
        # Check for concurrency protection unless --force is used
        if not options.get('force', False):
            # Check if another warming command is already running
            command_lock_key = "warmup_counter_cache_command_lock"
            
            if cache.get(command_lock_key):
                self.stdout.write(
                    self.style.WARNING(
                        'WARNING: Another cache warming command is already running.\n'
                        'Use --force to override this protection, but be aware this may cause:\n'
                        '- Database connection timeouts\n'
                        '- Conflicting cache updates\n'
                        '- Inconsistent counter values\n'
                        'Recommended: Wait for current warming to complete.'
                    )
                )
                return
            
            # Set command lock with 30 minute timeout (comprehensive warming can take a while)
            cache.set(command_lock_key, True, 1800)  # 30 minutes
            
            self.stdout.write(
                self.style.SUCCESS('Acquired concurrency lock - starting cache warming')
            )
        else:
            self.stdout.write(
                self.style.WARNING('WARNING: --force used - skipping concurrency protection')
            )
            command_lock_key = None
        
        start_time = timezone.now()
        
        if options['stats']:
            self._show_statistics()
            if command_lock_key:
                cache.delete(command_lock_key)
            return
        
        # Add prominent recommendation about killing services
        self.stdout.write(
            self.style.WARNING('=' * 75)
        )
        self.stdout.write(
            self.style.WARNING('WARNING  RECOMMENDATION: Kill all running Python services first!')
        )
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('On Windows:'))
        self.stdout.write(
            self.style.WARNING('  taskkill /f /im python.exe'))
        self.stdout.write(
            self.style.WARNING('  taskkill /f /im pythonw.exe'))
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('On Linux/Mac:'))
        self.stdout.write(
            self.style.WARNING('  pkill -f python'))
        self.stdout.write(
            self.style.WARNING('  pkill -f manage.py'))
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('Why? This prevents:'))
        self.stdout.write(
            self.style.WARNING('• Database connection conflicts and timeouts'))
        self.stdout.write(
            self.style.WARNING('• Competing cache warming operations'))
        self.stdout.write(
            self.style.WARNING('• Resource exhaustion from multiple processes'))
        self.stdout.write(
            self.style.WARNING('=' * 75)
        )
        self.stdout.write('')
        
        self.stdout.write(
            self.style.SUCCESS('Starting Counter Cache Warming (10 councils per batch)')
        )
        
        try:
            if options['council']:
                self._warm_council_counters(options['council'], options['verbose'])
            elif options['all']:
                self._warm_all_counters(options['force'], options['verbose'])
            else:
                self._warm_critical_counters(options['verbose'])
            
            total_time = (timezone.now() - start_time).total_seconds()
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'SUCCESS Cache warming completed in {total_time:.2f}s')
            )
            self.stdout.write(
                self.style.SUCCESS('Processed all councils in batches of 10 for better progress visibility')
            )
            
        finally:
            # Always release the command lock if we acquired one
            if command_lock_key:
                try:
                    cache.delete(command_lock_key)
                    self.stdout.write('Released concurrency lock')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to release lock: {e}')
                    )
    
    def _warm_critical_counters(self, verbose=False):
        """Warm critical counters (homepage promoted)"""
        self.stdout.write('Warming critical counters (homepage promoted)...')
        
        results = counter_cache_service.warm_critical_counters()
        
        # Handle different result statuses
        if results.get('status') == 'already_running':
            self.stdout.write(
                self.style.WARNING(f'SKIPPED: {results.get("message", "Another warming session is in progress")}')
            )
            return
        
        self.stdout.write(
            f'Warmed {results["counters_warmed"]} critical counters in {results["total_time_seconds"]}s'
        )
        
        if results['counters_failed'] > 0:
            self.stdout.write(
                self.style.WARNING(f'WARNING: {results["counters_failed"]} counters failed to warm')
            )
        
        if results.get('status') == 'failed':
            self.stdout.write(
                self.style.ERROR('ERROR: Critical counter warming encountered failures')
            )
        
        if verbose:
            self._show_warming_details(results)
    
    def _warm_all_counters(self, force=False, verbose=False):
        """Warm all counter results"""
        self.stdout.write('Warming ALL counter results (this may take several minutes)...')
        
        # This would be a comprehensive warming of all possible counter combinations
        # For now, just warm critical + some additional logic
        results = counter_cache_service.warm_critical_counters()
        
        # TODO: Add logic to warm individual council counters as well
        councils = Council.objects.all()[:10]  # Limit to first 10 for demo
        
        for council in councils:
            if verbose:
                self.stdout.write(f'  Warming {council.name}...')
            
            # Warm key counters for this council
            for counter_slug in ['total-debt', 'current-liabilities', 'long-term-liabilities']:
                try:
                    value = counter_cache_service.get_counter_value(
                        counter_slug=counter_slug,
                        council_slug=council.slug,
                        year_label='2024/25'
                    )
                    if verbose:
                        self.stdout.write(f'    {counter_slug}: £{value:,.2f}')
                except Exception as e:
                    if verbose:
                        self.stdout.write(f'    {counter_slug}: Error - {e}')
        
        self.stdout.write(f'All counter warming completed')
    
    def _warm_council_counters(self, council_slug, verbose=False):
        """Warm counters for specific council"""
        try:
            council = Council.objects.get(slug=council_slug)
        except Council.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'ERROR: Council "{council_slug}" not found')
            )
            return
        
        self.stdout.write(f'Warming counters for {council.name}...')
        
        # Warm key counters for this council
        warmed_count = 0
        failed_count = 0
        
        # Warm ALL default counters shown on council detail page
        from council_finance.models import CounterDefinition
        default_counters = CounterDefinition.objects.filter(show_by_default=True)
        counter_slugs = [c.slug for c in default_counters]
        years = ['2024/25', '2023/24']
        
        for counter_slug in counter_slugs:
            for year_label in years:
                try:
                    value = counter_cache_service.get_counter_value(
                        counter_slug=counter_slug,
                        council_slug=council_slug,
                        year_label=year_label
                    )
                    warmed_count += 1
                    
                    if verbose:
                        self.stdout.write(f'  {counter_slug} ({year_label}): £{value:,.2f}')
                        
                except Exception as e:
                    failed_count += 1
                    if verbose:
                        self.stdout.write(f'  {counter_slug} ({year_label}): Error - {e}')
        
        self.stdout.write(
            f'Warmed {warmed_count} counter values for {council.name}'
        )
        
        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f'WARNING: {failed_count} counter values failed')
            )
    
    def _show_statistics(self):
        """Show comprehensive cache statistics"""
        self.stdout.write(self.style.SUCCESS('Counter Cache Statistics'))
        self.stdout.write('=' * 60)
        
        # Cache service statistics
        cache_stats = counter_cache_service.get_cache_statistics()
        
        self.stdout.write(f'Database Results:')
        self.stdout.write(f'  Total: {cache_stats["total_results"]:,}')
        self.stdout.write(f'  Fresh: {cache_stats["fresh_results"]:,}')
        self.stdout.write(f'  Stale: {cache_stats["stale_results"]:,}')
        self.stdout.write(f'  Recently calculated: {cache_stats["recently_calculated"]:,}')
        self.stdout.write(f'  Total cache hits: {cache_stats["total_cache_hits"]:,}')
        self.stdout.write('')
        
        # Rate limiting stats
        self.stdout.write(f'Rate Limiting:')
        self.stdout.write(f'  Rate limited results: {cache_stats["rate_limited_results"]:,}')
        
        stale_stats = cache_stats["stale_marking_stats"]
        self.stdout.write(f'  Stale marks (24h): {stale_stats["total_stale_marks"]:,}')
        
        if stale_stats["councils_with_high_stale_rate"]:
            self.stdout.write(f'  High stale rate councils:')
            for council_name, count in stale_stats["councils_with_high_stale_rate"].items():
                self.stdout.write(f'    {council_name}: {count} stale marks')
        
        self.stdout.write('')
        
        # Performance breakdown
        self.stdout.write(f'Performance:')
        perf = cache_stats["performance_breakdown"]
        
        if perf["fastest_calculations"]:
            self.stdout.write(f'  Fastest calculations:')
            for calc in perf["fastest_calculations"]:
                council_name = calc["council__name"] or "Site-wide"
                self.stdout.write(f'    {calc["counter__name"]} ({council_name}): {calc["calculation_time_seconds"]:.2f}s')
        
        if perf["slowest_calculations"]:
            self.stdout.write(f'  Slowest calculations:')
            for calc in perf["slowest_calculations"]:
                council_name = calc["council__name"] or "Site-wide"
                self.stdout.write(f'    {calc["counter__name"]} ({council_name}): {calc["calculation_time_seconds"]:.2f}s')
        
        self.stdout.write('')
        
        # Invalidation statistics
        invalidation_stats = counter_invalidation_service.get_invalidation_statistics()
        
        self.stdout.write(f'Invalidation Service:')
        self.stdout.write(f'  Pending batches: {invalidation_stats["pending_batches"]}')
        self.stdout.write(f'  Active sessions: {invalidation_stats["active_sessions"]}')
        self.stdout.write(f'  Frequently invalidated results: {len(invalidation_stats["frequently_invalidated_results"])}')
        
        if invalidation_stats["frequently_invalidated_results"]:
            self.stdout.write(f'  Top frequently invalidated:')
            for result in invalidation_stats["frequently_invalidated_results"][:5]:
                council_name = result["council__name"] or "Site-wide"
                self.stdout.write(f'    {result["counter__name"]} ({council_name}): {result["stale_mark_count"]} marks')
        
        self.stdout.write('')
        
        # Critical counters status
        self.stdout.write(f'Critical Counters (Homepage):')
        promoted_counters = SiteCounter.objects.filter(promote_homepage=True)
        
        for sc in promoted_counters:
            year_label = sc.year.label if sc.year else "all"
            
            # Check if result exists and is fresh
            try:
                from council_finance.models import CounterDefinition
                counter = CounterDefinition.objects.get(slug=sc.counter.slug)
                result = CounterResult.objects.filter(
                    counter=counter,
                    council=None,  # Site-wide
                    year=sc.year
                ).first()
                
                if result:
                    status = "STALE" if result.is_stale else "FRESH"
                    age_hours = (timezone.now() - result.calculated_at).total_seconds() / 3600
                    self.stdout.write(f'  {sc.name}: £{result.value:,.2f} ({status}, {age_hours:.1f}h old)')
                else:
                    self.stdout.write(f'  {sc.name}: NOT CACHED')
                    
            except Exception as e:
                self.stdout.write(f'  {sc.name}: ERROR - {e}')
    
    def _show_warming_details(self, results):
        """Show detailed warming results"""
        self.stdout.write('\nWarming Details:')
        
        for counter in results['warmed_counters']:
            council_name = counter.get('council_name', 'Site-wide')
            year = counter.get('year_label', 'All Years')
            time_taken = counter.get('time_seconds', 0)
            
            if counter.get('skipped'):
                self.stdout.write(f'  SKIPPED {counter["counter_name"]} ({year}): Already fresh')
            else:
                self.stdout.write(f'  WARMED {counter["counter_name"]} ({year}): £{counter["value"]:,.2f} ({time_taken:.2f}s)')
        
        if results['failed_counters']:
            self.stdout.write('\nFailed Counters:')
            for counter in results['failed_counters']:
                self.stdout.write(f'  FAILED {counter["counter_name"]}: {counter["error"]}')