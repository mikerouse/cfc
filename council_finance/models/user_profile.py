from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
import datetime

from .council import Council
from .trust_tier import TrustTier


class UserProfile(models.Model):
    """Extra details linked to a Django ``User``."""

    # Each user gets exactly one profile created for them.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # Optional UK postal code for the account holder.
    postcode = models.CharField(max_length=20, blank=True)
    # When a user explicitly refuses to provide a postcode we still
    # record that fact so we don't continue to prompt them.
    postcode_refused = models.BooleanField(default=False)
    # Councils the user has marked as favourites.
    favourites = models.ManyToManyField(Council, blank=True, related_name="fans")
    # Enhanced email confirmation system
    email_confirmed = models.BooleanField(default=False)
    confirmation_token = models.CharField(max_length=64, blank=True)
    
    # Pending email change system
    pending_email = models.EmailField(blank=True, help_text="New email address awaiting confirmation")
    pending_email_token = models.CharField(max_length=64, blank=True)
    pending_email_expires = models.DateTimeField(null=True, blank=True)
    
    # Confirmation tracking
    last_confirmation_sent = models.DateTimeField(null=True, blank=True)
    confirmation_attempts = models.IntegerField(default=0)
    max_confirmation_attempts = models.IntegerField(default=5)
    
    # Security tracking
    email_confirmed_at = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    requires_reconfirmation = models.BooleanField(default=False, help_text="Requires email re-confirmation due to security changes")
    
    # Auth0 integration fields
    auth0_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="Auth0 user identifier")
    auth0_metadata = models.JSONField(default=dict, blank=True, help_text="Additional Auth0 user metadata")
    last_login_method = models.CharField(max_length=50, blank=True, help_text="Last authentication method used")
    
    # OSA Compliance fields
    date_of_birth = models.DateField(null=True, blank=True, help_text="Required for Online Safety Act compliance")
    age_verified = models.BooleanField(default=False, help_text="User has completed age verification")
    is_uk_user = models.BooleanField(default=True, help_text="User is based in the United Kingdom")
    can_access_comments = models.BooleanField(default=True, help_text="User can access comments and feed sections")
    community_guidelines_accepted = models.BooleanField(default=False, help_text="User has accepted community guidelines")
    community_guidelines_accepted_at = models.DateTimeField(null=True, blank=True, help_text="When guidelines were accepted")
    
    # Geographic fields for enhanced location handling
    country = models.CharField(max_length=2, blank=True, help_text="ISO country code")
    # Visibility of this profile. Friends is the default.
    VISIBILITY_CHOICES = [
        ("private", "Private"),
        ("friends", "Friends only"),
        ("followers", "Followers only"),
        ("public", "Public"),
    ]
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default="friends"
    )
    # Trust tier controlling moderation rights. Defaults to tier 1.
    tier = models.ForeignKey(
        TrustTier,
        on_delete=models.PROTECT,
        default=1,
        related_name="users",
    )
    # Optional political party affiliation.
    political_affiliation = models.CharField(max_length=100, blank=True)
    # Council employment info used for automatic tier bump.
    works_for_council = models.BooleanField(default=False)
    employer_council = models.ForeignKey(
        Council,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )
    official_email = models.EmailField(blank=True)
    official_email_confirmed = models.BooleanField(default=False)
    official_email_token = models.CharField(max_length=64, blank=True)
    # Preferred Google Font used across the site. Defaults to Cairo to
    # provide a clean, modern feel. Users can override this from their
    # profile page.
    preferred_font = models.CharField(max_length=100, default="Cairo", blank=True)
    
    # Font size preference for better accessibility
    FONT_SIZE_CHOICES = [
        ("small", "Small (14px)"),
        ("medium", "Medium (16px)"),
        ("large", "Large (18px)"),
        ("extra-large", "Extra Large (20px)"),
    ]
    font_size = models.CharField(
        max_length=20, 
        choices=FONT_SIZE_CHOICES, 
        default="medium",
        help_text="Choose your preferred font size for better readability"
    )
    
    # High contrast mode for accessibility
    high_contrast_mode = models.BooleanField(
        default=False,
        help_text="Enable high contrast colors for better visibility"
    )
    
    # Color theme preference
    THEME_CHOICES = [
        ("auto", "Auto (follows system)"),
        ("light", "Light theme"),
        ("dark", "Dark theme"),
        ("high-contrast", "High contrast"),
    ]
    color_theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default="auto",
        help_text="Choose your preferred color theme"
    )
    
    # Gamification fields tracking contribution performance.
    points = models.IntegerField(default=0)
    rejection_count = models.IntegerField(default=0)
    # Number of unique IP addresses that have been verified via approved
    # submissions. This can be used to gauge trustworthiness of the account
    # based on consistent usage patterns.
    verified_ip_count = models.IntegerField(default=0)
    # Total number of contributions by this user that moderators approved.
    # Used for auto-approval thresholds.
    approved_submission_count = models.IntegerField(default=0)
    
    # Notification preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text="Receive email notifications for important updates"
    )
    contribution_notifications = models.BooleanField(
        default=True,
        help_text="Get notified when your contributions are reviewed"
    )
    council_update_notifications = models.BooleanField(
        default=False,
        help_text="Receive notifications about councils you follow"
    )
    weekly_digest = models.BooleanField(
        default=False,
        help_text="Receive a weekly summary of activity and updates"
    )

    def __str__(self) -> str:
        return f"Profile for {self.user.username}"

    def completion_percent(self) -> int:
        """Simple metric indicating how much optional data is filled in."""
        fields_total = 4
        completed = 0
        if self.postcode or self.postcode_refused:
            completed += 1
        if self.political_affiliation:
            completed += 1
        if self.employer_council:
            completed += 1
        if self.official_email_confirmed:
            completed += 1
        return int((completed / fields_total) * 100)

    # --- Gamification helpers -------------------------------------------------

    def level(self) -> int:
        """Return the numeric level derived from ``points``.

        Levels provide a simple progression system to reward active
        contributors. The thresholds below can be tweaked without
        requiring a database migration because they are computed on the
        fly. A higher level means the user has made more approved
        contributions.
        """

        # Ordered from highest to lowest so the first match is returned.
        thresholds = [
            (100, 5),
            (50, 4),
            (25, 3),
            (10, 2),
            (0, 1),
        ]
        for minimum, lvl in thresholds:
            if self.points >= minimum:
                return lvl
        return 1

    def badge(self) -> str:
        """Human readable badge for the current :py:meth:`level`."""

        badges = {
            1: "Newcomer",
            2: "Contributor",
            3: "Enthusiast",
            4: "Expert",
            5: "Champion",
        }
        return badges.get(self.level(), "Newcomer")

    # --- Email Confirmation helpers -------------------------------------------
    
    def can_send_confirmation(self) -> bool:
        """Check if user can send another confirmation email (rate limiting)."""
        if not self.last_confirmation_sent:
            return True
        
        # Allow one confirmation email every 5 minutes
        time_since_last = timezone.now() - self.last_confirmation_sent
        return time_since_last >= datetime.timedelta(minutes=5)
    
    def has_exceeded_confirmation_attempts(self) -> bool:
        """Check if user has exceeded maximum confirmation attempts."""
        return self.confirmation_attempts >= self.max_confirmation_attempts
    
    def generate_confirmation_token(self) -> str:
        """Generate a new confirmation token."""
        token = get_random_string(64)
        self.confirmation_token = token
        return token
    
    def generate_pending_email_token(self) -> str:
        """Generate a new token for pending email changes."""
        token = get_random_string(64)
        self.pending_email_token = token
        self.pending_email_expires = timezone.now() + datetime.timedelta(hours=24)
        return token
    
    def is_pending_email_expired(self) -> bool:
        """Check if pending email change has expired."""
        if not self.pending_email_expires:
            return True
        return timezone.now() > self.pending_email_expires
    
    def clear_pending_email(self):
        """Clear pending email change data."""
        self.pending_email = ''
        self.pending_email_token = ''
        self.pending_email_expires = None
    
    def confirm_email(self):
        """Mark email as confirmed."""
        self.email_confirmed = True
        self.email_confirmed_at = timezone.now()
        self.confirmation_token = ''
        self.confirmation_attempts = 0
        self.requires_reconfirmation = False
    
    def require_reconfirmation(self, reason="security_change"):
        """Mark account as requiring email re-confirmation."""
        self.requires_reconfirmation = True
        self.email_confirmed = False
        # Keep email_confirmed_at for reference but require new confirmation
    
    def get_confirmation_status(self) -> dict:
        """Get comprehensive confirmation status."""
        return {
            'email_confirmed': self.email_confirmed,
            'requires_reconfirmation': self.requires_reconfirmation,
            'has_pending_email': bool(self.pending_email),
            'pending_email_expired': self.is_pending_email_expired() if self.pending_email else False,
            'can_send_confirmation': self.can_send_confirmation(),
            'attempts_remaining': max(0, self.max_confirmation_attempts - self.confirmation_attempts),
            'confirmation_status': self._get_status_message()
        }
    
    def _get_status_message(self) -> str:
        """Get human-readable confirmation status message."""
        if self.email_confirmed and not self.requires_reconfirmation:
            return "Email confirmed"
        elif self.requires_reconfirmation:
            return "Email re-confirmation required"
        elif self.pending_email and not self.is_pending_email_expired():
            return f"Email change pending confirmation ({self.pending_email})"
        elif self.pending_email and self.is_pending_email_expired():
            return "Email change expired - please try again"
        elif self.has_exceeded_confirmation_attempts():
            return "Maximum confirmation attempts exceeded - contact support"
        else:
            return "Email confirmation required"
    
    # --- Onboarding helpers ---------------------------------------------------
    
    def needs_onboarding(self) -> bool:
        """Check if user needs to complete onboarding process."""
        user = self.user
        
        # Must have first and last name
        if not (user.first_name and user.last_name):
            return True
            
        # Must have completed age verification (OSA compliance)
        if not (self.date_of_birth and self.age_verified):
            return True
            
        # Must have accepted community guidelines
        if not self.community_guidelines_accepted:
            return True
        
        return False
    
    # --- Age verification helpers (OSA compliance) ---------------------------
    
    def age(self) -> int:
        """Calculate user's current age from date of birth."""
        if not self.date_of_birth:
            return None
        
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def is_adult(self) -> bool:
        """Check if user is 18 or older."""
        return self.age() >= 18 if self.age() is not None else False
    
    def is_legal_minimum_age(self) -> bool:
        """Check if user meets minimum age requirement (13+) for the platform."""
        return self.age() >= 13 if self.age() is not None else False
    
    def update_content_access(self):
        """Update content access permissions based on age."""
        if self.date_of_birth and self.age_verified:
            # OSA compliance: Under 18s cannot access user-generated content
            self.can_access_comments = self.is_adult()
            self.save()
