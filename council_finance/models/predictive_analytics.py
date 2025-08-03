"""
Predictive Analytics Models for AI Factoid System

Provides trend analysis, cost forecasting, and performance predictions
to optimize system operations and budget management.
"""

from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
import json
import statistics


class AIUsageTrend(models.Model):
    """
    Tracks and analyzes usage patterns for predictive modeling.
    """
    date = models.DateField(default=timezone.now)
    hour = models.IntegerField(default=0)  # 0-23
    
    # Usage metrics
    request_count = models.IntegerField(default=0)
    unique_councils = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0.0)
    success_rate = models.FloatField(default=100.0)
    
    # Cost metrics
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    avg_cost_per_request = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    
    # Predictions (calculated daily)
    predicted_next_hour_requests = models.IntegerField(null=True, blank=True)
    predicted_next_hour_cost = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    prediction_confidence = models.FloatField(null=True, blank=True)  # 0-100%
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_usage_trend'
        unique_together = ['date', 'hour']
        ordering = ['-date', '-hour']
        indexes = [
            models.Index(fields=['date', 'hour']),
            models.Index(fields=['request_count']),
        ]
    
    def __str__(self):
        return f"{self.date} {self.hour:02d}:00 - {self.request_count} requests"
    
    @classmethod
    def calculate_predictions(cls, lookback_days=7):
        """Calculate predictions for the next hour based on historical data using simple moving average."""
        now = timezone.now()
        current_hour = now.hour
        
        # Get historical data for the same hour over past days
        historical = cls.objects.filter(
            date__gte=now.date() - timedelta(days=lookback_days),
            hour=current_hour
        ).order_by('date')
        
        if historical.count() < 3:  # Need minimum data for prediction
            return None, None, 0.0
        
        # Get data points
        requests = [h.request_count for h in historical]
        costs = [float(h.total_cost) for h in historical]
        
        # Simple weighted moving average (recent data weighted more)
        weights = list(range(1, len(requests) + 1))
        total_weight = sum(weights)
        
        predicted_requests = sum(r * w for r, w in zip(requests, weights)) / total_weight
        predicted_cost = sum(c * w for c, w in zip(costs, weights)) / total_weight
        
        # Calculate confidence based on data consistency
        request_std = statistics.stdev(requests) if len(requests) > 1 else 0
        cost_std = statistics.stdev(costs) if len(costs) > 1 else 0
        
        # Lower standard deviation = higher confidence
        avg_request = statistics.mean(requests)
        avg_cost = statistics.mean(costs)
        
        request_confidence = max(0, 100 - (request_std / avg_request * 100)) if avg_request > 0 else 0
        cost_confidence = max(0, 100 - (cost_std / avg_cost * 100)) if avg_cost > 0 else 0
        confidence = (request_confidence + cost_confidence) / 2
        
        return int(predicted_requests), predicted_cost, confidence


class CostForecast(models.Model):
    """
    Monthly and yearly cost forecasts based on usage trends.
    """
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Actual metrics (for completed periods)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    actual_requests = models.IntegerField(null=True, blank=True)
    
    # Forecasted metrics
    forecasted_cost = models.DecimalField(max_digits=10, decimal_places=4)
    forecasted_requests = models.IntegerField()
    forecast_confidence = models.FloatField()  # 0-100%
    
    # Budget alerts
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_alert_sent = models.BooleanField(default=False)
    budget_exceeded_at = models.DateTimeField(null=True, blank=True)
    
    # Recommendations
    cost_optimization_tips = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cost_forecast'
        unique_together = ['period_type', 'period_start']
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['period_type', 'period_start']),
            models.Index(fields=['budget_exceeded_at']),
        ]
    
    def __str__(self):
        return f"{self.period_type} forecast {self.period_start} - £{self.forecasted_cost}"
    
    def check_budget_alert(self):
        """Check if budget alert should be sent."""
        if not self.budget_limit:
            return False
        
        if self.actual_cost and self.actual_cost > self.budget_limit * 0.8:
            if not self.budget_alert_sent:
                self.budget_alert_sent = True
                if self.actual_cost > self.budget_limit:
                    self.budget_exceeded_at = timezone.now()
                self.save()
                return True
        return False
    
    def generate_optimization_tips(self):
        """Generate cost optimization recommendations."""
        tips = []
        
        if self.forecasted_cost > self.budget_limit * 0.9:
            tips.append({
                'priority': 'high',
                'tip': 'Consider reducing factoid generation frequency during low-traffic hours',
                'potential_savings': '15-20%'
            })
        
        if self.actual_requests and self.actual_requests > 1000:
            tips.append({
                'priority': 'medium',
                'tip': 'Implement request batching for multiple council queries',
                'potential_savings': '10-15%'
            })
        
        tips.append({
            'priority': 'low',
            'tip': 'Monitor cache hit rates and adjust TTL for better efficiency',
            'potential_savings': '5-10%'
        })
        
        self.cost_optimization_tips = tips
        self.save()


class PerformanceAnomaly(models.Model):
    """
    Detects and tracks performance anomalies for proactive monitoring.
    """
    ANOMALY_TYPES = [
        ('spike', 'Traffic Spike'),
        ('slowdown', 'Performance Slowdown'),
        ('error_rate', 'High Error Rate'),
        ('cost_spike', 'Cost Spike'),
        ('cache_miss', 'High Cache Miss Rate'),
    ]
    
    anomaly_type = models.CharField(max_length=20, choices=ANOMALY_TYPES)
    detected_at = models.DateTimeField(default=timezone.now)
    severity = models.IntegerField(default=1)  # 1-5, 5 being most severe
    
    # Anomaly details
    metric_name = models.CharField(max_length=100)
    expected_value = models.FloatField()
    actual_value = models.FloatField()
    deviation_percentage = models.FloatField()
    
    # Context
    affected_councils = models.JSONField(default=list)
    affected_features = models.JSONField(default=list)
    
    # Resolution
    auto_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Predictions
    predicted_duration = models.IntegerField(null=True, blank=True)  # minutes
    predicted_impact = models.JSONField(default=dict)  # cost, performance impact
    
    class Meta:
        db_table = 'performance_anomaly'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['anomaly_type', 'detected_at']),
            models.Index(fields=['severity', 'auto_resolved']),
        ]
    
    def __str__(self):
        return f"{self.get_anomaly_type_display()} - Severity {self.severity} at {self.detected_at}"
    
    def calculate_impact(self):
        """Calculate the predicted impact of this anomaly."""
        impact = {}
        
        if self.anomaly_type == 'cost_spike':
            impact['estimated_extra_cost'] = (self.actual_value - self.expected_value) * 24  # Daily impact
            impact['budget_impact'] = 'high' if self.deviation_percentage > 50 else 'medium'
        
        elif self.anomaly_type == 'slowdown':
            impact['user_experience_impact'] = 'severe' if self.actual_value > 10 else 'moderate'
            impact['estimated_affected_users'] = len(self.affected_councils) * 10  # Rough estimate
        
        elif self.anomaly_type == 'error_rate':
            impact['failed_requests'] = int(self.actual_value * 100)  # Assuming percentage
            impact['reliability_impact'] = 'critical' if self.actual_value > 0.1 else 'moderate'
        
        self.predicted_impact = impact
        return impact


class LoadBalancerConfig(models.Model):
    """
    Dynamic load balancing configuration for high-traffic scenarios.
    """
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    # Thresholds
    requests_per_second_threshold = models.IntegerField(default=10)
    cpu_threshold = models.FloatField(default=80.0)  # percentage
    memory_threshold = models.FloatField(default=85.0)  # percentage
    
    # Scaling rules
    min_instances = models.IntegerField(default=1)
    max_instances = models.IntegerField(default=5)
    scale_up_cooldown = models.IntegerField(default=300)  # seconds
    scale_down_cooldown = models.IntegerField(default=600)  # seconds
    
    # Current state
    current_instances = models.IntegerField(default=1)
    last_scaled_at = models.DateTimeField(null=True, blank=True)
    
    # Performance metrics
    avg_request_time = models.FloatField(default=0.0)
    requests_per_second = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'load_balancer_config'
    
    def __str__(self):
        return f"{self.name} - {self.current_instances} instances"
    
    def should_scale_up(self):
        """Determine if we should scale up."""
        if self.current_instances >= self.max_instances:
            return False
        
        if self.last_scaled_at:
            cooldown_elapsed = (timezone.now() - self.last_scaled_at).total_seconds()
            if cooldown_elapsed < self.scale_up_cooldown:
                return False
        
        return self.requests_per_second > self.requests_per_second_threshold
    
    def should_scale_down(self):
        """Determine if we should scale down."""
        if self.current_instances <= self.min_instances:
            return False
        
        if self.last_scaled_at:
            cooldown_elapsed = (timezone.now() - self.last_scaled_at).total_seconds()
            if cooldown_elapsed < self.scale_down_cooldown:
                return False
        
        return self.requests_per_second < (self.requests_per_second_threshold * 0.5)