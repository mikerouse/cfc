"""
Activity Log Comment model for Following feed integration.

Allows users to comment on ActivityLog entries when viewing them in the Following feed.
This provides social interaction around council activity data.
"""

from django.conf import settings
from django.db import models
from .activity_log import ActivityLog


class ActivityLogComment(models.Model):
    """
    Comments on ActivityLog entries displayed in the Following feed.
    
    This allows users to discuss and provide context around specific
    council activities they're following.
    """
    
    # The activity log entry being commented on
    activity_log = models.ForeignKey(
        ActivityLog,
        on_delete=models.CASCADE,
        related_name='following_comments',
        help_text="The activity log entry this comment relates to"
    )
    
    # User who made the comment
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_log_comments',
        help_text="User who made this comment"
    )
    
    # Comment content
    content = models.TextField(
        help_text="The comment content"
    )
    
    # Threading support for replies
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text="Parent comment if this is a reply"
    )
    
    # Moderation fields
    is_approved = models.BooleanField(
        default=True,
        help_text="Whether this comment is approved for display"
    )
    
    is_flagged = models.BooleanField(
        default=False,
        help_text="Whether this comment has been flagged for review"
    )
    
    # Engagement metrics
    like_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of likes this comment has received"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this comment was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this comment was last updated"
    )
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['activity_log', 'is_approved', 'created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_flagged']),
        ]
    
    def __str__(self):
        activity_desc = self.activity_log.description[:50] + "..." if len(self.activity_log.description) > 50 else self.activity_log.description
        return f"Comment by {self.user.username} on '{activity_desc}'"
    
    def get_reply_count(self):
        """Get the number of approved replies to this comment."""
        return self.replies.filter(is_approved=True).count()
    
    def is_reply(self):
        """Check if this comment is a reply to another comment."""
        return self.parent is not None
    
    def get_thread_root(self):
        """Get the root comment of this thread."""
        if self.parent is None:
            return self
        
        # Walk up the tree to find the root
        current = self
        while current.parent is not None:
            current = current.parent
        return current