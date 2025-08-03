"""
Django management command for intelligent sitewide factoid updates.

This command implements the 4x daily schedule with change detection,
only generating new factoids when underlying data has actually changed.

Usage:
    python manage.py update_sitewide_factoids --check-schedule    # Normal scheduled operation
    python manage.py update_sitewide_factoids --force             # Force generation regardless
    python manage.py update_sitewide_factoids --dry-run           # Show what would be done
    python manage.py update_sitewide_factoids --init-schedule     # Initialize default schedule
"""

import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.cache import cache

from council_finance.models import (
    SitewideFactoidSchedule, SitewideDataChangeLog, SitewideDataSummary,
    OptimizedFactoidCache
)
from council_finance.services.optimized_sitewide_generator import OptimizedSitewideFactoidGenerator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Intelligently update sitewide factoids based on schedule and data changes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-schedule',
            action='store_true',
            help='Check if updates are needed based on schedule and data changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation regardless of schedule or changes'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it'
        )
        parser.add_argument(
            '--init-schedule',
            action='store_true',
            help='Initialize default schedule configuration'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=3,
            help='Number of factoids to generate (default: 3)'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        self.verbosity = options['verbosity']
        self.dry_run = options['dry_run']
        
        if options['init_schedule']:
            self.initialize_schedule()
            return
        
        # Get or create schedule
        schedule = SitewideFactoidSchedule.get_default_schedule()
        
        if options['force']:
            self.force_generation(schedule, options['limit'])
        elif options['check_schedule']:
            self.check_and_update(schedule, options['limit'])
        else:
            self.stdout.write("Please specify --check-schedule, --force, or --init-schedule")

    def initialize_schedule(self):
        """Initialize the default factoid update schedule."""
        self.stdout.write("Initializing sitewide factoid schedule...")
        
        schedule = SitewideFactoidSchedule.get_default_schedule()
        
        # Set default times: early morning, mid-morning, mid-afternoon, evening
        default_times = ['06:00', '10:30', '14:00', '18:30']
        schedule.update_times = default_times
        schedule.is_active = True
        schedule.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Schedule initialized with {len(default_times)} daily update times: {', '.join(default_times)}"
            )
        )

    def check_and_update(self, schedule, limit):
        """Check schedule and data changes, update if needed."""
        self.stdout.write("Checking if sitewide factoids need updating...")
        
        # Step 1: Check if we should check for updates
        if not schedule.should_check_for_updates():
            if self.verbosity >= 1:
                self.stdout.write("Not in scheduled update window")
            return
        
        # Step 2: Check for data changes
        if self.verbosity >= 1:
            self.stdout.write("Checking for data changes...")
        
        change_count = schedule.detect_data_changes()
        
        if self.verbosity >= 1:
            if change_count > 0:
                self.stdout.write(f"Found {change_count} data changes since last check")
            else:
                self.stdout.write("No new data changes detected")
        
        # Step 3: Check if we should generate factoids
        if not schedule.should_generate_factoids():
            if self.verbosity >= 1:
                if not schedule.pending_changes:
                    self.stdout.write("No pending changes, factoids are up to date")
                else:
                    self.stdout.write("Too soon since last generation")
            return
        
        # Step 4: Generate factoids
        self.generate_factoids(schedule, limit)

    def force_generation(self, schedule, limit):
        """Force factoid generation regardless of schedule."""
        self.stdout.write("Forcing sitewide factoid generation...")
        
        # Mark as having pending changes to bypass checks
        schedule.pending_changes = True
        schedule.save()
        
        self.generate_factoids(schedule, limit)

    def generate_factoids(self, schedule, limit):
        """Generate new sitewide factoids."""
        if self.dry_run:
            self.stdout.write(f"[DRY RUN] Would generate {limit} sitewide factoids")
            return
        
        self.stdout.write(f"Generating {limit} sitewide factoids...")
        
        start_time = timezone.now()
        
        try:
            # Initialize the optimized generator
            generator = OptimizedSitewideFactoidGenerator()
            
            # Generate factoids using optimized data
            factoids = generator.generate_optimized_factoids(limit=limit)
            
            generation_time = (timezone.now() - start_time).total_seconds()
            
            if factoids:
                # Cache the results with multi-level strategy
                self.cache_factoids(factoids, generation_time)
                
                # Record successful generation
                schedule.record_generation(
                    success=True,
                    generation_time=generation_time
                )
                
                # Mark changes as processed
                self.mark_changes_processed()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Generated {len(factoids)} factoids in {generation_time:.1f}s"
                    )
                )
                
                if self.verbosity >= 2:
                    for i, factoid in enumerate(factoids, 1):
                        self.stdout.write(f"  {i}. {factoid.get('text', 'N/A')}")
                
            else:
                raise Exception("No factoids generated")
        
        except Exception as e:
            generation_time = (timezone.now() - start_time).total_seconds()
            
            # Record failed generation
            schedule.record_generation(
                success=False,
                generation_time=generation_time,
                error_message=str(e)
            )
            
            self.stdout.write(
                self.style.ERROR(f"Factoid generation failed: {e}")
            )
            
            logger.error(f"Sitewide factoid generation failed: {e}")

    def cache_factoids(self, factoids, generation_time):
        """Cache factoids using multi-level strategy."""
        if self.verbosity >= 2:
            self.stdout.write("Caching factoids...")
        
        # Cache in Django cache for immediate use
        cache_key = "sitewide_factoids_3"
        cache.set(cache_key, factoids, 21600)  # 6 hours
        
        # Store in optimized cache for analytics and backup
        content_hash = OptimizedFactoidCache.objects.model._meta.get_field('content_hash')
        
        import hashlib
        import json
        content_json = json.dumps(factoids, sort_keys=True)
        content_hash_value = hashlib.sha256(content_json.encode()).hexdigest()
        
        # Store in optimized cache
        OptimizedFactoidCache.objects.update_or_create(
            cache_key=cache_key,
            defaults={
                'cache_level': 'factoids',
                'content': factoids,
                'content_hash': content_hash_value,
                'expires_at': timezone.now() + timedelta(hours=6),
                'generation_time': generation_time,
                'content_size': len(content_json)
            }
        )
        
        if self.verbosity >= 2:
            self.stdout.write(f"  Cached {len(factoids)} factoids")

    def mark_changes_processed(self):
        """Mark all pending changes as processed."""
        # Get unprocessed changes
        unprocessed = SitewideDataChangeLog.objects.filter(processed=False)
        count = unprocessed.count()
        
        if count > 0:
            # Mark all as processed
            unprocessed.update(processed=True, processed_at=timezone.now())
            
            if self.verbosity >= 2:
                self.stdout.write(f"  Marked {count} changes as processed")

    def cleanup_expired_cache(self):
        """Clean up expired cache entries."""
        cleaned_count = OptimizedFactoidCache.cleanup_expired()
        
        if cleaned_count > 0 and self.verbosity >= 2:
            self.stdout.write(f"  Cleaned up {cleaned_count} expired cache entries")