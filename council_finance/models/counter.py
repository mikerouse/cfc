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
    # How many decimal places should be shown when this counter is rendered
    precision = models.PositiveIntegerField(
        default=0,
        help_text="Decimal places to display",
    )
    # Whether the value should be shown with a leading currency symbol and commas
    show_currency = models.BooleanField(
        default=True,
        help_text="Prefix with £ and include comma separators",
    )
    # Use friendly format like £1m for large numbers
    friendly_format = models.BooleanField(
        default=False,
        help_text="Use short forms e.g. £1m",
    )
    # Control whether this counter should appear on council pages when no
    # explicit CouncilCounter override exists. Admins can opt out per council
    # using the inline model or opt in globally here.
    show_by_default = models.BooleanField(
        default=True,
        help_text="Show on council pages unless disabled for a specific council",
    )
    # When marked as a headline counter it will be emphasised on the front end
    # and shown before any other counters.
    headline = models.BooleanField(
        default=False,
        help_text="Highlight this counter as a headline figure",
    )
    # Restrict display to certain council types. Empty set implies all types.
    council_types = models.ManyToManyField(
        "council_finance.CouncilType",
        blank=True,
        help_text="Council types this counter applies to",
    )

    def save(self, *args, **kwargs):
        """Auto-generate a slug from the name when missing."""
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)
            slug = base
            i = 1
            while CounterDefinition.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def format_value(self, value: float) -> str:
        """Return the value formatted according to the settings."""
        # This helper keeps formatting rules in one place so templates and
        # agents can rely on a consistent representation of numbers.
        # Ensure we are dealing with a numeric value
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "0"

        # Apply "friendly" formatting if requested
        if self.friendly_format:
            abs_val = abs(value)
            if abs_val >= 1_000_000_000:
                value_str = f"{value / 1_000_000_000:.1f}b"
            elif abs_val >= 1_000_000:
                value_str = f"{value / 1_000_000:.1f}m"
            elif abs_val >= 1_000:
                value_str = f"{value / 1_000:.1f}k"
            else:
                value_str = f"{value:.{self.precision}f}"
        else:
            value_str = (
                f"{value:,.{self.precision}f}"
                if self.show_currency
                else f"{value:.{self.precision}f}"
            )

        if self.show_currency:
            return f"£{value_str}"
        return value_str

    def __str__(self) -> str:
        return self.name

    def display_council_types(self) -> str:
        """Helper for admin list view."""
        names = [ct.name for ct in self.council_types.all()]
        return ", ".join(names) if names else "All"


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
