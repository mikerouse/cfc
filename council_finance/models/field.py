from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType


# Slugs listed here are considered immutable. Staff can update the value
# associated with these fields but should never rename or remove them
# because other parts of the system rely on these identifiers.
PROTECTED_SLUGS = {
    "council_type",
    "council_name",
    "population",
    "households",
    # Each council should always have a website address recorded, so this
    # field is protected to prevent accidental removal.
    "council_website",
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
        # New list type references another dataset for selectable options
        ("list", "List"),
    ]

    # Use BigAutoField to stay compatible with existing migrations which
    # created this model with a BigAutoField primary key.
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=FIELD_CATEGORIES, default="general")
    explanation = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default="text")
    # When ``content_type`` is ``list`` this holds the model that provides
    # selectable options. We store a ContentType so new datasets can be
    # referenced without additional migrations.
    dataset_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Model providing options for list values",
    )
    # Allow a field to be restricted to specific council types. When no types
    # are selected the field applies to all councils. Using a ManyToManyField
    # keeps the relationship flexible without additional tables for each link.
    council_types = models.ManyToManyField(
        "council_finance.CouncilType",
        blank=True,
        help_text="Council types this field applies to",
    )
    formula = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=False)

    @property
    def is_protected(self) -> bool:
        """Return True if this field's slug is immutable."""
        return self.slug in PROTECTED_SLUGS

    def save(self, *args, **kwargs):
        """Prevent renaming protected slugs and auto-generate when blank."""
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)
            slug = base
            i = 1
            while DataField.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
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

    def display_value(self, value: str) -> str:
        """Return a human readable representation for a stored value.

        List type fields store the primary key of the related model.
        This helper fetches the object name so tables show something
        meaningful instead of an ID. Other field types simply return
        the value unchanged.
        """
        if self.content_type == "list" and self.dataset_type:
            model = self.dataset_type.model_class()
            try:
                obj = model.objects.get(pk=value)
                return str(obj)
            except (ValueError, model.DoesNotExist):
                return value
        return value

    def display_council_types(self) -> str:
        """Return a comma separated list of linked council type names."""
        names = [ct.name for ct in self.council_types.all()]
        return ", ".join(names) if names else "All"
