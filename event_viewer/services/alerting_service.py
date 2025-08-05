"""
Event Viewer Alerting Service

Provides threshold-based alerting, trend detection, and intelligent notifications
for system monitoring and early issue detection.
"""

import logging
from datetime import timedelta, datetime
from collections import defaultdict
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.cache import cache
from django.db.models import Count, Q
from ..models import SystemEvent, EventSummary
from ..settings import event_viewer_config
from .correlation_engine import correlation_engine

logger = logging.getLogger(__name__)


class AlertingService:
    """
    Manages threshold-based alerting and intelligent notifications
    for the Event Viewer system.
    """
    
    def __init__(self):
        self.config = event_viewer_config
        self.rate_limit_cache_prefix = 'event_viewer_alert_rate_limit'
    
    def check_thresholds_and_alert(self):
        """
        Check all configured alert thresholds and send notifications
        for any violations. This should be called periodically.
        """
        if not self.config.is_email_alerts_enabled():
            logger.debug("Email alerts are disabled, skipping threshold checks")
            return
        
        alerts_sent = []
        
        # Check hourly thresholds
        alerts_sent.extend(self._check_hourly_thresholds())
        
        # Check daily thresholds
        alerts_sent.extend(self._check_daily_thresholds())
        
        # Check for error patterns
        alerts_sent.extend(self._check_error_patterns())
        
        # Check for anomalies if trend detection is enabled
        if self.config.is_trend_detection_enabled():
            alerts_sent.extend(self._check_anomalies())
        
        return alerts_sent
    
    def _check_hourly_thresholds(self):
        """Check thresholds that are measured per hour."""
        alerts_sent = []
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        # Critical errors threshold
        critical_threshold = self.config.get_alert_threshold('critical_errors_per_hour')
        if critical_threshold > 0:
            critical_count = SystemEvent.objects.filter(
                timestamp__gte=one_hour_ago,
                level='critical'
            ).count()
            
            if critical_count >= critical_threshold:
                alert_sent = self._send_threshold_alert(
                    'critical_errors_per_hour',
                    f"Critical Error Threshold Exceeded: {critical_count} events in the last hour",
                    f"System has generated {critical_count} critical errors in the last hour, "
                    f"exceeding the threshold of {critical_threshold}.",
                    critical_count,
                    critical_threshold,
                    self._get_recent_events(one_hour_ago, level='critical')
                )
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        # Total errors threshold
        total_threshold = self.config.get_alert_threshold('total_errors_per_hour')
        if total_threshold > 0:
            total_count = SystemEvent.objects.filter(
                timestamp__gte=one_hour_ago,
                level__in=['error', 'critical']
            ).count()
            
            if total_count >= total_threshold:
                alert_sent = self._send_threshold_alert(
                    'total_errors_per_hour',
                    f"Total Error Threshold Exceeded: {total_count} events in the last hour",
                    f"System has generated {total_count} total errors in the last hour, "
                    f"exceeding the threshold of {total_threshold}.",
                    total_count,
                    total_threshold,
                    self._get_recent_events(one_hour_ago, level__in=['error', 'critical'])
                )
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        # API errors threshold
        api_threshold = self.config.get_alert_threshold('api_errors_per_hour')
        if api_threshold > 0:
            api_count = SystemEvent.objects.filter(
                timestamp__gte=one_hour_ago,
                source='api',
                level__in=['error', 'critical']
            ).count()
            
            if api_count >= api_threshold:
                alert_sent = self._send_threshold_alert(
                    'api_errors_per_hour',
                    f"API Error Threshold Exceeded: {api_count} events in the last hour",
                    f"API system has generated {api_count} errors in the last hour, "
                    f"exceeding the threshold of {api_threshold}.",
                    api_count,
                    api_threshold,
                    self._get_recent_events(one_hour_ago, source='api', level__in=['error', 'critical'])
                )
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        # Security events threshold
        security_threshold = self.config.get_alert_threshold('security_events_per_hour')
        if security_threshold > 0:
            security_count = SystemEvent.objects.filter(
                timestamp__gte=one_hour_ago,
                category='security'
            ).count()
            
            if security_count >= security_threshold:
                alert_sent = self._send_threshold_alert(
                    'security_events_per_hour',
                    f"Security Event Threshold Exceeded: {security_count} events in the last hour",
                    f"System has detected {security_count} security events in the last hour, "
                    f"exceeding the threshold of {security_threshold}.",
                    security_count,
                    security_threshold,
                    self._get_recent_events(one_hour_ago, category='security')
                )
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        return alerts_sent
    
    def _check_daily_thresholds(self):
        """Check thresholds that are measured per day."""
        alerts_sent = []
        one_day_ago = timezone.now() - timedelta(days=1)
        
        # Test failures threshold
        test_threshold = self.config.get_alert_threshold('test_failures_per_day')
        if test_threshold > 0:
            test_count = SystemEvent.objects.filter(
                timestamp__gte=one_day_ago,
                category='test_failure'
            ).count()
            
            if test_count >= test_threshold:
                alert_sent = self._send_threshold_alert(
                    'test_failures_per_day',
                    f"Test Failure Threshold Exceeded: {test_count} failures in the last day",
                    f"System has detected {test_count} test failures in the last day, "
                    f"exceeding the threshold of {test_threshold}.",
                    test_count,
                    test_threshold,
                    self._get_recent_events(one_day_ago, category='test_failure')
                )
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        return alerts_sent
    
    def _check_error_patterns(self):
        """Check for error patterns that indicate systemic issues."""
        alerts_sent = []
        
        patterns = correlation_engine.detect_error_patterns(hours_back=2)
        
        for pattern in patterns:
            if pattern['severity'] == 'high':
                alert_sent = self._send_pattern_alert(pattern)
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        return alerts_sent
    
    def _check_anomalies(self):
        """Check for anomalies using trend detection."""
        alerts_sent = []
        
        # This would implement statistical anomaly detection
        # For now, we'll implement a simple version
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        last_hour = current_hour - timedelta(hours=1)
        
        # Get error count for the last hour
        current_errors = SystemEvent.objects.filter(
            timestamp__gte=last_hour,
            timestamp__lt=current_hour,
            level__in=['error', 'critical']
        ).count()
        
        # Get baseline (average of same hour over past week)
        baseline_hours = []
        for i in range(1, 8):  # Past 7 days
            baseline_start = current_hour - timedelta(days=i)
            baseline_end = baseline_start + timedelta(hours=1)
            baseline_count = SystemEvent.objects.filter(
                timestamp__gte=baseline_start,
                timestamp__lt=baseline_end,
                level__in=['error', 'critical']
            ).count()
            baseline_hours.append(baseline_count)
        
        if baseline_hours:
            baseline_average = sum(baseline_hours) / len(baseline_hours)
            threshold_multiplier = self.config.get('TREND_DETECTION.anomaly_threshold', 2.5)
            
            if current_errors > (baseline_average * threshold_multiplier) and current_errors >= 5:
                alert_sent = self._send_anomaly_alert(
                    current_errors,
                    baseline_average,
                    threshold_multiplier
                )
                if alert_sent:
                    alerts_sent.append(alert_sent)
        
        return alerts_sent
    
    def _send_threshold_alert(self, threshold_name, subject, description, current_count, threshold, recent_events):
        """Send a threshold violation alert."""
        # Check rate limiting
        cache_key = f"{self.rate_limit_cache_prefix}:{threshold_name}"
        if cache.get(cache_key):
            logger.debug(f"Rate limiting threshold alert: {threshold_name}")
            return None
        
        # Set rate limit
        rate_limit_minutes = self.config.get('NOTIFICATIONS.notification_rate_limit_minutes', 60)
        cache.set(cache_key, True, rate_limit_minutes * 60)
        
        # Prepare email content
        context = {
            'threshold_name': threshold_name,
            'subject': subject,
            'description': description,
            'current_count': current_count,
            'threshold': threshold,
            'recent_events': recent_events[:10],  # Limit to 10 events
            'timestamp': timezone.now(),
        }
        
        html_content = render_to_string('event_viewer/emails/threshold_alert.html', context)
        text_content = render_to_string('event_viewer/emails/threshold_alert.txt', context)
        
        # Send email
        try:
            msg = EmailMultiAlternatives(
                subject=f"[System Alert] {subject}",
                body=text_content,
                from_email=self.config.get('ALERT_EMAIL_FROM'),
                to=self.config.get_alert_recipients()
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Sent threshold alert: {threshold_name}")
            return {
                'type': 'threshold_alert',
                'threshold_name': threshold_name,
                'subject': subject,
                'sent_at': timezone.now()
            }
        
        except Exception as e:
            logger.error(f"Failed to send threshold alert: {e}")
            return None
    
    def _send_pattern_alert(self, pattern):
        """Send an alert for detected error patterns."""
        # Check rate limiting
        cache_key = f"{self.rate_limit_cache_prefix}:pattern:{pattern['type']}"
        if cache.get(cache_key):
            logger.debug(f"Rate limiting pattern alert: {pattern['type']}")
            return None
        
        # Set rate limit
        rate_limit_minutes = self.config.get('NOTIFICATIONS.notification_rate_limit_minutes', 60)
        cache.set(cache_key, True, rate_limit_minutes * 60)
        
        # Prepare email content
        context = {
            'pattern': pattern,
            'timestamp': timezone.now(),
        }
        
        html_content = render_to_string('event_viewer/emails/pattern_alert.html', context)
        text_content = render_to_string('event_viewer/emails/pattern_alert.txt', context)
        
        # Send email
        try:
            msg = EmailMultiAlternatives(
                subject=f"[System Pattern Alert] {pattern['title']}",
                body=text_content,
                from_email=self.config.get('ALERT_EMAIL_FROM'),
                to=self.config.get_alert_recipients()
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Sent pattern alert: {pattern['type']}")
            return {
                'type': 'pattern_alert',
                'pattern_type': pattern['type'],
                'subject': pattern['title'],
                'sent_at': timezone.now()
            }
        
        except Exception as e:
            logger.error(f"Failed to send pattern alert: {e}")
            return None
    
    def _send_anomaly_alert(self, current_count, baseline_average, threshold_multiplier):
        """Send an alert for detected anomalies."""
        # Check rate limiting
        cache_key = f"{self.rate_limit_cache_prefix}:anomaly"
        if cache.get(cache_key):
            logger.debug("Rate limiting anomaly alert")
            return None
        
        # Set rate limit
        rate_limit_minutes = self.config.get('NOTIFICATIONS.notification_rate_limit_minutes', 60)
        cache.set(cache_key, True, rate_limit_minutes * 60)
        
        # Prepare email content
        context = {
            'current_count': current_count,
            'baseline_average': round(baseline_average, 1),
            'threshold_multiplier': threshold_multiplier,
            'percentage_increase': round(((current_count / baseline_average) - 1) * 100, 1),
            'timestamp': timezone.now(),
        }
        
        html_content = render_to_string('event_viewer/emails/anomaly_alert.html', context)
        text_content = render_to_string('event_viewer/emails/anomaly_alert.txt', context)
        
        # Send email
        try:
            msg = EmailMultiAlternatives(
                subject=f"[System Anomaly Alert] Error Rate Spike Detected",
                body=text_content,
                from_email=self.config.get('ALERT_EMAIL_FROM'),
                to=self.config.get_alert_recipients()
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info("Sent anomaly alert")
            return {
                'type': 'anomaly_alert',
                'current_count': current_count,
                'baseline_average': baseline_average,
                'sent_at': timezone.now()
            }
        
        except Exception as e:
            logger.error(f"Failed to send anomaly alert: {e}")
            return None
    
    def _get_recent_events(self, since, **filters):
        """Get recent events matching the given filters."""
        return list(SystemEvent.objects.filter(
            timestamp__gte=since,
            **filters
        ).order_by('-timestamp')[:20])
    
    def send_health_report(self, report_type='daily'):
        """Send a health report email."""
        if not self.config.is_email_alerts_enabled():
            return None
        
        if report_type == 'daily':
            return self._send_daily_health_report()
        elif report_type == 'weekly':
            return self._send_weekly_health_report()
    
    def _send_daily_health_report(self):
        """Send daily health report."""
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Get daily summary
        try:
            summary = EventSummary.objects.get(date=yesterday)
        except EventSummary.DoesNotExist:
            # Create summary if it doesn't exist
            summary = self._create_daily_summary(yesterday)
        
        # Get top events from yesterday
        yesterday_start = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
        yesterday_end = yesterday_start + timedelta(days=1)
        
        top_errors = SystemEvent.objects.filter(
            timestamp__range=(yesterday_start, yesterday_end),
            level__in=['error', 'critical']
        ).order_by('-timestamp')[:10]
        
        context = {
            'report_type': 'Daily',
            'date': yesterday,
            'summary': summary,
            'top_errors': top_errors,
            'timestamp': timezone.now(),
        }
        
        html_content = render_to_string('event_viewer/emails/health_report.html', context)
        text_content = render_to_string('event_viewer/emails/health_report.txt', context)
        
        try:
            msg = EmailMultiAlternatives(
                subject=f"[Daily Health Report] System Status for {yesterday}",
                body=text_content,
                from_email=self.config.get('ALERT_EMAIL_FROM'),
                to=self.config.get_alert_recipients()
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Sent daily health report for {yesterday}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send daily health report: {e}")
            return False
    
    def _send_weekly_health_report(self):
        """Send weekly health report."""
        # Implementation for weekly reports
        # This would aggregate data over the past week
        pass
    
    def _create_daily_summary(self, date):
        """Create a daily summary for the given date."""
        from .analytics_service import analytics_service
        return analytics_service.create_daily_summary(date)


# Global alerting service instance
alerting_service = AlertingService()