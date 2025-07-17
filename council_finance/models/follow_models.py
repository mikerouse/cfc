"""
Enhanced Following system models to support comprehensive social features.

Supports following councils, lists, financial figures, and contributors with
prioritized feeds, filtering, and telemetry collection.
"""

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from .council import Council
from .council_list import CouncilList
from .field import DataField


class FollowableItem(models.Model):
    """
    Generic following system that supports multiple types of followable content.
    Uses Django's contenttypes framework for flexibility.
    """
    
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('normal', 'Normal Priority'), 
        ('high', 'High Priority'),
        ('critical', 'Critical Priority'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follows'
    )
    
    # Generic foreign key to support following different types of objects
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # User preferences for this follow
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    # Telemetry and engagement tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_viewed = models.DateTimeField(null=True, blank=True)
    interaction_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['user', 'priority']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'last_viewed']),
        ]
    
    def __str__(self):
        return f"{self.user} follows {self.content_object} ({self.priority})"
    
    def update_engagement(self):
        """Update engagement metrics when user interacts with this follow."""
        from django.utils import timezone
        self.last_viewed = timezone.now()
        self.interaction_count += 1
        self.save(update_fields=['last_viewed', 'interaction_count'])


class FeedUpdate(models.Model):
    """
    Enhanced feed update system that supports rich content and interactions.
    Replaces the basic CouncilUpdate with more flexible structure.
    """
    
    UPDATE_TYPES = [
        ('financial', 'Financial Data Update'),
        ('contribution', 'User Contribution'),
        ('council_news', 'Council News'),
        ('list_change', 'List Modification'),
        ('system', 'System Update'),
        ('achievement', 'User Achievement'),
    ]
    
    # Source of the update - generic to support different content types
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    source_object = GenericForeignKey('content_type', 'object_id')
    
    # Update details
    update_type = models.CharField(max_length=20, choices=UPDATE_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    rich_content = models.JSONField(default=dict, blank=True)  # For charts, images, etc.
    
    # User who triggered the update (if applicable)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='authored_updates'
    )
    
    # Visibility and targeting
    is_public = models.BooleanField(default=True)
    targeted_followers_only = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Engagement metrics
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['update_type', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['is_public', '-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.update_type}: {self.title}"
    
    def increment_views(self):
        """Atomically increment view count."""
        FeedUpdate.objects.filter(id=self.id).update(view_count=models.F('view_count') + 1)
        
    def get_related_object_name(self):
        """Get a human-readable name for the related object."""
        if hasattr(self.source_object, 'name'):
            return self.source_object.name
        elif hasattr(self.source_object, 'title'):
            return self.source_object.title
        elif hasattr(self.source_object, '__str__'):
            return str(self.source_object)
        return "Unknown"


class FeedInteraction(models.Model):
    """
    User interactions with feed updates (likes, shares, etc.).
    """
    
    INTERACTION_TYPES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
        ('share', 'Share'),
        ('bookmark', 'Bookmark'),
        ('flag', 'Flag as Inappropriate'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    update = models.ForeignKey(FeedUpdate, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=10, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Additional context for some interaction types
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('user', 'update', 'interaction_type')
        indexes = [
            models.Index(fields=['update', 'interaction_type']),
            models.Index(fields=['user', 'interaction_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} {self.interaction_type}d {self.update.title}"


class FeedComment(models.Model):
    """
    Enhanced commenting system for feed updates.
    """
    
    update = models.ForeignKey(FeedUpdate, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    
    # Threading support for replies
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Engagement
    like_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['update', 'is_approved', 'created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user} on {self.update.title}"
    
    def get_reply_count(self):
        """Get the number of replies to this comment."""
        return self.replies.filter(is_approved=True).count()


class UserFeedPreferences(models.Model):
    """
    User preferences for their personalized feed.
    """
    
    FEED_ALGORITHMS = [
        ('chronological', 'Chronological (Newest First)'),
        ('engagement', 'High Engagement First'),
        ('priority', 'Your Priorities First'),
        ('mixed', 'Smart Mix (Recommended)'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='feed_preferences'
    )
    
    # Feed algorithm preference
    algorithm = models.CharField(max_length=20, choices=FEED_ALGORITHMS, default='mixed')
    
    # Content type filters
    show_financial_updates = models.BooleanField(default=True)
    show_contributions = models.BooleanField(default=True)
    show_council_news = models.BooleanField(default=True)
    show_list_changes = models.BooleanField(default=True)
    show_system_updates = models.BooleanField(default=False)
    show_achievements = models.BooleanField(default=True)
    
    # Engagement preferences
    auto_mark_read = models.BooleanField(default=False)
    digest_frequency = models.CharField(
        max_length=10,
        choices=[
            ('realtime', 'Real-time'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('never', 'Never'),
        ],
        default='realtime'
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    notification_quiet_hours_start = models.TimeField(null=True, blank=True)
    notification_quiet_hours_end = models.TimeField(null=True, blank=True)
    
    # Privacy settings
    public_activity = models.BooleanField(default=True)
    show_in_suggestions = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Feed preferences for {self.user}"


class TrendingContent(models.Model):
    """
    Track trending content for algorithmic promotion.
    """
    
    CONTENT_TYPES = [
        ('council', 'Council'),
        ('list', 'Council List'),
        ('contributor', 'User/Contributor'),
        ('field', 'Financial Field'),
        ('update', 'Feed Update'),
    ]
    
    # What's trending
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Trending metrics
    trend_score = models.FloatField(default=0.0)
    follow_velocity = models.FloatField(default=0.0)  # Rate of new follows
    engagement_velocity = models.FloatField(default=0.0)  # Rate of interactions
    view_velocity = models.FloatField(default=0.0)  # Rate of views
    
    # Time windows for trend calculation
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Metadata
    reason = models.TextField(blank=True)  # Why this is trending
    is_promoted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-trend_score']
        indexes = [
            models.Index(fields=['-trend_score', 'is_promoted']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"Trending: {self.content_object} (score: {self.trend_score:.2f})"
