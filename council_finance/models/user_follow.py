from django.conf import settings
from django.db import models


class UserFollow(models.Model):
    """Simple follower relationship between users."""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following",
        on_delete=models.CASCADE,
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="followers",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate follow relationships
        unique_together = ("follower", "target")

    def __str__(self) -> str:
        return f"{self.follower} follows {self.target}"
