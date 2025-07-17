"""
Flagging system for community moderation.

This system allows users to flag content, contributions, and users for review.
Replaces the old pending approval system with a post-approval flagging system.
"""

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from datetime import timedelta

from .council import Council
from .field import DataField
from .contribution import Contribution


class Flag(models.Model):
    """
    A flag raised by a user against content, contributions, or other users.
    """
    
    FLAG_TYPES = [
        ('content_incorrect', 'Data is Incorrect'),
        ('content_outdated', 'Data is Outdated'),
        ('content_spam', 'Spam or Irrelevant'),
        ('content_duplicate', 'Duplicate Entry'),
        ('user_abuse', 'User Abuse/Harassment'),
        ('user_spam', 'User Spamming'),
        ('system_error', 'System/Technical Error'),
        ('other', 'Other (See Description)'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Who flagged this
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flags_raised'
    )
    
    # What was flagged (generic to support different content types)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    flagged_object = GenericForeignKey('content_type', 'object_id')
    
    # Flag details
    flag_type = models.CharField(max_length=20, choices=FLAG_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    description = models.TextField(help_text="Detailed description of the issue")
    
    # Moderation details
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_flags'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_flags'
    )
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # IP tracking for abuse prevention
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['flagged_by', '-created_at']),
            models.Index(fields=['priority', 'status']),
        ]
        # Prevent duplicate flags from the same user for the same object
        unique_together = ['flagged_by', 'content_type', 'object_id']
    
    def __str__(self):
        return f"Flag by {self.flagged_by} - {self.get_flag_type_display()}"
    
    @property
    def age_in_days(self):
        """How many days since this flag was raised."""
        return (timezone.now() - self.created_at).days
    
    @property
    def is_stale(self):
        """Flag is considered stale if open for more than 7 days."""
        return self.age_in_days > 7 and self.status == 'open'
    
    def mark_resolved(self, resolved_by, notes=""):
        """Mark this flag as resolved."""
        self.status = 'resolved'
        self.reviewed_by = resolved_by
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.resolved_at = timezone.now()
        self.save()
    
    def mark_dismissed(self, dismissed_by, notes=""):
        """Mark this flag as dismissed."""
        self.status = 'dismissed'
        self.reviewed_by = dismissed_by
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()


class FlaggedContent(models.Model):
    """
    Tracks content that has been flagged multiple times.
    Provides aggregated view for moderation.
    """
    
    # What content is flagged
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Flag statistics
    total_flags = models.PositiveIntegerField(default=0)
    unique_flaggers = models.PositiveIntegerField(default=0)
    first_flagged = models.DateTimeField(auto_now_add=True)
    last_flagged = models.DateTimeField(auto_now=True)
    
    # Status tracking
    is_under_review = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)  # Hide from public view
    
    # Auto-escalation thresholds
    auto_escalated = models.BooleanField(default=False)
    escalation_threshold = models.PositiveIntegerField(default=3)
    
    class Meta:
        ordering = ['-last_flagged']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['total_flags', '-last_flagged']),
            models.Index(fields=['is_under_review', 'is_resolved']),
        ]
        unique_together = ['content_type', 'object_id']
    
    def __str__(self):
        return f"{self.total_flags} flags for {self.content_object}"
    
    def should_auto_escalate(self):
        """Check if this content should be auto-escalated for review."""
        return (
            self.total_flags >= self.escalation_threshold and 
            not self.auto_escalated and 
            not self.is_under_review
        )
    
    def escalate(self):
        """Mark content for automatic escalation."""
        self.auto_escalated = True
        self.is_under_review = True
        self.save()
    
    def get_flags(self):
        """Get all flags for this content."""
        return Flag.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id
        ).select_related('flagged_by').order_by('-created_at')
    
    @property
    def flags(self):
        """Property to access flags like a related manager."""
        return self.get_flags()
    
    @property
    def status(self):
        """Get status for template compatibility."""
        if self.is_resolved:
            return 'resolved'
        elif self.is_under_review:
            return 'under_review'
        else:
            return 'open'
    
    @property
    def priority(self):
        """Get highest priority from associated flags."""
        flags = self.get_flags()
        if not flags:
            return 'low'
        
        priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        highest_priority = max(flags, key=lambda f: priority_order.get(f.priority, 1))
        return highest_priority.priority
    
    @property
    def flag_count(self):
        """Alias for total_flags for template compatibility."""
        return self.total_flags

    def add_flag(self, flag):
        """Add a new flag to this content."""
        self.total_flags += 1
        self.unique_flaggers = Flag.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id
        ).values('flagged_by').distinct().count()
        self.last_flagged = timezone.now()
        self.save()
        
        # Check for auto-escalation
        if self.should_auto_escalate():
            self.escalate()


class UserModerationRecord(models.Model):
    """
    Tracks moderation actions for users (warnings, suspensions, etc.)
    """
    
    ACTION_TYPES = [
        ('warning', 'Warning'),
        ('temp_ban', 'Temporary Ban'),
        ('perm_ban', 'Permanent Ban'),
        ('flag_limit', 'Flag Submission Limit'),
        ('contrib_limit', 'Contribution Limit'),
        ('restored', 'Privileges Restored'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderation_records'
    )
    action = models.CharField(max_length=15, choices=ACTION_TYPES)
    reason = models.TextField()
    
    # Duration for temporary actions
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Who took the action
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='moderation_actions'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Flag or contribution that triggered this action
    related_flag = models.ForeignKey(Flag, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} for {self.user.username}"
    
    @property
    def is_active(self):
        """Check if this moderation action is still active."""
        if self.expires_at:
            return timezone.now() < self.expires_at
        return self.action in ['perm_ban', 'flag_limit', 'contrib_limit']
    
    @property
    def time_remaining(self):
        """Time remaining for temporary actions."""
        if self.expires_at and self.is_active:
            return self.expires_at - timezone.now()
        return None


class FlagComment(models.Model):
    """
    Comments on flags for discussion between moderators.
    """
    
    flag = models.ForeignKey(Flag, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Flag this comment as important
    is_important = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on Flag #{self.flag.id}"
