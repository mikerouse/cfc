from django.conf import settings
from django.db import models
from .council import Council

class CouncilList(models.Model):
    """User created collection of councils."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="council_lists",
    )
    name = models.CharField(max_length=100)
    councils = models.ManyToManyField(Council, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"
