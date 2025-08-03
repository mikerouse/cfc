"""
Django management command to warm up AI factoid cache for popular councils.

This command can be run via cron to proactively warm the cache for councils
that are frequently accessed, improving user experience.

Usage:
    python manage.py warmup_popular_councils
    python manage.py warmup_popular_councils --priority=1  # Only high priority
    python manage.py warmup_popular_councils --force       # Force all schedules
    python manage.py warmup_popular_councils --dry-run     # Show what would be done
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg
from django.core.cache import cache

from council_finance.models import (
    Council, AIUsageLog, CacheWarmupSchedule, PerformanceAlert
)
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Warm up AI factoid cache for popular councils based on usage patterns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--priority',
            type=int,
            choices=[1, 2, 3],
            help='Only warm councils with this priority level (1=High, 2=Medium, 3=Low)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force warmup regardless of schedule timing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually warming caches'
        )
        parser.add_argument(
            '--create-schedules',
            action='store_true',
            help='Create warmup schedules for councils based on recent usage'
        )
        parser.add_argument(
            '--max-councils',
            type=int,
            default=20,
            help='Maximum number of councils to warm up in one run'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        self.verbosity = options['verbosity']
        self.dry_run = options['dry_run']
        
        if options['create_schedules']:
            self.create_schedules()
        else:
            self.warmup_councils(
                priority=options.get('priority'),
                force=options['force'],
                max_councils=options['max_councils']
            )

    def create_schedules(self):
        """Create or update warmup schedules based on recent usage patterns."""
        self.stdout.write("🔍 Analyzing recent usage patterns...")
        
        # Analyze last 7 days of usage
        week_ago = timezone.now() - timedelta(days=7)
        usage_stats = AIUsageLog.objects.filter(
            created_at__gte=week_ago,
            success=True
        ).values('council').annotate(
            request_count=Count('id'),
            avg_response_time=Avg('processing_time_seconds')
        ).order_by('-request_count')
        
        schedules_created = 0
        schedules_updated = 0
        
        for stats in usage_stats[:50]:  # Top 50 councils by usage
            try:
                council = Council.objects.get(id=stats['council'])
                request_count = stats['request_count']
                avg_response_time = stats['avg_response_time'] or 0
                
                # Determine priority based on usage
                if request_count >= 20:  # 20+ requests per week
                    priority = 1
                    frequency_hours = 12  # Every 12 hours
                elif request_count >= 5:  # 5-19 requests per week
                    priority = 2
                    frequency_hours = 24  # Daily
                else:  # 1-4 requests per week
                    priority = 3
                    frequency_hours = 72  # Every 3 days
                
                # Calculate popularity score
                popularity_score = min(1.0, request_count / 50.0)
                
                # Create or update schedule
                schedule, created = CacheWarmupSchedule.objects.update_or_create(
                    council=council,
                    defaults={
                        'is_active': True,
                        'priority': priority,
                        'frequency_hours': frequency_hours,
                        'avg_daily_requests': request_count / 7,
                        'last_request': timezone.now(),
                        'popularity_score': popularity_score,
                        'consecutive_failures': 0
                    }
                )
                
                # Calculate next warmup time
                schedule.calculate_next_warmup()
                schedule.save()
                
                if created:
                    schedules_created += 1
                    if self.verbosity >= 2:
                        self.stdout.write(f"  ✅ Created schedule for {council.name} (Priority {priority})")
                else:
                    schedules_updated += 1
                    if self.verbosity >= 2:
                        self.stdout.write(f"  🔄 Updated schedule for {council.name} (Priority {priority})")
                
            except Council.DoesNotExist:
                continue
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error processing council {stats['council']}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Schedule analysis complete: {schedules_created} created, {schedules_updated} updated"
            )
        )

    def warmup_councils(self, priority=None, force=False, max_councils=20):
        """Warm up councils based on their schedules."""
        self.stdout.write("🔥 Starting cache warmup process...")
        
        # Build query for councils to warm up
        query = CacheWarmupSchedule.objects.filter(is_active=True)
        
        if priority:
            query = query.filter(priority=priority)
        
        if not force:
            # Only warm councils that are due for warmup
            query = query.filter(
                next_warmup__lte=timezone.now()
            )
        
        schedules = query.select_related('council').order_by(
            'priority', '-popularity_score'
        )[:max_councils]
        
        if not schedules.exists():
            self.stdout.write("ℹ️  No councils due for warmup at this time")
            return
        
        # Initialize AI generator
        generator = AIFactoidGenerator()
        gatherer = CouncilDataGatherer()
        
        if not generator.client:
            raise CommandError("❌ OpenAI client not available - cannot perform cache warmup")
        
        warmed_count = 0
        failed_count = 0
        skipped_count = 0
        
        for schedule in schedules:
            council = schedule.council
            
            try:
                if self.dry_run:
                    self.stdout.write(f"🧪 [DRY RUN] Would warm cache for {council.name}")
                    continue
                
                self.stdout.write(f"🔥 Warming cache for {council.name}...")
                
                # Clear existing cache
                cache_key = f"ai_factoids:{council.slug}"
                cache_key_stale = f"ai_factoids_stale:{council.slug}"
                cache_key_data = f"ai_council_data:{council.slug}"
                
                cache.delete(cache_key)
                cache.delete(cache_key_stale)
                cache.delete(cache_key_data)
                
                # Gather council data
                council_data = gatherer.gather_council_data(council)
                
                # Generate AI factoids
                start_time = timezone.now()
                factoids = generator.generate_insights(
                    council_data=council_data,
                    limit=10,
                    style='news_ticker'
                )
                
                processing_time = (timezone.now() - start_time).total_seconds()
                
                # Cache the results with same strategy as main API
                response_data = {
                    'success': True,
                    'council': council.slug,
                    'factoids': factoids,
                    'generated_at': timezone.now().isoformat(),
                    'ai_model': generator.model,
                    'cache_status': 'fresh',
                    'factoid_count': len(factoids)
                }
                
                cache.set(cache_key, response_data, 604800)  # 7 days
                cache.set(cache_key_stale, response_data, 2592000)  # 30 days
                
                # Update schedule
                schedule.last_warmup = timezone.now()
                schedule.consecutive_failures = 0
                schedule.calculate_next_warmup()
                schedule.save()
                
                warmed_count += 1
                
                if self.verbosity >= 1:
                    self.stdout.write(
                        f"  ✅ {council.name}: {len(factoids)} factoids, {processing_time:.1f}s"
                    )
                
            except Exception as e:
                failed_count += 1
                
                # Update schedule failure count
                schedule.consecutive_failures += 1
                schedule.calculate_next_warmup()  # This will delay next attempt
                schedule.save()
                
                error_msg = f"❌ Failed to warm {council.name}: {str(e)}"
                self.stdout.write(self.style.ERROR(error_msg))
                
                # Create performance alert for repeated failures
                if schedule.consecutive_failures >= 3:
                    PerformanceAlert.objects.create(
                        alert_type='cache_inefficiency',
                        severity='medium',
                        title=f'Repeated Cache Warmup Failures',
                        description=f'Cache warmup for {council.name} has failed {schedule.consecutive_failures} times',
                        recommendation='Check council data quality and AI service availability',
                        council=council,
                        metric_value=schedule.consecutive_failures,
                        threshold_value=3
                    )
                
                if self.verbosity >= 2:
                    logger.error(f"Cache warmup failed for {council.slug}: {e}")
        
        # Summary
        total_processed = warmed_count + failed_count + skipped_count
        
        if self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"🧪 [DRY RUN] Would process {total_processed} councils")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Cache warmup complete: {warmed_count} warmed, {failed_count} failed"
                )
            )
            
            # Log summary for monitoring
            logger.info(
                f"Cache warmup summary: {warmed_count} successful, {failed_count} failed, "
                f"{total_processed} total processed"
            )