"""
Site-wide Factoids Optimization Models

Provides efficient data aggregation and change detection for scalable
cross-council analysis and intelligent factoid generation scheduling.
"""

import hashlib
import json
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from .council import Council, FinancialYear
from .field import DataField


class SitewideDataSummary(models.Model):
    """
    Pre-aggregated summary data for efficient cross-council analysis.
    
    Stores daily snapshots of key statistics to avoid recalculating
    large datasets on every factoid generation.
    """
    date_calculated = models.DateField(default=timezone.now)
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    
    # Aggregated statistics
    total_councils = models.IntegerField(default=0)
    average_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    median_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    std_deviation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Top/bottom performers (JSON for efficiency)
    top_5_councils = models.JSONField(default=list)  # [{"name": "X", "slug": "x", "value": 123.45}, ...]
    bottom_5_councils = models.JSONField(default=list)
    
    # Council type breakdowns
    type_averages = models.JSONField(default=dict)  # {"Unitary": avg, "County": avg, ...}
    nation_averages = models.JSONField(default=dict)  # {"England": avg, "Scotland": avg, ...}
    
    # Quality indicators
    data_completeness = models.FloatField(default=0.0)  # % of councils with data
    outlier_count = models.IntegerField(default=0)  # Number of statistical outliers
    
    # Change detection
    data_hash = models.CharField(max_length=64)  # SHA256 of source data for change detection
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sitewide_data_summary'
        unique_together = ['date_calculated', 'year', 'field']
        ordering = ['-date_calculated', 'field__name']
        indexes = [
            models.Index(fields=['date_calculated', 'year']),
            models.Index(fields=['field', 'data_hash']),
            models.Index(fields=['data_completeness']),
        ]
    
    def __str__(self):
        return f"{self.field.name} - {self.year.label} ({self.date_calculated})"
    
    @classmethod
    def calculate_hash(cls, field_data):
        """Calculate hash for change detection."""
        # Sort data to ensure consistent hashing
        sorted_data = sorted(field_data, key=lambda x: x.get('council_slug', ''))
        data_string = json.dumps(sorted_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def get_insights_summary(self):
        """Get a compact summary suitable for AI prompt generation."""
        return {
            'field_name': self.field.name,
            'year': self.year.label,
            'total_councils': self.total_councils,
            'average': float(self.average_value) if self.average_value else None,
            'range': {
                'min': float(self.min_value) if self.min_value else None,
                'max': float(self.max_value) if self.max_value else None,
            },
            'top_performers': self.top_5_councils[:3],  # Only top 3 for prompt efficiency
            'bottom_performers': self.bottom_5_councils[:3],
            'type_comparison': self.type_averages,
            'nation_comparison': self.nation_averages,
            'data_quality': self.data_completeness
        }


class SitewideDataChangeLog(models.Model):
    """
    Tracks changes to underlying data to trigger intelligent factoid refresh.
    
    Only logs changes that affect comparison fields to avoid unnecessary updates.
    """
    CHANGE_TYPES = [
        ('data_update', 'Financial Data Updated'),
        ('new_council', 'New Council Added'),
        ('new_field', 'New Field Added'),
        ('council_removed', 'Council Removed'),
        ('field_removed', 'Field Removed'),
        ('bulk_import', 'Bulk Data Import'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    
    # Affected entities (nullable for system-wide changes)
    affected_year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE, null=True, blank=True)
    affected_field = models.ForeignKey(DataField, on_delete=models.CASCADE, null=True, blank=True)
    affected_council = models.ForeignKey(Council, on_delete=models.CASCADE, null=True, blank=True)
    
    # Change metadata
    old_hash = models.CharField(max_length=64, blank=True)
    new_hash = models.CharField(max_length=64)
    change_magnitude = models.FloatField(default=0.0)  # Percentage change if applicable
    
    # Processing status
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'sitewide_data_change_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'processed']),
            models.Index(fields=['change_type', 'processed']),
            models.Index(fields=['affected_field', 'processed']),
        ]
    
    def __str__(self):
        entity = ""
        if self.affected_council:
            entity = f" ({self.affected_council.name})"
        elif self.affected_field:
            entity = f" ({self.affected_field.name})"
        return f"{self.get_change_type_display()}{entity} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_processed(self):
        """Mark this change as processed by the factoid update system."""
        self.processed = True
        self.processed_at = timezone.now()
        self.save()


class SitewideFactoidSchedule(models.Model):
    """
    Manages intelligent scheduling of site-wide factoid updates.
    
    Ensures factoids are only regenerated when data changes and
    follows the 4x daily schedule: early morning, mid-morning, mid-afternoon, evening.
    """
    # Schedule configuration
    update_times = models.JSONField(
        default=list,
        help_text="Update times in 24-hour format, e.g., ['06:00', '10:30', '14:00', '18:30']"
    )
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    last_data_check = models.DateTimeField(null=True, blank=True)
    last_generation = models.DateTimeField(null=True, blank=True)
    next_scheduled_check = models.DateTimeField(null=True, blank=True)
    
    # Change detection
    last_data_hash = models.CharField(max_length=64, blank=True)
    pending_changes = models.BooleanField(default=False)
    change_count_since_last_generation = models.IntegerField(default=0)
    
    # Performance tracking
    generation_count_today = models.IntegerField(default=0)
    avg_generation_time = models.FloatField(default=0.0)
    last_generation_time = models.FloatField(null=True, blank=True)
    total_generations = models.IntegerField(default=0)
    
    # Quality metrics
    success_rate_7_days = models.FloatField(default=100.0)
    last_error = models.TextField(blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sitewide_factoid_schedule'
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Sitewide Factoid Schedule ({status}) - {len(self.update_times)} daily updates"
    
    @classmethod
    def get_default_schedule(cls):
        """Get the default update schedule."""
        schedule, created = cls.objects.get_or_create(
            defaults={
                'update_times': ['06:00', '10:30', '14:00', '18:30'],
                'is_active': True
            }
        )
        return schedule
    
    def should_check_for_updates(self):
        """Determine if we should check for data changes now."""
        if not self.is_active:
            return False
        
        now = timezone.now()
        
        # If we've never checked, we should check
        if not self.last_data_check:
            return True
        
        # Check if enough time has passed since last check (minimum 1 hour)
        time_since_check = now - self.last_data_check
        if time_since_check.total_seconds() < 3600:  # 1 hour
            return False
        
        # Check if we're in a scheduled update window
        current_time = now.strftime('%H:%M')
        
        # Allow 30-minute window around each scheduled time
        for update_time in self.update_times:
            scheduled_hour, scheduled_minute = map(int, update_time.split(':'))
            scheduled_time = now.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0)
            
            time_diff = abs((now - scheduled_time).total_seconds())
            if time_diff <= 1800:  # Within 30 minutes
                return True
        
        return False
    
    def should_generate_factoids(self):
        """Determine if we should generate new factoids."""
        if not self.pending_changes:
            return False
        
        # Don't generate too frequently (minimum 2 hours between generations)
        if self.last_generation:
            time_since_generation = timezone.now() - self.last_generation
            if time_since_generation.total_seconds() < 7200:  # 2 hours
                return False
        
        return True
    
    def record_generation(self, success=True, generation_time=None, error_message=None):
        """Record the results of a factoid generation attempt."""
        now = timezone.now()
        
        self.last_generation = now
        self.generation_count_today += 1
        self.total_generations += 1
        
        if generation_time:
            self.last_generation_time = generation_time
            # Update rolling average
            if self.avg_generation_time == 0:
                self.avg_generation_time = generation_time
            else:
                self.avg_generation_time = (self.avg_generation_time * 0.8) + (generation_time * 0.2)
        
        if success:
            self.pending_changes = False
            self.change_count_since_last_generation = 0
            self.last_error = ""
            self.last_error_at = None
        else:
            self.last_error = error_message or "Unknown error"
            self.last_error_at = now
        
        # Reset daily count if it's a new day
        if self.updated_at and self.updated_at.date() != now.date():
            self.generation_count_today = 1
        
        self.save()
    
    def detect_data_changes(self):
        """Check for data changes since last check."""
        # Get unprocessed changes
        unprocessed_changes = SitewideDataChangeLog.objects.filter(
            processed=False,
            timestamp__gt=self.last_data_check if self.last_data_check else timezone.now() - timezone.timedelta(days=1)
        )
        
        change_count = unprocessed_changes.count()
        
        if change_count > 0:
            self.pending_changes = True
            self.change_count_since_last_generation += change_count
            
            # Calculate new data hash
            latest_summaries = SitewideDataSummary.objects.filter(
                date_calculated=timezone.now().date()
            ).values_list('data_hash', flat=True)
            
            combined_hash = hashlib.sha256(
                ''.join(sorted(latest_summaries)).encode()
            ).hexdigest()
            
            self.last_data_hash = combined_hash
        
        self.last_data_check = timezone.now()
        self.save()
        
        return change_count


class OptimizedFactoidCache(models.Model):
    """
    Multi-level caching for optimized factoid storage and retrieval.
    
    Stores factoids with metadata for intelligent cache management.
    """
    CACHE_LEVELS = [
        ('summaries', 'Pre-aggregated Summaries'),
        ('factoids', 'Generated Factoids'),
        ('fallback', 'Emergency Fallback'),
    ]
    
    cache_level = models.CharField(max_length=20, choices=CACHE_LEVELS)
    cache_key = models.CharField(max_length=255, unique=True)
    
    # Cache content
    content = models.JSONField()
    content_hash = models.CharField(max_length=64)
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    # Performance metrics
    generation_time = models.FloatField(null=True, blank=True)
    content_size = models.IntegerField(default=0)  # Size in bytes
    
    class Meta:
        db_table = 'optimized_factoid_cache'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['cache_level', 'expires_at']),
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_cache_level_display()} - {self.cache_key}"
    
    def is_expired(self):
        """Check if this cache entry has expired."""
        return timezone.now() > self.expires_at
    
    def access(self):
        """Record an access to this cache entry."""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired cache entries."""
        expired_count = cls.objects.filter(expires_at__lt=timezone.now()).count()
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return expired_count