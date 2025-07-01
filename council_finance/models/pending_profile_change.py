from django.conf import settings
from django.db import models


class PendingProfileChange(models.Model):
    """Store pending updates that require email confirmation."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Random token emailed to the user to confirm the change
    token = models.CharField(max_length=64, unique=True)
    new_first_name = models.CharField(max_length=150, blank=True)
    new_last_name = models.CharField(max_length=150, blank=True)
    new_email = models.EmailField(blank=True)
    new_password = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Pending change for {self.user}" \
            f" ({self.created_at:%Y-%m-%d})"
