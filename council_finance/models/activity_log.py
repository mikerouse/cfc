from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import json

from .council import Council

class ActivityLog(models.Model):
    """Modern activity logging system for tracking user actions and system events.
    
    Supports both specific council-related activities and general system activities.
    Provides audit trails for Wikipedia-like collaborative editing and God Mode operations.
    """

    # Core fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who performed the action (null for system actions)"
    )
    
    # Activity classification
    ACTIVITY_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('merge', 'Merge'),
        ('import', 'Import'),
        ('export', 'Export'),
        ('auth', 'Authentication'),
        ('system', 'System'),
        ('moderation', 'Moderation'),
        ('contribution', 'Contribution'),
        ('council_merge', 'Council Merge'),
        ('financial_year', 'Financial Year Management'),
        ('data_correction', 'Data Correction'),
        ('bulk_operation', 'Bulk Operation'),
    ]
    
    activity_type = models.CharField(
        max_length=20, 
        choices=ACTIVITY_TYPES,
        default='system',
        help_text="Type of activity performed"
    )
    
    description = models.CharField(
        max_length=255,
        default='Legacy activity',
        help_text="Human-readable description of the activity"
    )
    
    # Status tracking
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed',
        help_text="Status of the activity"
    )
    
    # Council relationship (for council-specific activities)
    related_council = models.ForeignKey(
        Council, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='activity_logs',
        help_text="Council this activity relates to (if applicable)"
    )
    
    # Generic foreign key for relating to any model
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Detailed information storage
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about the activity"
    )
    
    # Context information
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        help_text="IP address of the user"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    # Timing
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Legacy fields for backward compatibility
    page = models.CharField(max_length=100, blank=True)
    activity = models.CharField(max_length=100, blank=True)
    log_type = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=100, blank=True)
    request = models.CharField(max_length=255, blank=True)
    response = models.CharField(max_length=255, blank=True)
    extra = models.TextField(blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=['user', '-created']),
            models.Index(fields=['related_council', '-created']),
            models.Index(fields=['activity_type', '-created']),
            models.Index(fields=['status', '-created']),
        ]

    def __str__(self) -> str:
        user_str = self.user.username if self.user else 'System'
        council_str = f" for {self.related_council.name}" if self.related_council else ""
        return f"{self.get_activity_type_display()}: {self.description} by {user_str}{council_str}"
    
    @classmethod
    def log_activity(cls, activity_type, description, user=None, related_council=None, 
                    content_object=None, details=None, status='completed', request=None):
        """Convenience method for creating activity logs."""
        
        # Extract IP and user agent from request if provided
        ip_address = None
        user_agent = ''
        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            status=status,
            related_council=related_council,
            content_object=content_object,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extract the real IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_details_display(self):
        """Return a formatted version of details for display."""
        if not self.details:
            return ""
        
        if isinstance(self.details, dict):
            return json.dumps(self.details, indent=2)
        return str(self.details)
    
    def is_recent(self, hours=1):
        """Check if this activity is recent (within specified hours)."""
        from django.utils import timezone
        from datetime import timedelta
        return self.created >= timezone.now() - timedelta(hours=hours)

