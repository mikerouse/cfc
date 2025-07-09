from django.conf import settings
from django.db import models

from .council import Council

class ActivityLog(models.Model):
    """Record significant user actions to aid troubleshooting."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    council = models.ForeignKey(
        Council, on_delete=models.SET_NULL, null=True, blank=True
    )
    page = models.CharField(max_length=100)
    activity = models.CharField(max_length=100)
    button = models.CharField(max_length=100, blank=True)
    action = models.CharField(max_length=100, blank=True)
    response = models.CharField(max_length=255, blank=True)
    extra = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.page}: {self.activity} by {self.user or 'anon'}"
