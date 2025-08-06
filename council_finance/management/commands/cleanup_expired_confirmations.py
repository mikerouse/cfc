"""
Management command to clean up expired email confirmation tokens and pending changes.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from council_finance.services.email_confirmation import email_confirmation_service
from event_viewer.models import SystemEvent


class Command(BaseCommand):
    help = 'Clean up expired email confirmation tokens and pending profile changes'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup of expired confirmations...')
        
        try:
            results = email_confirmation_service.cleanup_expired_confirmations()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully cleaned up {results["expired_changes"]} expired changes '
                    f'and {results["expired_profile_tokens"]} expired profile tokens'
                )
            )
            
            # Log to Event Viewer
            SystemEvent.objects.create(
                source='maintenance',
                level='info',
                category='data_processing',
                title='Expired Confirmations Cleanup Completed',
                message=f'Cleaned up {results["expired_changes"]} expired changes and {results["expired_profile_tokens"]} expired tokens',
                details=results,
                tags=['cleanup', 'maintenance', 'email_confirmation'],
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during cleanup: {e}')
            )
            
            # Log error to Event Viewer
            SystemEvent.objects.create(
                source='maintenance',
                level='error',
                category='data_processing',
                title='Expired Confirmations Cleanup Failed',
                message=f'Error during cleanup: {str(e)}',
                tags=['cleanup', 'maintenance', 'error'],
            )