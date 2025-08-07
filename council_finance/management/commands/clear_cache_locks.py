"""
Management command to clear stuck cache warming locks.

Usage:
    python manage.py clear_cache_locks              # Clear all cache warming locks
    python manage.py clear_cache_locks --list-only  # Show current locks without clearing
    python manage.py clear_cache_locks --force      # Force clear all locks regardless of age
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Clear stuck cache warming locks (emergency use only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list-only',
            action='store_true', 
            help='List current locks without clearing them'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force clear all locks regardless of how long they have been held'
        )

    def handle(self, *args, **options):
        # Known lock keys that might get stuck
        lock_keys = [
            "site_totals_agent_run_lock",
            "critical_counter_warming_lock", 
            "warmup_counter_cache_command_lock",
            "counter_cache_warming_progress"
        ]
        
        found_locks = []
        
        # Check which locks exist
        for lock_key in lock_keys:
            lock_value = cache.get(lock_key)
            if lock_value is not None:
                found_locks.append(lock_key)
        
        if not found_locks:
            self.stdout.write(
                self.style.SUCCESS('✅ No cache warming locks found - system is clear')
            )
            return
        
        # List current locks
        self.stdout.write(
            self.style.WARNING(f'Found {len(found_locks)} active locks:')
        )
        for lock_key in found_locks:
            self.stdout.write(f'  - {lock_key}')
        
        if options['list_only']:
            self.stdout.write('')
            self.stdout.write('Use --force to clear these locks if they are stuck')
            return
        
        # Clear the locks
        cleared_count = 0
        for lock_key in found_locks:
            try:
                cache.delete(lock_key)
                cleared_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Cleared lock: {lock_key}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to clear {lock_key}: {e}')
                )
        
        self.stdout.write('')
        if cleared_count == len(found_locks):
            self.stdout.write(
                self.style.SUCCESS(f'🎉 Successfully cleared all {cleared_count} locks!')
            )
            self.stdout.write('')
            self.stdout.write('The cache warming system should now be able to run normally.')
            self.stdout.write('You may want to run: python manage.py warmup_counter_cache')
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Cleared {cleared_count}/{len(found_locks)} locks')
            )