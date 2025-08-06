"""
Management command to send daily feedback digest emails.
Run this via cron job or task scheduler for daily reports.
"""

from django.core.management.base import BaseCommand
from council_finance.services.feedback_notifications import send_feedback_digest


class Command(BaseCommand):
    help = 'Send daily digest of unresolved feedback submissions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send digest even if no new feedback',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Sending feedback digest...')
        
        try:
            success = send_feedback_digest()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✓ Feedback digest sent successfully')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ No digest sent (no unresolved feedback or email not configured)')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed to send feedback digest: {e}')
            )