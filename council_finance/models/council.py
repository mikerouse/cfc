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
    start_date = models.DateField(null=True, blank=True, help_text="When this financial year starts (optional)")
    end_date = models.DateField(null=True, blank=True, help_text="When this financial year ends (optional)")
    # New fields for enhanced year management
    is_provisional = models.BooleanField(
        default=True, 
        help_text="True if this year's figures are still being collected/finalized"
    )
    is_forecast = models.BooleanField(
        default=False,
        help_text="True if this is a future year with projected/estimated figures"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this financial year (data quality, issues, etc.)"
    )
    
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
    
    @property
    def status(self):
        """Return the status of this financial year: 'current', 'future', or 'past'."""
        if self.is_current:
            return 'current'
        
        current_year = self.get_current()
        if current_year:
            # Enhanced comparison that handles multiple year formats
            try:
                current_start = self._extract_start_year(current_year.label)
                this_start = self._extract_start_year(self.label)
                
                if this_start > current_start:
                    return 'future'
                elif this_start < current_start:
                    return 'past'
                else:
                    return 'current'
            except (ValueError, TypeError):
                # Fall back to string comparison if parsing fails
                if self.label > current_year.label:
                    return 'future'
                elif self.label < current_year.label:
                    return 'past'
                else:
                    return 'current'
        
        return 'unknown'
    
    def _extract_start_year(self, label):
        """Extract the starting year from various label formats."""
        import re
        
        # Handle formats like "2023/24", "2023-24", "2023_24"
        match = re.match(r'^(\d{4})[/-_](\d{2,4})$', label)
        if match:
            return int(match.group(1))
        
        # Handle single year like "2023"
        match = re.match(r'^(\d{4})$', label)
        if match:
            return int(match.group(1))
        
        # Handle full year ranges like "2023/2024"
        match = re.match(r'^(\d{4})[/-_](\d{4})$', label)
        if match:
            return int(match.group(1))
        
        # If we can't parse it, raise an error
        raise ValueError(f"Cannot parse year format: {label}")
    
    @property
    def is_future(self):
        """Return True if this is a future financial year."""
        return self.status == 'future'
    
    @property
    def is_past(self):
        """Return True if this is a past financial year."""
        return self.status == 'past'
    
    @property
    def data_reliability_level(self):
        """Return reliability level: 'high', 'medium', 'low'."""
        if self.is_forecast:
            return 'low'  # Future projections
        elif self.is_current and self.is_provisional:
            return 'medium'  # Current year, still collecting data
        elif self.is_past and not self.is_provisional:
            return 'high'  # Past year, finalized
        else:
            return 'medium'  # Default
    
    @property
    def reliability_note(self):
        """Return a detailed note about data reliability for this year."""
        if self.is_forecast:
            return f"Future year ({self.label}) - figures are projections and estimates only"
        elif self.is_current:
            if self.is_provisional:
                return f"Current year ({self.label}) - figures may be incomplete or provisional"
            else:
                return f"Current year ({self.label}) - figures are being finalized"
        elif self.is_past:
            if self.is_provisional:
                return f"Past year ({self.label}) - figures may still be provisional"
            else:
                return f"Past year ({self.label}) - figures should be final and audited"
        else:
            return f"Status unclear ({self.label}) - use caution when interpreting figures"
    
    @property
    def display_status_badge(self):
        """Return a CSS class for status badge display."""
        status = self.status
        if status == 'current':
            return 'bg-green-100 text-green-800'
        elif status == 'future':
            return 'bg-blue-100 text-blue-800'
        elif status == 'past':
            return 'bg-gray-100 text-gray-800'
        else:
            return 'bg-yellow-100 text-yellow-800'
    
    def get_figure_count(self):
        """Return the number of figure submissions for this year."""
        return FigureSubmission.objects.filter(year=self).count()
    
    def can_be_deleted(self):
        """Check if this year can be safely deleted (no associated data)."""
        return self.get_figure_count() == 0

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
