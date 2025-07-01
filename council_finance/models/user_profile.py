from django.conf import settings
from django.db import models

from .council import Council


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

    def __str__(self) -> str:
        return f"Profile for {self.user.username}"
