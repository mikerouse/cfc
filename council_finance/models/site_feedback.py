from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator


class SiteFeedback(models.Model):
    """
    Captures user feedback for pre-alpha testing and ongoing improvements.
    
    Designed for early release testing to capture:
    - Bug reports with context
    - Feature suggestions 
    - Usability issues
    - General feedback
    """
    
    FEEDBACK_TYPES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('improvement', 'Improvement Suggestion'),
        ('usability', 'Usability Issue'),
        ('content', 'Content Issue'),
        ('performance', 'Performance Issue'),
        ('general', 'General Feedback'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low - Minor issue or suggestion'),
        ('medium', 'Medium - Affects functionality'),
        ('high', 'High - Major problem or blocker'),
        ('critical', 'Critical - Site unusable'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('wont_fix', 'Won\'t Fix'),
        ('duplicate', 'Duplicate'),
    ]
    
    # Core feedback details
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_TYPES,
        default='general',
        help_text="What type of feedback is this?"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Brief summary of the issue or suggestion"
    )
    
    description = models.TextField(
        validators=[MaxLengthValidator(2000)],
        help_text="Detailed description of the issue, suggestion, or feedback"
    )
    
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium',
        help_text="How severe is this issue?"
    )
    
    # Context information (crucial for debugging)
    page_url = models.URLField(
        blank=True,
        help_text="URL where the issue occurred"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="Browser and device information"
    )
    
    screen_resolution = models.CharField(
        max_length=50,
        blank=True,
        help_text="Screen resolution when issue occurred"
    )
    
    steps_to_reproduce = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(1000)],
        help_text="Steps to reproduce the issue (for bugs)"
    )
    
    expected_behaviour = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500)],
        help_text="What did you expect to happen?"
    )
    
    actual_behaviour = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500)],
        help_text="What actually happened?"
    )
    
    # User information
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who submitted the feedback (if logged in)"
    )
    
    contact_email = models.EmailField(
        blank=True,
        help_text="Email address for follow-up (optional)"
    )
    
    contact_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name for follow-up (optional)"
    )
    
    # Metadata
    submitted_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # Administrative fields
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        help_text="Current status of this feedback"
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes for administrators"
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this feedback was resolved"
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_feedback',
        help_text="Administrator who resolved this feedback"
    )
    
    # For feature requests and improvements
    votes = models.PositiveIntegerField(
        default=0,
        help_text="Number of users who upvoted this suggestion"
    )

    class Meta:
        verbose_name = "Site Feedback"
        verbose_name_plural = "Site Feedback"
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['feedback_type', 'status']),
            models.Index(fields=['severity', 'submitted_at']),
            models.Index(fields=['status', 'submitted_at']),
        ]

    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.title}"
    
    @property
    def is_bug(self):
        """Check if this is a bug report."""
        return self.feedback_type == 'bug'
    
    @property  
    def is_resolved(self):
        """Check if this feedback has been resolved."""
        return self.status in ['resolved', 'wont_fix']
    
    @property
    def age_in_days(self):
        """Calculate how many days since submission."""
        return (timezone.now() - self.submitted_at).days
    
    def mark_as_resolved(self, resolved_by_user=None):
        """Mark this feedback as resolved."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        if resolved_by_user:
            self.resolved_by = resolved_by_user
        self.save(update_fields=['status', 'resolved_at', 'resolved_by'])
    
    def get_priority_score(self):
        """Calculate priority score for triage (higher = more urgent)."""
        severity_scores = {
            'critical': 4,
            'high': 3, 
            'medium': 2,
            'low': 1
        }
        
        type_multipliers = {
            'bug': 1.5,
            'performance': 1.3,
            'usability': 1.2,
            'feature': 1.0,
            'improvement': 1.0,
            'content': 0.8,
            'general': 0.7
        }
        
        base_score = severity_scores.get(self.severity, 2)
        type_multiplier = type_multipliers.get(self.feedback_type, 1.0)
        
        # Age factor - older items get slight priority boost
        age_boost = min(self.age_in_days * 0.1, 2.0)
        
        return (base_score * type_multiplier) + age_boost
    
    def log_to_event_viewer(self, request=None):
        """Log this feedback submission to the Event Viewer system."""
        try:
            from event_viewer.models import SystemEvent
            
            # Map feedback severity to SystemEvent levels
            severity_to_level = {
                'critical': 'critical',
                'high': 'error',
                'medium': 'warning',
                'low': 'info'
            }
            
            level = severity_to_level.get(self.severity, 'info')
            
            # Create contextual details
            details = {
                'feedback_id': self.id,
                'feedback_type': self.feedback_type,
                'severity': self.severity,
                'page_url': self.page_url,
                'has_contact_info': bool(self.contact_email or self.contact_name),
                'steps_provided': bool(self.steps_to_reproduce),
                'priority_score': round(self.get_priority_score(), 2)
            }
            
            if self.user_agent:
                details['user_agent'] = self.user_agent[:200]  # Truncate for storage
            
            if self.screen_resolution:
                details['screen_resolution'] = self.screen_resolution
            
            # Create SystemEvent
            SystemEvent.objects.create(
                source='site_feedback',
                level=level,
                category='user_feedback',  # New category for feedback
                title=f'{self.get_feedback_type_display()}: {self.title}',
                message=self.description[:500],  # Truncate for overview
                user=self.user,
                details=details,
                tags=[
                    'feedback',
                    self.feedback_type,
                    self.severity,
                    'pre_alpha' if 'pre-alpha' in self.title.lower() else 'general'
                ],
                fingerprint=f'feedback_{self.feedback_type}_{self.severity}'
            )
            
            return True
            
        except Exception as e:
            # Don't fail feedback submission if logging fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log feedback {self.id} to Event Viewer: {e}")
            return False
    
    def save(self, *args, **kwargs):
        """Override save to automatically log to Event Viewer and send email on creation."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Log to Event Viewer and send email for new submissions
        if is_new:
            self.log_to_event_viewer()
            self.send_email_notification()
    
    def send_email_notification(self):
        """Send email notification for this feedback submission."""
        try:
            from council_finance.services.feedback_notifications import send_feedback_notification
            return send_feedback_notification(self)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email notification for feedback {self.id}: {e}")
            return False


class SiteAnnouncement(models.Model):
    """
    Site-wide announcements banner system.
    
    Allows administrators to display important messages to all users,
    such as maintenance notices, new features, or testing phases.
    """
    
    ANNOUNCEMENT_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error/Alert'),
        ('maintenance', 'Maintenance'),
        ('feature', 'New Feature'),
        ('test', 'Testing Phase'),
    ]
    
    title = models.CharField(
        max_length=200,
        help_text="Main announcement text"
    )
    
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500)],
        help_text="Additional details (optional)"
    )
    
    announcement_type = models.CharField(
        max_length=20,
        choices=ANNOUNCEMENT_TYPES,
        default='info',
        help_text="Visual style and importance level"
    )
    
    link_text = models.CharField(
        max_length=100,
        blank=True,
        help_text="Text for action link (optional)"
    )
    
    link_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL for action link (can be internal path or external URL)"
    )
    
    # Display settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this announcement is currently displayed"
    )
    
    is_dismissible = models.BooleanField(
        default=True,
        help_text="Whether users can dismiss this announcement"
    )
    
    show_on_all_pages = models.BooleanField(
        default=True,
        help_text="Show on all pages or just homepage"
    )
    
    # Scheduling
    start_date = models.DateTimeField(
        default=timezone.now,
        help_text="When to start showing this announcement"
    )
    
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to stop showing this announcement (optional)"
    )
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Administrator who created this announcement"
    )
    
    # Analytics
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this announcement was displayed"
    )
    
    click_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times the action link was clicked"
    )

    class Meta:
        verbose_name = "Site Announcement"
        verbose_name_plural = "Site Announcements"  
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.get_announcement_type_display()}: {self.title}"
    
    @property
    def is_currently_active(self):
        """Check if announcement should be displayed now."""
        now = timezone.now()
        
        if not self.is_active:
            return False
            
        if now < self.start_date:
            return False
            
        if self.end_date and now > self.end_date:
            return False
            
        return True
    
    def increment_views(self):
        """Increment view counter."""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_clicks(self):
        """Increment click counter."""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    @property
    def click_through_rate(self):
        """Calculate click-through rate as percentage."""
        if self.view_count == 0:
            return 0
        return round((self.click_count / self.view_count) * 100, 2)