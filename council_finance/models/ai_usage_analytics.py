"""
AI Usage Analytics Models

Tracks AI factoid generation usage, costs, performance metrics,
and provides data for optimization recommendations.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from .council import Council


class AIUsageLog(models.Model):
    """
    Logs each AI API call for analytics and cost tracking.
    """
    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name='ai_usage_logs')
    model_used = models.CharField(max_length=50, default='gpt-4o-mini')
    factoids_requested = models.IntegerField(default=3)
    factoids_generated = models.IntegerField(default=0)
    
    # Performance metrics
    processing_time_seconds = models.FloatField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Request details
    style = models.CharField(max_length=20, default='news_ticker')
    force_refresh = models.BooleanField(default=False)
    cache_hit = models.BooleanField(default=False)
    
    # Result status
    success = models.BooleanField(default=True)
    error_type = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    
    # Request context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_usage_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['council', 'created_at']),
            models.Index(fields=['model_used', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"{self.council.name} - {self.model_used} - {status} - {self.created_at}"
    
    def get_cost_per_1k_tokens(self):
        """Get the cost per 1k tokens for the model used."""
        model_costs = {
            'gpt-4o-mini': 0.000150,
            'gpt-4o': 0.0025,
            'gpt-4-turbo': 0.01,
            'gpt-4': 0.03,
            'gpt-3.5-turbo': 0.0015
        }
        return model_costs.get(self.model_used, 0.01)


class DailyCostSummary(models.Model):
    """
    Daily aggregation of AI costs and usage for reporting.
    """
    date = models.DateField(unique=True)
    
    # Usage metrics
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    cache_hits = models.IntegerField(default=0)
    
    # Performance metrics
    total_factoids_generated = models.IntegerField(default=0)
    avg_processing_time = models.FloatField(null=True, blank=True)
    total_tokens_used = models.IntegerField(default=0)
    
    # Cost metrics
    total_estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    cost_per_factoid = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Model usage breakdown (JSON field for flexibility)
    model_usage_breakdown = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_cost_summary'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Daily Summary {self.date} - {self.total_requests} requests - £{self.total_estimated_cost}"
    
    @classmethod
    def calculate_for_date(cls, date):
        """Calculate and store daily summary for a specific date."""
        from django.db.models import Sum, Avg, Count
        
        # Get all logs for the date
        logs = AIUsageLog.objects.filter(created_at__date=date)
        
        if not logs.exists():
            return None
        
        # Calculate aggregations
        aggregates = logs.aggregate(
            total_requests=Count('id'),
            successful_requests=Count('id', filter=models.Q(success=True)),
            failed_requests=Count('id', filter=models.Q(success=False)),
            cache_hits=Count('id', filter=models.Q(cache_hit=True)),
            total_factoids=Sum('factoids_generated'),
            avg_time=Avg('processing_time_seconds'),
            total_tokens=Sum('tokens_used'),
            total_cost=Sum('estimated_cost')
        )
        
        # Calculate model usage breakdown
        model_breakdown = {}
        for log in logs:
            model = log.model_used
            if model not in model_breakdown:
                model_breakdown[model] = {'requests': 0, 'cost': 0}
            model_breakdown[model]['requests'] += 1
            if log.estimated_cost:
                model_breakdown[model]['cost'] += float(log.estimated_cost)
        
        # Calculate cost per factoid
        cost_per_factoid = None
        if aggregates['total_factoids'] and aggregates['total_cost']:
            cost_per_factoid = aggregates['total_cost'] / aggregates['total_factoids']
        
        # Create or update summary
        summary, created = cls.objects.update_or_create(
            date=date,
            defaults={
                'total_requests': aggregates['total_requests'],
                'successful_requests': aggregates['successful_requests'],
                'failed_requests': aggregates['failed_requests'],
                'cache_hits': aggregates['cache_hits'],
                'total_factoids_generated': aggregates['total_factoids'] or 0,
                'avg_processing_time': aggregates['avg_time'],
                'total_tokens_used': aggregates['total_tokens'] or 0,
                'total_estimated_cost': aggregates['total_cost'] or 0,
                'cost_per_factoid': cost_per_factoid,
                'model_usage_breakdown': model_breakdown
            }
        )
        
        return summary


class CacheWarmupSchedule(models.Model):
    """
    Schedules for automated cache warming of popular councils.
    """
    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name='warmup_schedules')
    
    # Schedule configuration
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="1=High, 2=Medium, 3=Low")
    frequency_hours = models.IntegerField(default=24, help_text="How often to warm cache (hours)")
    
    # Usage-based scheduling
    avg_daily_requests = models.IntegerField(default=0)
    last_request = models.DateTimeField(null=True, blank=True)
    popularity_score = models.FloatField(default=0.0)
    
    # Execution tracking
    last_warmup = models.DateTimeField(null=True, blank=True)
    next_warmup = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cache_warmup_schedule'
        ordering = ['priority', '-popularity_score']
        indexes = [
            models.Index(fields=['is_active', 'next_warmup']),
            models.Index(fields=['priority', 'popularity_score']),
        ]
    
    def __str__(self):
        return f"Warmup {self.council.name} - Priority {self.priority} - Every {self.frequency_hours}h"
    
    def calculate_next_warmup(self):
        """Calculate when this council should next be warmed up."""
        from datetime import timedelta
        
        if self.last_warmup:
            self.next_warmup = self.last_warmup + timedelta(hours=self.frequency_hours)
        else:
            self.next_warmup = timezone.now() + timedelta(hours=self.frequency_hours)
        
        # Adjust based on popularity and recent failures
        if self.popularity_score > 0.8:
            # High popularity - warm up more frequently
            self.next_warmup = self.next_warmup - timedelta(hours=self.frequency_hours * 0.2)
        elif self.consecutive_failures > 2:
            # Recent failures - delay next attempt
            delay_hours = min(self.consecutive_failures * 2, 24)
            self.next_warmup = self.next_warmup + timedelta(hours=delay_hours)
    
    def update_popularity_score(self):
        """Update popularity score based on recent usage."""
        from datetime import timedelta
        from django.db.models import Count
        
        # Count requests in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        recent_requests = AIUsageLog.objects.filter(
            council=self.council,
            created_at__gte=week_ago
        ).count()
        
        # Update average daily requests
        self.avg_daily_requests = recent_requests / 7
        
        # Calculate popularity score (0.0 to 1.0)
        # Based on requests per day, with diminishing returns
        if recent_requests == 0:
            self.popularity_score = 0.0
        else:
            # Score increases with requests but caps at 1.0
            self.popularity_score = min(1.0, recent_requests / 50.0)


class PerformanceAlert(models.Model):
    """
    Alerts for performance issues and optimization opportunities.
    """
    ALERT_TYPES = [
        ('high_cost', 'High Cost Alert'),
        ('slow_response', 'Slow Response Time'),
        ('high_failure_rate', 'High Failure Rate'),
        ('cache_inefficiency', 'Cache Inefficiency'),
        ('budget_threshold', 'Budget Threshold Exceeded'),
        ('optimization_opportunity', 'Optimization Opportunity'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    recommendation = models.TextField(blank=True)
    
    # Related objects
    council = models.ForeignKey(Council, on_delete=models.CASCADE, null=True, blank=True)
    
    # Alert data
    metric_value = models.FloatField(null=True, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'performance_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'severity']),
            models.Index(fields=['alert_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.severity.upper()}: {self.title}"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged by a user."""
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self):
        """Mark alert as resolved."""
        self.is_active = False
        self.resolved_at = timezone.now()
        self.save()