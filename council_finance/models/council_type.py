from django.db import models


class CouncilType(models.Model):
    """Represents a configurable council type (e.g. Unitary)."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Council type"
        verbose_name_plural = "Council types"

    def __str__(self) -> str:
        return self.name
