from django.db import models
from django.core.exceptions import ValidationError


# Slugs listed here are considered immutable. Staff can update the value
# associated with these fields but should never rename or remove them
# because other parts of the system rely on these identifiers.
PROTECTED_SLUGS = {
    "council_type",
    "council_name",
    "population",
    "households",
}

class DataField(models.Model):
    """Definition of a figure/field that can be populated for each council."""

    FIELD_CATEGORIES = [
        ("balance_sheet", "Balance Sheet"),
        ("cash_flow", "Cash Flow"),
        ("income", "Income"),
        ("spending", "Spending"),
        ("general", "General"),
        ("calculated", "Calculated"),
    ]

    CONTENT_TYPES = [
        ("monetary", "Monetary"),
        ("integer", "Integer"),
        ("text", "Text"),
        ("url", "URL"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=FIELD_CATEGORIES, default="general")
    explanation = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default="text")
    formula = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=False)

    @property
    def is_protected(self) -> bool:
        """Return True if this field's slug is immutable."""
        return self.slug in PROTECTED_SLUGS

    def save(self, *args, **kwargs):
        """Prevent renaming protected slugs."""
        if self.pk:
            original = DataField.objects.get(pk=self.pk)
            if original.slug in PROTECTED_SLUGS and original.slug != self.slug:
                raise ValidationError("This field's slug is protected and cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Disallow deletion of protected fields."""
        if self.slug in PROTECTED_SLUGS:
            raise ValidationError("This field is protected and cannot be deleted.")
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
