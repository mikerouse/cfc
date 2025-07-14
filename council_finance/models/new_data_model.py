"""
New data model architecture to replace the FigureSubmission legacy system.

This separates council characteristics from financial figures and provides
proper versioning/change tracking for both.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class CouncilCharacteristic(models.Model):
    """
    Stores current characteristic values for councils (website, postcode, etc.)
    This replaces storing characteristics in FigureSubmission.
    """
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='characteristics')
    field = models.ForeignKey('DataField', on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    
    # Metadata
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['council', 'field']
        indexes = [
            models.Index(fields=['council', 'field']),
            models.Index(fields=['field']),
        ]
    
    def __str__(self):
        return f"{self.council.name} - {self.field.name}: {self.value}"


class CouncilCharacteristicHistory(models.Model):
    """
    Tracks changes to council characteristics over time.
    Every time a characteristic changes, we log the old and new values.
    """
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='characteristic_history')
    field = models.ForeignKey('DataField', on_delete=models.CASCADE)
    
    # The change
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    
    # Who and when
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    # Source of change
    source = models.CharField(max_length=50, choices=[
        ('import', 'Data Import'),
        ('contribution', 'User Contribution'),
        ('admin', 'Admin Edit'),
        ('api', 'API Update'),
    ], default='contribution')
    
    class Meta:
        indexes = [
            models.Index(fields=['council', 'field', 'changed_at']),
            models.Index(fields=['changed_at']),
        ]
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.council.name} - {self.field.name} changed at {self.changed_at}"


class FinancialFigure(models.Model):
    """
    Stores financial figures for councils by year.
    This replaces FigureSubmission for financial data only.
    """
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='financial_figures')
    field = models.ForeignKey('DataField', on_delete=models.CASCADE)
    year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE)
    
    # The actual figure
    value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Data quality flags
    is_estimated = models.BooleanField(default=False)
    is_provisional = models.BooleanField(default=False)
    confidence_level = models.CharField(max_length=20, choices=[
        ('high', 'High Confidence'),
        ('medium', 'Medium Confidence'),
        ('low', 'Low Confidence'),
        ('unknown', 'Unknown'),
    ], default='unknown')
    
    # Sources and notes
    source_document = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True)
    
    # Metadata
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['council', 'field', 'year']
        indexes = [
            models.Index(fields=['council', 'field', 'year']),
            models.Index(fields=['year', 'field']),
            models.Index(fields=['council', 'year']),
        ]
    
    def __str__(self):
        return f"{self.council.name} - {self.field.name} ({self.year.label}): £{self.value}"


class FinancialFigureHistory(models.Model):
    """
    Tracks changes to financial figures over time.
    """
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='financial_history')
    field = models.ForeignKey('DataField', on_delete=models.CASCADE)
    year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE)
    
    # The change
    old_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    new_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Who and when
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    # Source of change
    source = models.CharField(max_length=50, choices=[
        ('import', 'Data Import'),
        ('contribution', 'User Contribution'),
        ('admin', 'Admin Edit'),
        ('correction', 'Data Correction'),
        ('audit', 'Audit Adjustment'),
    ], default='contribution')
    
    class Meta:
        indexes = [
            models.Index(fields=['council', 'field', 'year', 'changed_at']),
            models.Index(fields=['changed_at']),
        ]
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.council.name} - {self.field.name} ({self.year.label}) changed at {self.changed_at}"


class ContributionV2(models.Model):
    """
    New contribution model that properly handles both characteristics and financial figures.
    Replaces the old Contribution model.
    """
    # Basic info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contributions_v2')
    council = models.ForeignKey('Council', on_delete=models.CASCADE)
    field = models.ForeignKey('DataField', on_delete=models.CASCADE)
    
    # For financial figures only
    year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE, null=True, blank=True)
    
    # The contribution
    value = models.TextField()  # Store as text initially, convert on approval
    
    # Current and proposed values for comparison
    current_value = models.TextField(blank=True, null=True)  # What's currently stored
    
    # Metadata
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('applied', 'Applied to Data'),
    ], default='pending')
    
    # Sources and validation
    source_url = models.URLField(blank=True, null=True)
    source_description = models.TextField(blank=True)
    
    # Review process
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_contributions_v2')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created']),
            models.Index(fields=['council', 'field']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['field', 'status']),
        ]
        ordering = ['-created']
    
    @property
    def is_characteristic(self):
        """Check if this contribution is for a characteristic field."""
        return self.field.category == 'characteristic'
    
    @property
    def is_financial(self):
        """Check if this contribution is for a financial field."""
        return self.field.category != 'characteristic'
    
    def __str__(self):
        year_part = f" ({self.year.label})" if self.year else ""
        return f"{self.user.username} -> {self.council.name} - {self.field.name}{year_part}: {self.value}"


# Utility functions for migration and data management

def migrate_characteristics_from_figuresubmission():
    """
    Migrate characteristic data from FigureSubmission to CouncilCharacteristic.
    Call this during the migration process.
    """
    from .council import FigureSubmission, DataField
    
    # Get all characteristic fields
    characteristic_fields = DataField.objects.filter(category='characteristic')
    
    for field in characteristic_fields:
        # Get all FigureSubmissions for this characteristic field
        submissions = FigureSubmission.objects.filter(field=field, year__isnull=True)
        
        for submission in submissions:
            # Create or update the characteristic
            characteristic, created = CouncilCharacteristic.objects.update_or_create(
                council=submission.council,
                field=submission.field,
                defaults={
                    'value': submission.value,
                    'updated_by': None,  # We don't know who originally entered this
                }
            )
            
            if created:
                # Create a history entry for the initial value
                CouncilCharacteristicHistory.objects.create(
                    council=submission.council,
                    field=submission.field,
                    old_value=None,
                    new_value=submission.value,
                    changed_by=None,
                    source='import'
                )


def migrate_financial_data_from_figuresubmission():
    """
    Migrate financial data from FigureSubmission to FinancialFigure.
    Call this during the migration process.
    """
    from .council import FigureSubmission, DataField
    from decimal import Decimal, InvalidOperation
    
    # Get all non-characteristic fields
    financial_fields = DataField.objects.exclude(category='characteristic')
    
    for field in financial_fields:
        # Get all FigureSubmissions for this financial field
        submissions = FigureSubmission.objects.filter(field=field, year__isnull=False)
        
        for submission in submissions:
            # Try to convert value to decimal
            try:
                decimal_value = Decimal(str(submission.value)) if submission.value else None
            except (InvalidOperation, TypeError):
                decimal_value = None
            
            # Create the financial figure
            figure, created = FinancialFigure.objects.update_or_create(
                council=submission.council,
                field=submission.field,
                year=submission.year,
                defaults={
                    'value': decimal_value,
                    'updated_by': None,  # We don't know who originally entered this
                }
            )
            
            if created and decimal_value is not None:
                # Create a history entry for the initial value
                FinancialFigureHistory.objects.create(
                    council=submission.council,
                    field=submission.field,
                    year=submission.year,
                    old_value=None,
                    new_value=decimal_value,
                    changed_by=None,
                    source='import'
                )
