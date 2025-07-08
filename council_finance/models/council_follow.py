from django.conf import settings
from django.db import models

from .council import Council


class CouncilFollow(models.Model):
    """Relationship tracking which users follow which councils."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="council_follows",
        on_delete=models.CASCADE,
    )
    council = models.ForeignKey(
        Council,
        related_name="followed_by",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "council")

    def __str__(self) -> str:
        return f"{self.user} follows {self.council}"
