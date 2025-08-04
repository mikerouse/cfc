"""
Management command to migrate existing ActivityLog entries to new format for better story generation
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from council_finance.models import ActivityLog, DataField
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate existing ActivityLog entries to new format for rich feed stories"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of entries to process (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS(f"Starting ActivityLog migration {'(DRY RUN)' if dry_run else ''}"))
        
        # Get all ActivityLog entries that need migration
        activity_logs = ActivityLog.objects.filter(
            activity_type__in=['data_edit', 'update', 'create']
        ).order_by('-created')[:limit]
        
        if not activity_logs:
            self.stdout.write(self.style.WARNING("No activity logs found to migrate"))
            return
        
        self.stdout.write(f"Found {len(activity_logs)} activity logs to check")
        
        # Create field lookup map for performance
        # Map display names to slugs
        field_name_to_slug = {}
        all_fields = DataField.objects.all()
        for field in all_fields:
            field_name_to_slug[field.name] = field.slug
            field_name_to_slug[field.name.lower()] = field.slug
            field_name_to_slug[field.slug] = field.slug  # Already correct
        
        migrated_count = 0
        error_count = 0
        
        for activity_log in activity_logs:
            try:
                if self._migrate_activity_log(activity_log, field_name_to_slug, dry_run):
                    migrated_count += 1
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error migrating activity {activity_log.id}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Migration complete: {migrated_count} migrated, {error_count} errors"
            )
        )
    
    def _migrate_activity_log(self, activity_log, field_name_to_slug, dry_run):
        """Migrate a single activity log entry"""
        try:
            # Parse existing details
            if isinstance(activity_log.details, str):
                details = json.loads(activity_log.details)
            else:
                details = activity_log.details or {}
        except (json.JSONDecodeError, TypeError):
            details = {}
        
        changed = False
        changes = []
        
        # 1. Update activity_type from 'data_edit' to 'update'
        if activity_log.activity_type == 'data_edit':
            if not dry_run:
                activity_log.activity_type = 'update'
            changes.append("activity_type: data_edit → update")
            changed = True
        
        # 2. Fix field_name format (display name → slug)
        if 'field_name' in details:
            current_field_name = details['field_name']
            
            # Check if it's already in slug format (contains hyphens)
            if '-' not in current_field_name and current_field_name in field_name_to_slug:
                # Convert display name to slug
                slug_name = field_name_to_slug[current_field_name]
                if slug_name != current_field_name:
                    details['field_name'] = slug_name
                    details['field_display_name'] = current_field_name  # Preserve original
                    changes.append(f"field_name: '{current_field_name}' → '{slug_name}'")
                    changed = True
        
        # 3. Add missing year if we can infer it
        if 'year' not in details and activity_log.created:
            # Try to infer year from creation date
            created_year = activity_log.created.year
            if created_year >= 2023:  # Only add for recent entries
                # Convert to financial year format (e.g., 2024 → 2024/25)
                financial_year = f"{created_year}/{str(created_year + 1)[-2:]}"
                details['year'] = financial_year
                changes.append(f"added year: {financial_year}")
                changed = True
        
        if changed:
            if not dry_run:
                activity_log.details = json.dumps(details)
                activity_log.save()
            
            self.stdout.write(
                f"{'[DRY RUN] ' if dry_run else ''}Activity {activity_log.id} "
                f"({activity_log.related_council.name}): {', '.join(changes)}"
            )
            return True
        
        return False