from django.db import models

class TrustTier(models.Model):
    """Renameable trust levels controlling volunteer permissions."""

    level = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["level"]

    def __str__(self) -> str:
        return f"{self.name} (Tier {self.level})"
