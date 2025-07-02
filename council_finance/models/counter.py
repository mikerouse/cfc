from django.db import models
from .council import Council


class CounterDefinition(models.Model):
    """Global definition for a counter displayed on council pages."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    # Store a simple formula listing figure field names separated by '+'
    formula = models.CharField(
        max_length=255,
        help_text="Fields to sum, e.g. 'total_debt+current_liabilities'",
    )
    explanation = models.TextField(blank=True)
    # Duration in milliseconds for the client side animation
    duration = models.PositiveIntegerField(default=2000)

    def __str__(self) -> str:
        return self.name


class CouncilCounter(models.Model):
    """Enable or disable a counter for a given council."""

    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    counter = models.ForeignKey(CounterDefinition, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("council", "counter")

    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"{self.council} - {self.counter} ({status})"
