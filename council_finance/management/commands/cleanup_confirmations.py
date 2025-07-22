"""
Management command to cleanup expired email confirmations and pending changes.

This command should be run regularly (e.g., daily via cron) to maintain database hygiene.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from council_finance.services.email_confirmation import email_confirmation_service


class Command(BaseCommand):
    help = 'Clean up expired email confirmations and pending profile changes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about the cleanup',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('Email Confirmation Cleanup')
        )
        self.stdout.write('=' * 50)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('[DRY RUN MODE - No changes will be made]')
            )
        
        # Get current counts before cleanup
        from council_finance.models import PendingProfileChange, UserProfile
        
        pending_changes_count = PendingProfileChange.objects.filter(
            status='pending'
        ).count()
        
        expired_pending_count = PendingProfileChange.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        ).count()
        
        expired_profile_tokens = UserProfile.objects.filter(
            pending_email_expires__lt=timezone.now(),
            pending_email__isnull=False
        ).exclude(pending_email='').count()
        
        if verbose:
            self.stdout.write('\nBefore cleanup:')
            self.stdout.write(f'  Total pending changes: {pending_changes_count}')
            self.stdout.write(f'  Expired pending changes: {expired_pending_count}')
            self.stdout.write(f'  Expired profile email tokens: {expired_profile_tokens}')
        
        if not dry_run:
            # Perform actual cleanup
            cleanup_results = email_confirmation_service.cleanup_expired_confirmations()
            
            self.stdout.write('\n' + self.style.SUCCESS('Cleanup Results:'))
            self.stdout.write(f'  Expired pending changes cleaned: {cleanup_results["expired_changes"]}')
            self.stdout.write(f'  Expired profile tokens cleaned: {cleanup_results["expired_profile_tokens"]}')
            
            if cleanup_results['expired_changes'] > 0 or cleanup_results['expired_profile_tokens'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully cleaned up {cleanup_results["expired_changes"] + cleanup_results["expired_profile_tokens"]} expired items'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ No expired items found - database is clean')
                )
        else:
            # Dry run - just show what would be cleaned
            total_to_clean = expired_pending_count + expired_profile_tokens
            
            self.stdout.write('\n' + self.style.WARNING('Would clean up:'))
            self.stdout.write(f'  {expired_pending_count} expired pending changes')
            self.stdout.write(f'  {expired_profile_tokens} expired profile email tokens')
            self.stdout.write(f'  Total items: {total_to_clean}')
            
            if total_to_clean > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Run without --dry-run to clean up {total_to_clean} expired items'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No expired items found - database is clean')
                )
        
        # Show current confirmation statistics
        if verbose:
            self.stdout.write('\n' + self.style.HTTP_INFO('Current Statistics:'))
            
            # Get fresh counts after cleanup
            current_pending = PendingProfileChange.objects.filter(
                status='pending'
            ).count()
            
            confirmed_changes = PendingProfileChange.objects.filter(
                status='confirmed'
            ).count()
            
            cancelled_changes = PendingProfileChange.objects.filter(
                status='cancelled'
            ).count()
            
            confirmed_profiles = UserProfile.objects.filter(
                email_confirmed=True
            ).count()
            
            unconfirmed_profiles = UserProfile.objects.filter(
                email_confirmed=False
            ).count()
            
            self.stdout.write(f'  Active pending changes: {current_pending}')
            self.stdout.write(f'  Confirmed changes (total): {confirmed_changes}')
            self.stdout.write(f'  Cancelled changes (total): {cancelled_changes}')
            self.stdout.write(f'  Users with confirmed email: {confirmed_profiles}')
            self.stdout.write(f'  Users with unconfirmed email: {unconfirmed_profiles}')
        
        self.stdout.write('\n' + self.style.SUCCESS('Cleanup completed successfully!'))
        
        # Provide recommendations
        if expired_pending_count > 10:
            self.stdout.write(
                self.style.WARNING(
                    '\n💡 Recommendation: Consider running this command more frequently.'
                )
            )
        
        if not dry_run and (cleanup_results.get('expired_changes', 0) > 0 or cleanup_results.get('expired_profile_tokens', 0) > 0):
            self.stdout.write(
                self.style.HTTP_INFO(
                    '\n📊 Tip: Add this command to your cron job to run daily:\n'
                    '   0 2 * * * /path/to/manage.py cleanup_confirmations'
                )
            )