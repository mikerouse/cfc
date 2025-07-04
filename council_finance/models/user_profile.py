from django.conf import settings
from django.db import models

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
    # Has the user verified their email address?
    email_confirmed = models.BooleanField(default=False)
    # Token used in confirmation links; blank when confirmed.
    confirmation_token = models.CharField(max_length=64, blank=True)
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
