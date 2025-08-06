"""
Management command to check authentication security and send alerts.

This command should be run periodically (e.g., every hour via cron) to monitor
for authentication failures, brute force attacks, and other security events.
"""

from django.core.management.base import BaseCommand
from council_finance.services.auth_security_monitor import auth_security_monitor
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check authentication security events and send alerts if necessary'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually sending alerts',
        )
        parser.add_argument(
            '--send-report',
            action='store_true',
            help='Send a complete security report regardless of alert thresholds',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Running authentication security check...')
        
        try:
            # Generate security report
            report = auth_security_monitor.generate_security_report()
            alerts = report['alerts']
            
            if options['verbose']:
                self.stdout.write(f"\nSecurity Report Generated at {report['generated_at']}")
                self.stdout.write("=" * 50)
                
                # Show security metrics
                metrics = report['security_metrics']
                self.stdout.write("\n📊 Security Metrics (24h):")
                self.stdout.write(f"  • Total auth events: {metrics['total_auth_events_24h']}")
                self.stdout.write(f"  • Failed logins: {metrics['failed_logins_24h']}")
                self.stdout.write(f"  • Successful registrations: {metrics['successful_registrations_24h']}")
                self.stdout.write(f"  • Password resets: {metrics['password_resets_24h']}")
                self.stdout.write(f"  • Unique IPs with failures: {metrics['unique_ips_with_failures']}")
                self.stdout.write(f"  • GDPR requests (7d): {metrics['gdpr_requests_7d']}")
                
                # Show user security status
                user_status = report['user_security_status']
                self.stdout.write("\n👥 User Security Status:")
                self.stdout.write(f"  • Total users: {user_status['total_users']}")
                self.stdout.write(f"  • Auth0 users: {user_status['auth0_users']}")
                self.stdout.write(f"  • Unverified emails: {user_status['unverified_emails']}")
                self.stdout.write(f"  • OSA restricted: {user_status['osa_restricted_users']}")
                self.stdout.write(f"  • Deactivated accounts: {user_status['deactivated_users']}")
            
            # Process alerts
            if alerts:
                self.stdout.write(f"\n🚨 {len(alerts)} Security Alert(s) Found:")
                
                for i, alert in enumerate(alerts, 1):
                    severity_icon = "🔴" if alert['severity'] == 'high' else "🟡"
                    self.stdout.write(f"\n{i}. {severity_icon} {alert['title']} ({alert['severity'].upper()})")
                    self.stdout.write(f"   {alert['message']}")
                    if 'threshold' in alert:
                        self.stdout.write(f"   Threshold: {alert['threshold']}, Actual: {alert['count']}")
                    if alert.get('details', {}).get('recommendation'):
                        self.stdout.write(f"   💡 {alert['details']['recommendation']}")
                
                if not options['dry_run']:
                    # Send alert email
                    auth_security_monitor.send_security_alert_email(alerts)
                    self.stdout.write("\n📧 Alert email sent to administrators")
                else:
                    self.stdout.write("\n📧 DRY RUN: Would send alert email to administrators")
            
            else:
                self.stdout.write("✅ No security alerts detected")
            
            # Send full report if requested
            if options['send_report']:
                if not options['dry_run']:
                    # TODO: Implement full report email
                    self.stdout.write("📊 Full security report functionality coming soon")
                else:
                    self.stdout.write("📊 DRY RUN: Would send full security report")
            
            # Log the security check
            if not options['dry_run']:
                auth_security_monitor.log_security_check(alerts)
                self.stdout.write("📝 Security check logged to Event Viewer")
            else:
                self.stdout.write("📝 DRY RUN: Would log security check to Event Viewer")
            
            self.stdout.write(f"\n✅ Security check completed - {len(alerts)} alerts processed")
            
        except Exception as e:
            logger.error(f"Error during security check: {e}")
            self.stderr.write(f"❌ Error during security check: {e}")
            raise e