"""
Event Viewer Configuration System

Provides centralized configuration for alerting thresholds, retention policies,
and analytics settings for the Event Viewer system.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Default Event Viewer settings
DEFAULT_EVENT_VIEWER_SETTINGS = {
    # Alerting Configuration
    'ENABLE_EMAIL_ALERTS': True,
    'ALERT_EMAIL_FROM': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
    'ALERT_EMAIL_TO': [getattr(settings, 'ERROR_ALERTS_EMAIL_ADDRESS', 'admin@example.com')],
    
    # Threshold-based alerting (events per time period)
    'ALERT_THRESHOLDS': {
        'critical_errors_per_hour': 5,
        'total_errors_per_hour': 20,
        'api_errors_per_hour': 10,
        'security_events_per_hour': 3,
        'test_failures_per_day': 1,
    },
    
    # Trend detection settings
    'TREND_DETECTION': {
        'enable_anomaly_detection': True,
        'baseline_days': 7,  # Days to use for baseline calculation
        'anomaly_threshold': 2.5,  # Standard deviations from baseline
        'minimum_events_for_trend': 10,  # Minimum events needed for trend analysis
    },
    
    # Data retention policies
    'RETENTION_POLICIES': {
        'default_retention_days': 90,
        'critical_events_retention_days': 365,
        'debug_events_retention_days': 30,
        'summary_retention_days': 730,  # EventSummary records
    },
    
    # Analytics settings
    'ANALYTICS': {
        'enable_health_scoring': True,
        'health_score_weights': {
            'error_rate': 0.4,
            'critical_events': 0.3,
            'security_incidents': 0.2,
            'system_availability': 0.1,
        },
        'daily_summary_time': '06:00',  # Time to generate daily summaries
        'weekly_report_day': 1,  # Monday (0=Monday, 6=Sunday)
    },
    
    # Log parsing settings
    'LOG_PARSING': {
        'auto_parse_enabled': False,  # Enable automatic log parsing
        'parse_interval_minutes': 15,  # How often to parse logs
        'max_parse_time_seconds': 300,  # Timeout for parsing operations
        'enable_real_time_parsing': False,  # File watching for real-time parsing
    },
    
    # Performance settings
    'PERFORMANCE': {
        'dashboard_cache_minutes': 5,
        'analytics_cache_hours': 1,
        'event_list_page_size': 50,
        'max_events_per_export': 10000,
    },
    
    # Notification settings
    'NOTIFICATIONS': {
        'enable_slack_integration': False,
        'slack_webhook_url': None,
        'enable_teams_integration': False,
        'teams_webhook_url': None,
        'notification_rate_limit_minutes': 60,  # Minimum time between similar notifications
    }
}


class EventViewerConfig:
    """
    Configuration manager for Event Viewer settings.
    
    Provides access to Event Viewer settings with fallbacks to defaults
    and validation of configuration values.
    """
    
    def __init__(self):
        self._settings = None
        self._load_settings()
    
    def _load_settings(self):
        """Load Event Viewer settings from Django settings with defaults."""
        user_settings = getattr(settings, 'EVENT_VIEWER_SETTINGS', {})
        
        # Merge user settings with defaults
        self._settings = DEFAULT_EVENT_VIEWER_SETTINGS.copy()
        self._merge_settings(self._settings, user_settings)
        
        # Validate critical settings
        self._validate_settings()
    
    def _merge_settings(self, defaults, user_settings):
        """Recursively merge user settings with defaults."""
        for key, value in user_settings.items():
            if key in defaults and isinstance(defaults[key], dict) and isinstance(value, dict):
                self._merge_settings(defaults[key], value)
            else:
                defaults[key] = value
    
    def _validate_settings(self):
        """Validate critical configuration settings."""
        # Validate email settings if alerts are enabled
        if self._settings['ENABLE_EMAIL_ALERTS']:
            if not self._settings['ALERT_EMAIL_TO'] or not self._settings['ALERT_EMAIL_TO'][0]:
                # Check if ERROR_ALERTS_EMAIL_ADDRESS is set in Django settings
                if not getattr(settings, 'ERROR_ALERTS_EMAIL_ADDRESS', None):
                    raise ImproperlyConfigured(
                        "ERROR_ALERTS_EMAIL_ADDRESS must be configured in Django settings (.env file) "
                        "when email alerts are enabled, or set EVENT_VIEWER_SETTINGS['ALERT_EMAIL_TO']"
                    )
        
        # Validate thresholds are positive integers
        for threshold_name, value in self._settings['ALERT_THRESHOLDS'].items():
            if not isinstance(value, int) or value < 0:
                raise ImproperlyConfigured(
                    f"Alert threshold '{threshold_name}' must be a positive integer"
                )
        
        # Validate retention days are positive
        for policy_name, days in self._settings['RETENTION_POLICIES'].items():
            if not isinstance(days, int) or days < 1:
                raise ImproperlyConfigured(
                    f"Retention policy '{policy_name}' must be a positive integer (days)"
                )
    
    def get(self, key, default=None):
        """Get a setting value with optional default."""
        keys = key.split('.')
        value = self._settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_alert_threshold(self, threshold_name):
        """Get a specific alert threshold value."""
        return self.get(f'ALERT_THRESHOLDS.{threshold_name}', 0)
    
    def get_retention_days(self, policy_name):
        """Get retention days for a specific policy."""
        return self.get(f'RETENTION_POLICIES.{policy_name}', 90)
    
    def is_email_alerts_enabled(self):
        """Check if email alerts are enabled."""
        return self.get('ENABLE_EMAIL_ALERTS', False)
    
    def get_alert_recipients(self):
        """Get list of email addresses for alerts."""
        return self.get('ALERT_EMAIL_TO', [])
    
    def is_trend_detection_enabled(self):
        """Check if trend detection is enabled."""
        return self.get('TREND_DETECTION.enable_anomaly_detection', False)
    
    def get_health_score_weights(self):
        """Get health score calculation weights."""
        return self.get('ANALYTICS.health_score_weights', {})
    
    def reload(self):
        """Reload settings from Django configuration."""
        self._load_settings()


# Global configuration instance
event_viewer_config = EventViewerConfig()


def get_setting(key, default=None):
    """Convenience function to get Event Viewer settings."""
    return event_viewer_config.get(key, default)


def get_alert_threshold(threshold_name):
    """Convenience function to get alert thresholds."""
    return event_viewer_config.get_alert_threshold(threshold_name)


def get_retention_days(policy_name='default_retention_days'):
    """Convenience function to get retention days."""
    return event_viewer_config.get_retention_days(policy_name)