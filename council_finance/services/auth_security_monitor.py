"""
Authentication Security Monitoring Service

Monitors authentication events from the Event Viewer system and generates alerts
for suspicious activity, auth failures, and security violations. 

This service integrates with the existing Event Viewer architecture and uses
proper event sources and categories as defined in EVENT_VIEWER.md.
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from event_viewer.models import SystemEvent
from council_finance.models import UserProfile
from council_finance.emails import send_email

logger = logging.getLogger(__name__)


class AuthSecurityMonitor:
    """Monitor authentication security events and generate alerts."""
    
    def __init__(self):
        self.alert_thresholds = {
            'failed_logins_per_hour': 10,
            'password_resets_per_hour': 5, 
            'failed_logins_per_ip_per_hour': 5,
            'email_security_violations_per_hour': 3,
            'suspicious_registrations_per_hour': 5,
            'account_deletions_per_day': 3,
        }
    
    def check_auth_failures(self, hours_back=1):
        """Check for excessive authentication failures."""
        cutoff = timezone.now() - timedelta(hours=hours_back)
        
        alerts = []
        
        # Failed login attempts
        failed_logins = SystemEvent.objects.filter(
            source='user_auth',
            level='warning',
            title__icontains='login failed',
            timestamp__gte=cutoff
        ).count()
        
        if failed_logins > self.alert_thresholds['failed_logins_per_hour']:
            alerts.append({
                'type': 'auth_failure_surge',
                'severity': 'high',
                'title': f'High Authentication Failure Rate Detected',
                'message': f'{failed_logins} failed login attempts in the last {hours_back} hour(s)',
                'count': failed_logins,
                'threshold': self.alert_thresholds['failed_logins_per_hour'],
                'details': {
                    'period': f'{hours_back}h',
                    'recommendation': 'Check for brute force attacks or account enumeration'
                }
            })
        
        # Password reset surge
        password_resets = SystemEvent.objects.filter(
            source='user_auth',
            title='Password Reset Requested',
            timestamp__gte=cutoff
        ).count()
        
        if password_resets > self.alert_thresholds['password_resets_per_hour']:
            alerts.append({
                'type': 'password_reset_surge',
                'severity': 'medium',
                'title': f'High Password Reset Activity',
                'message': f'{password_resets} password reset requests in the last {hours_back} hour(s)',
                'count': password_resets,
                'threshold': self.alert_thresholds['password_resets_per_hour'],
                'details': {
                    'period': f'{hours_back}h',
                    'recommendation': 'May indicate credential stuffing or account takeover attempts'
                }
            })
        
        # Email security violations
        email_violations = SystemEvent.objects.filter(
            source='user_auth',
            title__icontains='security constraint violation',
            timestamp__gte=cutoff
        ).count()
        
        if email_violations > self.alert_thresholds['email_security_violations_per_hour']:
            alerts.append({
                'type': 'email_security_violations',
                'severity': 'medium',
                'title': f'Email Security Constraint Violations',
                'message': f'{email_violations} security constraint violations in the last {hours_back} hour(s)',
                'count': email_violations,
                'threshold': self.alert_thresholds['email_security_violations_per_hour'],
                'details': {
                    'period': f'{hours_back}h',
                    'recommendation': 'Check for rate limiting violations or suspicious email changes'
                }
            })
        
        return alerts
    
    def check_ip_based_attacks(self, hours_back=1):
        """Check for IP-based attack patterns."""
        cutoff = timezone.now() - timedelta(hours=hours_back)
        alerts = []
        
        # Get failed logins by IP address
        failed_login_events = SystemEvent.objects.filter(
            source='user_auth',
            level='warning',
            title__icontains='login failed',
            timestamp__gte=cutoff,
            details__ip_address__isnull=False
        )
        
        ip_failures = {}
        for event in failed_login_events:
            ip = event.details.get('ip_address')
            if ip:
                ip_failures[ip] = ip_failures.get(ip, 0) + 1
        
        # Alert on IPs with excessive failures
        for ip, count in ip_failures.items():
            if count > self.alert_thresholds['failed_logins_per_ip_per_hour']:
                alerts.append({
                    'type': 'ip_brute_force',
                    'severity': 'high',
                    'title': f'Potential Brute Force Attack from {ip}',
                    'message': f'{count} failed login attempts from IP {ip} in the last {hours_back} hour(s)',
                    'count': count,
                    'threshold': self.alert_thresholds['failed_logins_per_ip_per_hour'],
                    'details': {
                        'ip_address': ip,
                        'period': f'{hours_back}h',
                        'recommendation': f'Consider blocking IP {ip} or implementing CAPTCHA'
                    }
                })
        
        return alerts
    
    def check_account_security_events(self, hours_back=24):
        """Check for suspicious account-related security events."""
        cutoff = timezone.now() - timedelta(hours=hours_back)
        alerts = []
        
        # Account deletions/security changes
        account_security_events = SystemEvent.objects.filter(
            source='user_account',
            level__in=['warning', 'critical'],
            title__in=['Account Deletion Requested', 'User Data Anonymized', 'User Account Deactivated'],
            timestamp__gte=cutoff
        ).count()
        
        if account_security_events > self.alert_thresholds['account_deletions_per_day'] and hours_back >= 24:
            alerts.append({
                'type': 'high_account_security_activity',
                'severity': 'medium',
                'title': f'High Account Security Activity',
                'message': f'{account_security_events} account security events in the last {hours_back} hours',
                'count': account_security_events,
                'threshold': self.alert_thresholds['account_deletions_per_day'],
                'details': {
                    'period': f'{hours_back}h',
                    'recommendation': 'Review for potential coordinated account changes or user dissatisfaction'
                }
            })
        
        return alerts
    
    def generate_security_report(self):
        """Generate a comprehensive security report."""
        all_alerts = []
        
        # Check different time periods
        all_alerts.extend(self.check_auth_failures(hours_back=1))
        all_alerts.extend(self.check_ip_based_attacks(hours_back=1))
        all_alerts.extend(self.check_account_security_events(hours_back=24))
        
        # Get overall security metrics
        now = timezone.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        security_metrics = {
            'total_auth_events_24h': SystemEvent.objects.filter(
                source='user_auth',
                timestamp__gte=day_ago
            ).count(),
            'failed_logins_24h': SystemEvent.objects.filter(
                source='user_auth',
                level='warning',
                title__icontains='login failed',
                timestamp__gte=day_ago
            ).count(),
            'successful_registrations_24h': SystemEvent.objects.filter(
                source='user_onboarding',
                level='info',
                title='User Registration Completed',
                timestamp__gte=day_ago
            ).count(),
            'password_resets_24h': SystemEvent.objects.filter(
                source='user_auth',
                title='Password Reset Requested',
                timestamp__gte=day_ago
            ).count(),
            'gdpr_requests_7d': SystemEvent.objects.filter(
                source='user_account',
                category='data_privacy',
                timestamp__gte=week_ago
            ).count(),
            'unique_ips_with_failures': SystemEvent.objects.filter(
                source='user_auth',
                level='warning',
                title__icontains='login failed',
                timestamp__gte=day_ago,
                details__ip_address__isnull=False
            ).values('details__ip_address').distinct().count(),
        }
        
        # User security status
        user_security_status = {
            'total_users': UserProfile.objects.count(),
            'auth0_users': UserProfile.objects.filter(auth0_user_id__isnull=False).count(),
            'unverified_emails': UserProfile.objects.filter(email_confirmed=False).count(),
            'osa_restricted_users': UserProfile.objects.filter(can_access_comments=False).count(),
            'users_requiring_reconfirmation': UserProfile.objects.filter(requires_reconfirmation=True).count(),
        }
        
        return {
            'alerts': all_alerts,
            'security_metrics': security_metrics,
            'user_security_status': user_security_status,
            'generated_at': now,
        }
    
    def send_security_alert_email(self, alerts):
        """
        Send security alert email using Event Viewer email integration.
        
        Uses ERROR_ALERTS_EMAIL_ADDRESS from .env as defined in EVENT_VIEWER.md
        to maintain consistency with existing error alerting system.
        """
        if not alerts:
            return
        
        high_severity_alerts = [a for a in alerts if a['severity'] == 'high']
        medium_severity_alerts = [a for a in alerts if a['severity'] == 'medium']
        
        # Only send email for high severity or multiple medium severity
        if not high_severity_alerts and len(medium_severity_alerts) < 2:
            return
        
        try:
            # Use ERROR_ALERTS_EMAIL_ADDRESS as defined in Event Viewer integration
            error_alerts_email = getattr(settings, 'ERROR_ALERTS_EMAIL_ADDRESS', None)
            
            if not error_alerts_email:
                logger.warning("ERROR_ALERTS_EMAIL_ADDRESS not configured - cannot send security alerts")
                return
            
            context = {
                'alerts': alerts,
                'high_severity_count': len(high_severity_alerts),
                'medium_severity_count': len(medium_severity_alerts),
                'timestamp': timezone.now(),
            }
            
            subject = f"🚨 Authentication Security Alert - {len(high_severity_alerts)} high priority issues"
            if not high_severity_alerts:
                subject = f"⚠️ Authentication Security Notice - {len(medium_severity_alerts)} medium priority issues"
            
            send_email(
                to_email=error_alerts_email,
                subject=subject,
                template='emails/security_alert.html',
                context=context
            )
            
            logger.info(f"Security alert email sent to {error_alerts_email} for {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Failed to send security alert email: {e}")
    
    def log_security_check(self, alerts_found):
        """Log the security check execution using proper Event Viewer sources."""
        SystemEvent.objects.create(
            source='security',  # Using Event Viewer's 'security' source
            level='info' if not alerts_found else 'warning',
            category='security',  # Using Event Viewer's 'security' category
            title='Authentication Security Check Completed',
            message=f'Security monitor checked authentication events, found {len(alerts_found)} alerts',
            details={
                'alerts_count': len(alerts_found),
                'check_timestamp': timezone.now().isoformat(),
                'monitor_version': '1.0',
                'alert_types': [alert['type'] for alert in alerts_found] if alerts_found else [],
            },
            tags=['security_check', 'automated_monitoring', 'auth_security'],
            fingerprint=f'auth_security_check_{timezone.now().strftime("%Y%m%d")}'
        )


# Singleton instance
auth_security_monitor = AuthSecurityMonitor()