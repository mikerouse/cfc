from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Simple in-app notification that can optionally also be emailed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    # Flags so the system can later decide how to deliver this message
    email = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Notification for {self.user}: {self.message}"

