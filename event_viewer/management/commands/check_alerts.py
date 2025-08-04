"""
Management command to check alert thresholds and send notifications.

This command should be run periodically (e.g., every 15 minutes via cron)
to monitor system health and send alerts when thresholds are exceeded.

Usage:
    python manage.py check_alerts                    # Check all thresholds
    python manage.py check_alerts --dry-run          # Check without sending emails
    python manage.py check_alerts --health-report    # Send daily health report
    python manage.py check_alerts --create-summaries # Create daily summaries
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from event_viewer.services.alerting_service import alerting_service
from event_viewer.services.analytics_service import analytics_service
from event_viewer.models import EventSummary


class Command(BaseCommand):
    help = 'Check alert thresholds and send notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Check thresholds but do not send emails',
        )
        parser.add_argument(
            '--health-report',
            action='store_true',
            help='Send daily health report',
        )
        parser.add_argument(
            '--create-summaries',
            action='store_true',
            help='Create daily summaries for missing dates',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        
        if options['verbose']:
            self.stdout.write(f"Starting alert check at {start_time}")
        
        results = {
            'alerts_sent': [],
            'summaries_created': 0,
            'health_reports_sent': 0,
            'errors': []
        }
        
        try:
            # Create daily summaries if requested
            if options['create_summaries']:
                results['summaries_created'] = self._create_missing_summaries(options['verbose'])
            
            # Send health report if requested
            if options['health_report']:
                if options['dry_run']:
                    self.stdout.write("Would send daily health report (dry run)")
                else:
                    health_report_sent = alerting_service.send_health_report('daily')
                    if health_report_sent:
                        results['health_reports_sent'] = 1
                        if options['verbose']:
                            self.stdout.write("Sent daily health report")
            
            # Check alert thresholds
            if not options['health_report']:  # Don't check thresholds if only sending health report
                if options['dry_run']:
                    self.stdout.write("Dry run mode - would check thresholds but not send alerts")
                    # Still run threshold checks to see what would be triggered
                    alerts = self._check_thresholds_dry_run(options['verbose'])
                    results['alerts_sent'] = alerts
                else:
                    alerts = alerting_service.check_thresholds_and_alert()
                    results['alerts_sent'] = alerts
                    
                    if options['verbose']:
                        if alerts:
                            self.stdout.write(f"Sent {len(alerts)} alerts:")
                            for alert in alerts:
                                self.stdout.write(f"  - {alert['type']}: {alert.get('subject', alert.get('threshold_name', 'Unknown'))}")
                        else:
                            self.stdout.write("No alerts triggered")
        
        except Exception as e:
            error_msg = f"Error during alert check: {e}"
            results['errors'].append(error_msg)
            self.stderr.write(error_msg)
        
        # Summary output
        duration = timezone.now() - start_time
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ALERT CHECK SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Duration: {duration.total_seconds():.2f} seconds")
        self.stdout.write(f"Alerts sent: {len(results['alerts_sent'])}")
        self.stdout.write(f"Summaries created: {results['summaries_created']}")
        self.stdout.write(f"Health reports sent: {results['health_reports_sent']}")
        
        if results['errors']:
            self.stdout.write(f"Errors: {len(results['errors'])}")
            for error in results['errors']:
                self.stderr.write(f"  - {error}")
        else:
            self.stdout.write("Errors: 0")
        
        if options['dry_run']:
            self.stdout.write("\n[DRY RUN] No emails were actually sent")
    
    def _create_missing_summaries(self, verbose=False):
        """Create daily summaries for the past 7 days if they don't exist."""
        summaries_created = 0
        
        for i in range(1, 8):  # Past 7 days
            target_date = date.today() - timedelta(days=i)
            
            if not EventSummary.objects.filter(date=target_date).exists():
                summary = analytics_service.create_daily_summary(target_date)
                summaries_created += 1
                
                if verbose:
                    self.stdout.write(f"Created summary for {target_date}: {summary.total_events} events")
        
        return summaries_created
    
    def _check_thresholds_dry_run(self, verbose=False):
        """Check thresholds in dry run mode to show what would be triggered."""
        from event_viewer.services.alerting_service import AlertingService
        from event_viewer.settings import event_viewer_config
        
        # Temporarily disable email sending for dry run
        original_email_setting = event_viewer_config._settings['ENABLE_EMAIL_ALERTS']
        event_viewer_config._settings['ENABLE_EMAIL_ALERTS'] = False
        
        try:
            dry_run_service = AlertingService()
            
            # Check what would be triggered
            triggered_alerts = []
            
            # Check hourly thresholds manually
            one_hour_ago = timezone.now() - timedelta(hours=1)
            
            # Critical errors
            from event_viewer.models import SystemEvent
            critical_count = SystemEvent.objects.filter(
                timestamp__gte=one_hour_ago,
                level='critical'
            ).count()
            critical_threshold = event_viewer_config.get_alert_threshold('critical_errors_per_hour')
            
            if critical_count >= critical_threshold and critical_threshold > 0:
                triggered_alerts.append({
                    'type': 'threshold_alert',
                    'threshold_name': 'critical_errors_per_hour',
                    'subject': f"Would alert: {critical_count} critical errors (threshold: {critical_threshold})"
                })
                if verbose:
                    self.stdout.write(f"Would trigger: Critical errors ({critical_count} >= {critical_threshold})")
            
            # Total errors
            total_count = SystemEvent.objects.filter(
                timestamp__gte=one_hour_ago,
                level__in=['error', 'critical']
            ).count()
            total_threshold = event_viewer_config.get_alert_threshold('total_errors_per_hour')
            
            if total_count >= total_threshold and total_threshold > 0:
                triggered_alerts.append({
                    'type': 'threshold_alert',
                    'threshold_name': 'total_errors_per_hour',
                    'subject': f"Would alert: {total_count} total errors (threshold: {total_threshold})"
                })
                if verbose:
                    self.stdout.write(f"Would trigger: Total errors ({total_count} >= {total_threshold})")
            
            if verbose and not triggered_alerts:
                self.stdout.write("No thresholds would be triggered")
            
            return triggered_alerts
            
        finally:
            # Restore original email setting
            event_viewer_config._settings['ENABLE_EMAIL_ALERTS'] = original_email_setting