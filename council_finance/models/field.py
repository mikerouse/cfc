from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType


# Built in slugs that represent core facts about a council. These are
# effectively characteristics rather than yearly figures.  The values
# may change but the slugs themselves are fixed so other parts of the
# application can reliably reference them.
CHARACTERISTIC_SLUGS = {
    "council_type",
    "council_nation",
    "council_name",
    "population",
    "households",
    # Each council should always have a website address recorded so the
    # site can link directly to their homepage.
    "council_website",
    # Post code for the council headquarters. Previously the slug was
    # ``council_location`` but has been renamed for clarity.
    "council_hq_post_code",
    # The number of elected councillors is a structural fact about a council
    # rather than a yearly statistic so this slug must remain consistent.
    "elected_members",
}

# Backwards compatibility constant - older modules import PROTECTED_SLUGS
# when determining immutable fields.  It now simply aliases the new name.
PROTECTED_SLUGS = CHARACTERISTIC_SLUGS

class DataField(models.Model):
    """Definition of a figure/field that can be populated for each council."""

    FIELD_CATEGORIES = [
        ("balance_sheet", "Balance Sheet"),
        ("cash_flow", "Cash Flow"),
        ("income", "Income"),
        ("spending", "Spending"),
        ("general", "General"),
        # New category used for council characteristics such as website or
        # address. These values apply across all years and are typically
        # sourced directly from the authority rather than a financial return.
        ("characteristic", "Characteristics"),
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
    def variable_name(self) -> str:
        """Return the slug formatted for template variables."""
        return self.slug.replace('-', '_')

    @classmethod
    def from_variable_name(cls, name: str):
        """Look up a field using the template variable name.

        The helper reverses :meth:`variable_name` by converting
        underscores back to hyphens so we can perform a lookup
        by ``slug``.
        
        Args:
            name (str): The template variable name. This can include a prefix
                (e.g., 'financial.total_debt'), in which case only the last
                part after the final '.' is used. Underscores in the name are
                replaced with hyphens to derive the slug.
        
        Returns:
            DataField: The DataField instance corresponding to the derived slug.
        
        Raises:
            DataField.DoesNotExist: If no DataField with the derived slug exists.
                The error message includes the original variable name for easier debugging.
            DataField.MultipleObjectsReturned: If multiple DataFields with the
                derived slug exist.
        """
        base = name.split('.')[-1]
        slug = base.replace('_', '-')
        try:
            return cls.objects.get(slug=slug)
        except cls.DoesNotExist:
            raise cls.DoesNotExist(
                f"DataField with variable name '{name}' (slug='{slug}') does not exist"
            )

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
                
            # If slug is being changed, clean up old references
            if original.slug != self.slug:
                self._cleanup_old_field_references(original.slug)
                
        # When saving a known characteristic ensure it lives in the
        # ``characteristic`` category so management screens group these
        # values separately from yearly financial fields.
        if self.slug in CHARACTERISTIC_SLUGS:
            self.category = "characteristic"
        super().save(*args, **kwargs)
        
    def _cleanup_old_field_references(self, old_slug):
        """Clean up references to the old field slug when field is renamed."""
        from django.db import transaction
        
        with transaction.atomic():
            # Remove DataIssues for the old field to prevent confusion
            from .data_issue import DataIssue
            old_issues = DataIssue.objects.filter(field__slug=old_slug)
            if old_issues.exists():
                # Log this for audit purposes
                count = old_issues.count()
                old_issues.delete()
                
                # You could add logging here if needed
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Removed {count} DataIssue records for renamed field: {old_slug} -> {self.slug}")

    def delete(self, *args, **kwargs):
        """Disallow deletion of protected fields."""
        if self.slug in PROTECTED_SLUGS:
            raise ValidationError("This field is protected and cannot be deleted.")
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    def display_value(self, value: str) -> str:
        """Return a human readable representation for a stored value.

        List type fields store the primary key of the related model. This helper
        fetches the object name so tables show something meaningful instead of an
        ID. Numeric types are formatted with thousand separators and currency
        symbols so the comparison table looks neat and is easy to read.
        """

        # For list type fields resolve the foreign key to a friendly name.
        if self.content_type == "list" and self.dataset_type:
            model = self.dataset_type.model_class()
            try:
                obj = model.objects.get(pk=value)
                return str(obj)
            except (ValueError, model.DoesNotExist):
                return value

        # Monetary and integer fields are formatted consistently across the
        # site. Any parsing errors fall back to the raw value so unexpected
        # input doesn't crash templates.
        if self.content_type in {"monetary", "integer"}:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return value
            if self.content_type == "monetary":
                return f"£{num:,.0f}"
            return f"{int(num):,}"

        # For all other field types return the value unchanged.
        return value

    def display_council_types(self) -> str:
        """Return a comma separated list of linked council type names."""
        names = [ct.name for ct in self.council_types.all()]
        return ", ".join(names) if names else "All"
