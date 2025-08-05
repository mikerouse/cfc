"""
Event Viewer Models

Complements the existing ActivityLog system by providing:
1. Error and exception tracking
2. Performance monitoring
3. System health metrics
4. Log file parsing storage

This does NOT replace ActivityLog - it extends the monitoring capabilities.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()


class SystemEvent(models.Model):
    """
    Unified event tracking for errors, performance, and system health.
    Complements ActivityLog by focusing on technical events rather than user actions.
    """
    
    # Event Sources - what generated this event
    EVENT_SOURCES = [
        ('django_error', 'Django Error Handler'),
        ('middleware', 'Error Middleware'),
        ('log_parser', 'Log File Parser'),
        ('performance', 'Performance Monitor'),
        ('ai_system', 'AI System'),
        ('test_runner', 'Test Runner'),
        ('cache', 'Cache System'),
        ('database', 'Database'),
        ('api', 'API Endpoint'),
        ('background_task', 'Background Task'),
        ('user_report', 'User Report'),
        ('health_check', 'Health Check'),
    ]
    
    # Event Levels - severity/importance
    EVENT_LEVELS = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    # Event Categories - what kind of event
    EVENT_CATEGORIES = [
        ('exception', 'Exception/Error'),
        ('performance', 'Performance Issue'),
        ('security', 'Security Event'),
        ('data_quality', 'Data Quality Issue'),
        ('integration', 'External Integration'),
        ('resource', 'Resource Issue'),
        ('configuration', 'Configuration Issue'),
        ('test_failure', 'Test Failure'),
    ]
    
    # Core fields
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    source = models.CharField(max_length=50, choices=EVENT_SOURCES, db_index=True)
    level = models.CharField(max_length=20, choices=EVENT_LEVELS, db_index=True)
    category = models.CharField(max_length=50, choices=EVENT_CATEGORIES, db_index=True)
    
    # Event description
    title = models.CharField(max_length=255, help_text="Brief description of the event")
    message = models.TextField(help_text="Detailed event message")
    
    # Error specific fields
    exception_type = models.CharField(max_length=100, blank=True, db_index=True)
    exception_value = models.TextField(blank=True)
    stack_trace = models.TextField(blank=True)
    
    # Context
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='system_events'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True, db_index=True)
    request_method = models.CharField(max_length=10, blank=True)
    
    # Performance metrics
    duration_ms = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Duration in milliseconds for performance events"
    )
    memory_mb = models.IntegerField(
        null=True,
        blank=True,
        help_text="Memory usage in MB"
    )
    
    # Related object (optional)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Structured data storage
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about the event"
    )
    
    # Tags for filtering and grouping
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tags for categorization"
    )
    
    # Resolution tracking
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_events'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Grouping similar events
    fingerprint = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Hash to group similar events together"
    )
    occurrence_count = models.IntegerField(default=1)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'level']),
            models.Index(fields=['source', 'timestamp']),
            models.Index(fields=['resolved', 'level', 'timestamp']),
            models.Index(fields=['exception_type', 'timestamp']),
            models.Index(fields=['fingerprint', 'timestamp']),
        ]
        verbose_name = "System Event"
        verbose_name_plural = "System Events"
    
    def __str__(self):
        return f"[{self.get_level_display()}] {self.title} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Auto-generate fingerprint for grouping similar events
        if not self.fingerprint and self.exception_type:
            # Simple fingerprint based on exception type and key details
            fingerprint_parts = [
                self.exception_type,
                self.source,
                self.request_path or 'no-path',
            ]
            self.fingerprint = '-'.join(fingerprint_parts)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def create_from_exception(cls, exception, request=None, source='django_error', extra_context=None):
        """
        Create a SystemEvent from a Python exception.
        """
        import traceback
        
        event = cls(
            source=source,
            level='error',
            category='exception',
            title=f"{exception.__class__.__name__}: {str(exception)[:200]}",
            message=str(exception),
            exception_type=exception.__class__.__name__,
            exception_value=str(exception),
            stack_trace=traceback.format_exc(),
        )
        
        # Add request context if available
        if request:
            event.user = request.user if request.user.is_authenticated else None
            event.request_path = request.path
            event.request_method = request.method
            event.ip_address = cls._get_client_ip(request)
            event.user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Add request details to context
            if extra_context is None:
                extra_context = {}
            extra_context['request_data'] = {
                'GET': dict(request.GET),
                'POST': cls._sanitize_data(dict(request.POST)),
                'COOKIES': cls._sanitize_data(dict(request.COOKIES)),
            }
        
        if extra_context:
            event.details = extra_context
        
        event.save()
        return event
    
    @staticmethod
    def _get_client_ip(request):
        """Extract the real IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _sanitize_data(data):
        """Remove sensitive data from dictionaries."""
        sensitive_keys = ['password', 'token', 'secret', 'api_key', 'csrf']
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        return sanitized
    
    def mark_resolved(self, user, notes=''):
        """Mark this event as resolved."""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.resolution_notes = notes
        self.save()
    
    def is_recent(self, hours=1):
        """Check if this event is recent."""
        return self.timestamp >= timezone.now() - timedelta(hours=hours)
    
    def get_similar_events(self, limit=10):
        """Get similar events based on fingerprint."""
        if not self.fingerprint:
            return SystemEvent.objects.none()
        
        return SystemEvent.objects.filter(
            fingerprint=self.fingerprint
        ).exclude(id=self.id).order_by('-timestamp')[:limit]
    
    @property
    def level_css_class(self):
        """Return GOV.UK style CSS class for the level."""
        return {
            'debug': 'govuk-tag--grey',
            'info': 'govuk-tag--blue',
            'warning': 'govuk-tag--yellow',
            'error': 'govuk-tag--red',
            'critical': 'govuk-tag--red',
        }.get(self.level, 'govuk-tag--grey')


class EventSummary(models.Model):
    """
    Daily summary of events for analytics and trending.
    """
    
    date = models.DateField(unique=True)
    
    # Event counts by level
    debug_count = models.IntegerField(default=0)
    info_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    critical_count = models.IntegerField(default=0)
    
    # Event counts by category
    exception_count = models.IntegerField(default=0)
    performance_count = models.IntegerField(default=0)
    security_count = models.IntegerField(default=0)
    data_quality_count = models.IntegerField(default=0)
    
    # Performance metrics
    avg_response_time_ms = models.FloatField(null=True, blank=True)
    max_response_time_ms = models.IntegerField(null=True, blank=True)
    slow_request_count = models.IntegerField(default=0)
    
    # User metrics
    unique_users_affected = models.IntegerField(default=0)
    unique_ips = models.IntegerField(default=0)
    
    # Resolution metrics
    events_resolved = models.IntegerField(default=0)
    avg_resolution_hours = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Event Summary"
        verbose_name_plural = "Event Summaries"
    
    def __str__(self):
        return f"Event Summary for {self.date}"
    
    @classmethod
    def generate_for_date(cls, date):
        """Generate or update summary for a specific date."""
        from django.db.models import Count, Avg, Max, Q
        
        # Get all events for the date
        start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
        end = start + timedelta(days=1)
        
        events = SystemEvent.objects.filter(
            timestamp__gte=start,
            timestamp__lt=end
        )
        
        # Calculate metrics
        summary, created = cls.objects.get_or_create(date=date)
        
        # Level counts
        level_counts = events.values('level').annotate(count=Count('id'))
        for item in level_counts:
            setattr(summary, f"{item['level']}_count", item['count'])
        
        # Category counts
        category_counts = events.values('category').annotate(count=Count('id'))
        for item in category_counts:
            setattr(summary, f"{item['category']}_count", item['count'])
        
        # Performance metrics
        perf_events = events.filter(category='performance', duration_ms__isnull=False)
        if perf_events.exists():
            summary.avg_response_time_ms = perf_events.aggregate(Avg('duration_ms'))['duration_ms__avg']
            summary.max_response_time_ms = perf_events.aggregate(Max('duration_ms'))['duration_ms__max']
            summary.slow_request_count = perf_events.filter(duration_ms__gt=1000).count()
        
        # User metrics
        summary.unique_users_affected = events.exclude(user__isnull=True).values('user').distinct().count()
        summary.unique_ips = events.exclude(ip_address__isnull=True).values('ip_address').distinct().count()
        
        # Resolution metrics
        resolved_events = events.filter(resolved=True)
        summary.events_resolved = resolved_events.count()
        
        summary.save()
        return summary
