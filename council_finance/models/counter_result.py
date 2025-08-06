"""
Counter Result Model - Persistent storage for counter calculation results.

This model provides database-backed caching for counter values that survives 
server restarts and enables smart cache invalidation when underlying data changes.

Key features:
- Persistent storage across server restarts
- Smart invalidation when source data changes  
- Rate limiting to prevent excessive recalculation
- Comprehensive Event Viewer integration for monitoring
"""

import hashlib
import json
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.cache import cache

# Event Viewer integration
try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False


def log_counter_result_event(level, category, title, message, details=None):
    """Log counter result events to Event Viewer system for debugging"""
    if not EVENT_VIEWER_AVAILABLE:
        return
    
    try:
        event_details = {
            'module': 'counter_result',
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            event_details.update(details)
        
        SystemEvent.objects.create(
            source='counter_result',
            level=level,
            category=category,
            title=title,
            message=message,
            details=event_details
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log counter result Event Viewer event: {e}")


class CounterResult(models.Model):
    """
    Persistent storage for counter calculation results.
    
    Enables fast counter loading by storing calculated values in database
    and only recalculating when underlying data actually changes.
    """
    
    # Counter identification
    counter = models.ForeignKey(
        'CounterDefinition', 
        on_delete=models.CASCADE,
        help_text="The counter definition this result belongs to"
    )
    council = models.ForeignKey(
        'Council', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        help_text="Council this result is for (None for site-wide totals)"
    )
    year = models.ForeignKey(
        'FinancialYear', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        help_text="Financial year this result is for (None for all-years)"
    )
    
    # Result data
    value = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        help_text="Calculated counter value"
    )
    calculated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this result was calculated"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this result was last updated"
    )
    
    # Cache invalidation tracking
    data_hash = models.CharField(
        max_length=64,
        help_text="Hash of source data for change detection"
    )
    is_stale = models.BooleanField(
        default=False,
        help_text="Whether this result needs recalculation"
    )
    stale_marked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this result was marked as stale"
    )
    
    # Performance tracking
    calculation_time_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="How long this calculation took"
    )
    cache_hits = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this result was served from cache"
    )
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this result was last accessed"
    )
    
    # Rate limiting for stale marking
    stale_mark_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times marked stale (for rate limiting)"
    )
    rate_limit_reset_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When rate limiting counter resets"
    )
    
    class Meta:
        unique_together = [('counter', 'council', 'year')]
        indexes = [
            # Primary lookup index
            models.Index(fields=['counter', 'council', 'year'], name='idx_counter_lookup'),
            # Performance monitoring indexes  
            models.Index(fields=['calculated_at'], name='idx_counter_calculated_at'),
            models.Index(fields=['is_stale'], name='idx_counter_stale'),
            models.Index(fields=['last_accessed'], name='idx_counter_accessed'),
            # Rate limiting index
            models.Index(fields=['stale_mark_count', 'rate_limit_reset_at'], name='idx_counter_rate_limit'),
        ]
        
    def __str__(self):
        council_str = self.council.name if self.council else "Site-wide"
        year_str = self.year.label if self.year else "All Years"
        return f"{self.counter.name} - {council_str} ({year_str}): £{self.value:,.2f}"
    
    def save(self, *args, **kwargs):
        """Override save to add comprehensive logging"""
        is_new = self.pk is None
        old_value = None
        
        if not is_new:
            try:
                old_result = CounterResult.objects.get(pk=self.pk)
                old_value = old_result.value
            except CounterResult.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Log counter result events for monitoring
        if is_new:
            log_counter_result_event(
                'info', 'calculation',
                'Counter Result Created',
                f'New counter result calculated: {self.counter.name} = £{self.value:,.2f}',
                details={
                    'counter_slug': self.counter.slug,
                    'council_slug': self.council.slug if self.council else None,
                    'council_name': self.council.name if self.council else 'Site-wide',
                    'year_label': self.year.label if self.year else 'All Years',
                    'calculated_value': float(self.value),
                    'calculation_time_seconds': self.calculation_time_seconds,
                    'data_hash': self.data_hash,
                    'is_site_wide': self.council is None
                }
            )
        elif old_value != self.value:
            change_amount = self.value - old_value
            change_percent = (change_amount / old_value * 100) if old_value != 0 else 0
            
            log_counter_result_event(
                'info', 'calculation',
                'Counter Result Updated',
                f'Counter result changed: {self.counter.name} £{old_value:,.2f} → £{self.value:,.2f} ({change_percent:+.1f}%)',
                details={
                    'counter_slug': self.counter.slug,
                    'council_slug': self.council.slug if self.council else None,
                    'council_name': self.council.name if self.council else 'Site-wide',
                    'year_label': self.year.label if self.year else 'All Years',
                    'old_value': float(old_value),
                    'new_value': float(self.value),
                    'change_amount': float(change_amount),
                    'change_percent': float(change_percent),
                    'data_hash': self.data_hash,
                    'is_site_wide': self.council is None
                }
            )
    
    def mark_stale(self, reason=None, force=False):
        """
        Mark this result as stale with rate limiting and comprehensive logging.
        
        Args:
            reason: Why this result is being marked stale
            force: Skip rate limiting (for admin actions)
            
        Returns:
            bool: True if marked stale, False if rate limited
        """
        now = timezone.now()
        
        # Rate limiting: max 5 stale marks per hour per result
        if not force:
            # Reset counter if it's been more than 1 hour
            if (not self.rate_limit_reset_at or 
                (now - self.rate_limit_reset_at).total_seconds() > 3600):
                self.stale_mark_count = 0
                self.rate_limit_reset_at = now
            
            # Check rate limit
            if self.stale_mark_count >= 5:
                log_counter_result_event(
                    'warning', 'performance',
                    'Counter Stale Marking Rate Limited',
                    f'Rate limit exceeded for {self.counter.name} stale marking (attempt #{self.stale_mark_count + 1})',
                    details={
                        'counter_slug': self.counter.slug,
                        'council_slug': self.council.slug if self.council else None,
                        'council_name': self.council.name if self.council else 'Site-wide',
                        'year_label': self.year.label if self.year else 'All Years',
                        'stale_mark_count': self.stale_mark_count,
                        'rate_limit_reason': reason,
                        'rate_limit_reset_at': self.rate_limit_reset_at.isoformat() if self.rate_limit_reset_at else None,
                        'is_site_wide': self.council is None
                    }
                )
                return False
        
        # Mark as stale
        was_fresh = not self.is_stale
        self.is_stale = True
        self.stale_marked_at = now
        self.stale_mark_count += 1
        
        # Clear Redis cache immediately
        cache_patterns = [
            f"counter_values:{self.council.slug}:{self.year.label}" if self.council and self.year else None,
            f"counter_total:{self.counter.slug}:{self.year.label if self.year else 'all'}",
        ]
        
        cleared_keys = []
        for pattern in cache_patterns:
            if pattern:
                if cache.get(pattern):
                    cache.delete(pattern)
                    cleared_keys.append(pattern)
        
        self.save()
        
        # Log stale marking event
        if was_fresh:
            log_counter_result_event(
                'info', 'cache_invalidation',
                'Counter Result Marked Stale',
                f'Counter result marked stale: {self.counter.name} (reason: {reason or "unknown"})',
                details={
                    'counter_slug': self.counter.slug,
                    'council_slug': self.council.slug if self.council else None,
                    'council_name': self.council.name if self.council else 'Site-wide',
                    'year_label': self.year.label if self.year else 'All Years',
                    'stale_reason': reason,
                    'stale_mark_count': self.stale_mark_count,
                    'cleared_cache_keys': cleared_keys,
                    'current_value': float(self.value),
                    'is_site_wide': self.council is None,
                    'forced': force
                }
            )
        
        return True
    
    def record_cache_hit(self):
        """Record that this result was served from cache"""
        self.cache_hits += 1
        self.last_accessed = timezone.now()
        # Use update() to avoid triggering save() logging
        CounterResult.objects.filter(pk=self.pk).update(
            cache_hits=self.cache_hits,
            last_accessed=self.last_accessed
        )
    
    @classmethod 
    def calculate_data_hash(cls, counter, council=None, year=None):
        """
        Calculate hash of source data to detect changes.
        
        Args:
            counter: CounterDefinition instance
            council: Council instance or None for site-wide
            year: FinancialYear instance or None for all years
            
        Returns:
            str: SHA256 hash of relevant source data
        """
        # Collect data that affects this counter calculation
        hash_data = {
            'counter_formula': counter.formula,
            'counter_slug': counter.slug,
        }
        
        if council:
            # Include council-specific data
            hash_data.update({
                'council_slug': council.slug,
                'council_type': council.council_type.slug if council.council_type else None,
            })
            
            # Get financial figures for this council/year
            from .new_data_model import FinancialFigure
            figures = FinancialFigure.objects.filter(council=council)
            if year:
                figures = figures.filter(year=year)
            
            figure_data = {}
            for fig in figures:
                figure_data[fig.field.slug] = str(fig.value)
            hash_data['financial_figures'] = figure_data
            
            # Get characteristics for this council
            from .new_data_model import CouncilCharacteristic  
            characteristics = CouncilCharacteristic.objects.filter(council=council)
            char_data = {}
            for char in characteristics:
                char_data[char.field.slug] = str(char.value)
            hash_data['characteristics'] = char_data
            
        else:
            # Site-wide: include count of councils and total figures
            from .council import Council
            from .new_data_model import FinancialFigure
            
            hash_data.update({
                'total_councils': Council.objects.count(),
                'total_figures': FinancialFigure.objects.count(),
            })
            
            if year:
                hash_data['year_figure_count'] = FinancialFigure.objects.filter(year=year).count()
        
        # Create hash
        data_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    @classmethod
    def get_stale_marking_stats(cls, hours_back=24):
        """Get statistics about stale marking for monitoring"""
        since = timezone.now() - timezone.timedelta(hours=hours_back)
        
        stats = {
            'total_stale_marks': cls.objects.filter(stale_marked_at__gte=since).count(),
            'rate_limited_results': cls.objects.filter(stale_mark_count__gte=5).count(),
            'most_marked_results': cls.objects.filter(
                stale_marked_at__gte=since
            ).order_by('-stale_mark_count')[:10],
            'councils_with_high_stale_rate': {},
        }
        
        # Find councils with unusually high stale marking
        from django.db.models import Count
        high_rate_councils = cls.objects.filter(
            stale_marked_at__gte=since,
            council__isnull=False
        ).values('council__name').annotate(
            stale_count=Count('id')
        ).filter(stale_count__gte=10).order_by('-stale_count')
        
        for council_data in high_rate_councils:
            stats['councils_with_high_stale_rate'][council_data['council__name']] = council_data['stale_count']
        
        return stats