"""
Models for storing approved council data - the single source of truth.
This separates live/approved data from contributions/submissions.
"""

from django.db import models
from django.core.exceptions import ValidationError
from .council import Council, FinancialYear
from .field import DataField, CHARACTERISTIC_SLUGS


class CouncilData(models.Model):
    """
    Authoritative storage for approved council data.
    
    This is the single source of truth for council information.
    When contributions are approved, they update this model.
    Views should read from this model, not FigureSubmission.
    """
    
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(
        FinancialYear, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Leave blank for characteristics that don't vary by year"
    )
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    
    # Track data quality and updates
    last_updated = models.DateTimeField(auto_now=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    confidence_level = models.CharField(
        max_length=20,
        choices=[
            ('high', 'High - Official source'),
            ('medium', 'Medium - Reliable source'),
            ('low', 'Low - Unverified'),
        ],
        default='medium'
    )
    
    # Track the source of this data
    source_type = models.CharField(
        max_length=20,
        choices=[
            ('official', 'Official council data'),
            ('government', 'Government dataset'),
            ('community', 'Community contribution'),
            ('calculated', 'Calculated value'),
        ],
        default='community'
    )
    source_notes = models.TextField(
        blank=True,
        help_text="Notes about the source of this data"
    )
    
    class Meta:
        unique_together = ("council", "year", "field")
        indexes = [
            models.Index(fields=['council', 'field']),
            models.Index(fields=['council', 'year']),
            models.Index(fields=['field', 'year']),
        ]
    
    def clean(self):
        """Validate that characteristics don't have a year."""
        if self.field and self.field.slug in CHARACTERISTIC_SLUGS:
            if self.year is not None:
                raise ValidationError(
                    f"Characteristic field '{self.field.slug}' should not have a year"
                )
        elif self.field and self.field.category != 'characteristic':
            if self.year is None:
                raise ValidationError(
                    f"Non-characteristic field '{self.field.slug}' requires a year"
                )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Update the Council model's direct fields for key characteristics
        if self.field and self.field.slug in CHARACTERISTIC_SLUGS:
            self._update_council_characteristics()
    
    def _update_council_characteristics(self):
        """Update the Council model's direct fields when characteristics change."""
        field_slug = self.field.slug
        
        # Update the Council model's direct fields for consistency
        if field_slug == 'council_website':
            self.council.website = self.value
            self.council.save(update_fields=['website'])
        elif field_slug == 'population':
            try:
                self.council.latest_population = int(float(self.value))
                self.council.save(update_fields=['latest_population'])
            except (ValueError, TypeError):
                pass
        # Add other characteristic mappings as needed
    
    @property
    def display_value(self) -> str:
        """Return a human readable version of the value."""
        return self.field.display_value(self.value)
    
    def __str__(self):
        year_str = f" ({self.year.label})" if self.year else ""
        return f"{self.council.name} - {self.field.name}{year_str}: {self.value}"


class DataApprovalLog(models.Model):
    """
    Track when contributions are approved and applied to CouncilData.
    """
    
    council_data = models.ForeignKey(CouncilData, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    
    # Link to the original submission (if any)
    source_submission = models.ForeignKey(
        'council_finance.FigureSubmission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    previous_value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Previous value before this update"
    )
    
    approval_notes = models.TextField(
        blank=True,
        help_text="Notes about why this data was approved"
    )
    
    class Meta:
        ordering = ['-approved_at']
    
    def __str__(self):
        return f"Approval: {self.council_data} at {self.approved_at}"
