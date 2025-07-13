from django.db import models

# The CouncilType model lives in a separate module so it can be edited
# independently in the admin. We import lazily to avoid circular imports
# when Django loads models during migrations.
from .council_type import CouncilType
from .council_nation import CouncilNation
from .field import DataField

class Council(models.Model):
    """Basic local authority info."""
    
    # Status choices for council flagging
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed/Disbanded'),
        ('merged', 'Merged'),
        ('renamed', 'Renamed'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Current status of the council"
    )
    
    # Store the most recent population figure so views don't repeatedly
    # search figure submissions. Null is used when no figure exists.
    latest_population = models.IntegerField(
        null=True,
        blank=True,
        help_text="Latest population figure across all years",
    )
    # Link to a CouncilType so the admin form can offer a drop-down list and
    # staff can manage available types.
    council_type = models.ForeignKey(
        CouncilType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # Associate each council with a UK nation. Null/blank allow existing data
    # to omit the field until populated via the admin interface.
    council_nation = models.ForeignKey(
        CouncilNation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    def update_latest_population(self):
        """Set ``latest_population`` based on the newest submitted figure."""
        pop_field = DataField.objects.filter(slug="population").first()
        if not pop_field:
            self.latest_population = None
        else:
            latest = (
                self.figuresubmission_set.filter(field=pop_field)
                .select_related("year")
                .order_by("-year__label")
                .first()
            )
            if latest:
                try:
                    self.latest_population = int(float(latest.value))
                except (TypeError, ValueError):
                    self.latest_population = None
            else:
                self.latest_population = None
        self.save(update_fields=["latest_population"])

class FinancialYear(models.Model):
    """Represents a financial year label (e.g. 2023/24)."""
    label = models.CharField(max_length=20, unique=True)
    is_current = models.BooleanField(default=False, help_text="Mark as current financial year")
    
    class Meta:
        ordering = ['-label']

    def __str__(self):
        return self.label
    
    def save(self, *args, **kwargs):
        # Ensure only one financial year is marked as current
        if self.is_current:
            FinancialYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_current(cls):
        """Get the current financial year."""
        return cls.objects.filter(is_current=True).first() or cls.objects.first()

class FigureSubmission(models.Model):
    """Stores a single value for a given field, council and year."""

    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    # Reference the DataField definition so we know what this value represents.
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    # Track when the figure value is missing so staff can easily find gaps
    # in the data and populate them later. A blank or null ``value`` will
    # automatically set this flag via imports and migrations.
    needs_populating = models.BooleanField(
        default=False,
        help_text="True if the source dataset did not provide this value",
    )

    @property
    def display_value(self) -> str:
        """Return a human readable version of ``value`` for templates.

        This simply delegates to ``DataField.display_value`` so the logic for
        list values and other formatting lives in one place. Having a property
        means templates can show the formatted value without calling a method
        with arguments, which Django does not allow.
        """
        return self.field.display_value(self.value)

    class Meta:
        unique_together = ("council", "year", "field")

class DebtAdjustment(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

class WhistleblowerReport(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

class ModerationLog(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
