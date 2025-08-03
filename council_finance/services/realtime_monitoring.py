"""
Real-time Monitoring Service for AI Factoid System

Provides live metrics, anomaly detection, and performance monitoring
for the production optimization dashboard.
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from django.core.cache import cache
from council_finance.models import (
    AIUsageLog, AIUsageTrend, PerformanceAnomaly,
    CostForecast, LoadBalancerConfig, DailyCostSummary
)


class RealtimeMonitoringService:
    """Provides real-time monitoring and analytics for the AI system."""
    
    def __init__(self):
        self.cache_prefix = "realtime_monitor"
        self.update_interval = 60  # seconds
        
    def get_live_metrics(self):
        """Get current system metrics with caching."""
        cache_key = f"{self.cache_prefix}:live_metrics"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_5_minutes = now - timedelta(minutes=5)
        
        # Real-time request metrics
        recent_requests = AIUsageLog.objects.filter(
            created_at__gte=last_5_minutes
        )
        
        metrics = {
            'timestamp': now.isoformat(),
            'requests_per_minute': recent_requests.count() / 5,
            'active_councils': recent_requests.values('council').distinct().count(),
            'current_hour_requests': AIUsageLog.objects.filter(
                created_at__gte=last_hour
            ).count(),
            'success_rate_5min': self._calculate_success_rate(recent_requests),
            'avg_response_time_5min': recent_requests.aggregate(
                avg=Avg('processing_time_seconds')
            )['avg'] or 0,
            'error_rate_5min': recent_requests.filter(
                success=False
            ).count() / max(recent_requests.count(), 1) * 100,
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'system_health': self._calculate_system_health(),
        }
        
        cache.set(cache_key, metrics, self.update_interval)
        return metrics
    
    def detect_anomalies(self):
        """Detect and report performance anomalies in real-time."""
        anomalies = []
        now = timezone.now()
        
        # Check for traffic spikes
        current_rpm = self._get_current_requests_per_minute()
        expected_rpm = self._get_expected_requests_per_minute()
        
        if current_rpm > expected_rpm * 2:
            anomaly = self._create_anomaly(
                'spike',
                'Requests per minute',
                expected_rpm,
                current_rpm,
                severity=3 if current_rpm > expected_rpm * 3 else 2
            )
            anomalies.append(anomaly)
        
        # Check for performance degradation
        current_response_time = self._get_current_avg_response_time()
        expected_response_time = 2.5  # seconds
        
        if current_response_time > expected_response_time * 1.5:
            anomaly = self._create_anomaly(
                'slowdown',
                'Average response time',
                expected_response_time,
                current_response_time,
                severity=4 if current_response_time > 10 else 3
            )
            anomalies.append(anomaly)
        
        # Check for high error rates
        error_rate = self._get_current_error_rate()
        if error_rate > 5:  # 5% threshold
            anomaly = self._create_anomaly(
                'error_rate',
                'Error rate percentage',
                2,
                error_rate,
                severity=5 if error_rate > 10 else 3
            )
            anomalies.append(anomaly)
        
        # Check for cost spikes
        current_hour_cost = self._get_current_hour_cost()
        avg_hour_cost = self._get_average_hour_cost()
        
        if current_hour_cost > avg_hour_cost * 1.5:
            anomaly = self._create_anomaly(
                'cost_spike',
                'Hourly cost',
                float(avg_hour_cost),
                float(current_hour_cost),
                severity=2
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def get_predictive_insights(self):
        """Generate predictive insights based on trends."""
        insights = {
            'next_hour_prediction': self._predict_next_hour(),
            'daily_forecast': self._get_daily_forecast(),
            'weekly_trend': self._analyze_weekly_trend(),
            'cost_projection': self._project_monthly_cost(),
            'optimization_recommendations': self._generate_recommendations(),
        }
        
        return insights
    
    def get_load_balancer_status(self):
        """Get current load balancer configuration and recommendations."""
        try:
            config = LoadBalancerConfig.objects.filter(is_active=True).first()
            if not config:
                return {
                    'status': 'inactive',
                    'message': 'No active load balancer configuration'
                }
            
            # Update current metrics
            rpm = self._get_current_requests_per_minute()
            config.requests_per_second = rpm / 60
            config.avg_request_time = self._get_current_avg_response_time()
            
            status = {
                'name': config.name,
                'current_instances': config.current_instances,
                'min_instances': config.min_instances,
                'max_instances': config.max_instances,
                'requests_per_second': round(config.requests_per_second, 2),
                'avg_response_time': round(config.avg_request_time, 2),
                'should_scale_up': config.should_scale_up(),
                'should_scale_down': config.should_scale_down(),
                'last_scaled': config.last_scaled_at.isoformat() if config.last_scaled_at else None,
            }
            
            # Add recommendations
            if status['should_scale_up']:
                status['recommendation'] = f"Scale up to {config.current_instances + 1} instances"
            elif status['should_scale_down']:
                status['recommendation'] = f"Scale down to {config.current_instances - 1} instances"
            else:
                status['recommendation'] = "Current configuration is optimal"
            
            config.save()
            return status
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _calculate_success_rate(self, queryset):
        """Calculate success rate from a queryset."""
        total = queryset.count()
        if total == 0:
            return 100.0
        
        successful = queryset.filter(success=True).count()
        return (successful / total) * 100
    
    def _calculate_cache_hit_rate(self):
        """Calculate cache hit rate from recent requests."""
        # This would integrate with your caching system
        # For now, return a simulated value
        return 85.5
    
    def _calculate_system_health(self):
        """Calculate overall system health score (0-100)."""
        factors = {
            'success_rate': self._get_current_success_rate() / 100,
            'response_time': min(1.0, 2.5 / max(self._get_current_avg_response_time(), 0.1)),
            'error_rate': 1 - (self._get_current_error_rate() / 100),
            'cache_performance': self._calculate_cache_hit_rate() / 100,
        }
        
        # Weighted average
        weights = {
            'success_rate': 0.3,
            'response_time': 0.3,
            'error_rate': 0.2,
            'cache_performance': 0.2,
        }
        
        health_score = sum(
            factors[key] * weights[key] 
            for key in factors
        ) * 100
        
        return round(health_score, 1)
    
    def _get_current_requests_per_minute(self):
        """Get current requests per minute."""
        last_minute = timezone.now() - timedelta(minutes=1)
        return AIUsageLog.objects.filter(
            created_at__gte=last_minute
        ).count()
    
    def _get_expected_requests_per_minute(self):
        """Get expected requests per minute based on historical data."""
        current_hour = timezone.now().hour
        
        # Get average for this hour from past week
        past_week = timezone.now().date() - timedelta(days=7)
        
        hourly_trends = AIUsageTrend.objects.filter(
            date__gte=past_week,
            hour=current_hour
        ).aggregate(avg=Avg('request_count'))
        
        # Convert hourly to per minute
        return (hourly_trends['avg'] or 10) / 60
    
    def _get_current_avg_response_time(self):
        """Get current average response time."""
        last_5_min = timezone.now() - timedelta(minutes=5)
        avg_time = AIUsageLog.objects.filter(
            created_at__gte=last_5_min
        ).aggregate(avg=Avg('processing_time_seconds'))
        
        return avg_time['avg'] or 2.5
    
    def _get_current_error_rate(self):
        """Get current error rate percentage."""
        last_5_min = timezone.now() - timedelta(minutes=5)
        recent = AIUsageLog.objects.filter(created_at__gte=last_5_min)
        
        total = recent.count()
        if total == 0:
            return 0
        
        errors = recent.filter(success=False).count()
        return (errors / total) * 100
    
    def _get_current_success_rate(self):
        """Get current success rate percentage."""
        return 100 - self._get_current_error_rate()
    
    def _get_current_hour_cost(self):
        """Get cost for current hour."""
        current_hour_start = timezone.now().replace(minute=0, second=0, microsecond=0)
        
        cost = AIUsageLog.objects.filter(
            created_at__gte=current_hour_start
        ).aggregate(total=Sum('estimated_cost'))
        
        return cost['total'] or Decimal('0')
    
    def _get_average_hour_cost(self):
        """Get average hourly cost from past week."""
        past_week = timezone.now() - timedelta(days=7)
        
        daily_costs = DailyCostSummary.objects.filter(
            date__gte=past_week.date()
        ).aggregate(avg=Avg('total_estimated_cost'))
        
        # Convert daily to hourly
        return (daily_costs['avg'] or Decimal('1')) / 24
    
    def _create_anomaly(self, anomaly_type, metric_name, expected, actual, severity=1):
        """Create and save a performance anomaly."""
        deviation = ((actual - expected) / expected) * 100
        
        anomaly = PerformanceAnomaly.objects.create(
            anomaly_type=anomaly_type,
            metric_name=metric_name,
            expected_value=expected,
            actual_value=actual,
            deviation_percentage=deviation,
            severity=severity
        )
        
        # Calculate predicted impact
        anomaly.calculate_impact()
        anomaly.save()
        
        return anomaly
    
    def _predict_next_hour(self):
        """Predict metrics for the next hour."""
        predicted_requests, predicted_cost, confidence = AIUsageTrend.calculate_predictions()
        
        if predicted_requests is None:
            return {
                'available': False,
                'message': 'Insufficient historical data for prediction'
            }
        
        return {
            'available': True,
            'predicted_requests': predicted_requests,
            'predicted_cost': round(predicted_cost, 4),
            'confidence': round(confidence, 1),
            'timestamp': (timezone.now() + timedelta(hours=1)).isoformat(),
        }
    
    def _get_daily_forecast(self):
        """Get or create daily forecast."""
        today = timezone.now().date()
        
        forecast, created = CostForecast.objects.get_or_create(
            period_type='daily',
            period_start=today,
            defaults={
                'period_end': today,
                'forecasted_cost': self._calculate_daily_forecast_cost(),
                'forecasted_requests': self._calculate_daily_forecast_requests(),
                'forecast_confidence': 85.0,
            }
        )
        
        return {
            'date': today.isoformat(),
            'forecasted_cost': float(forecast.forecasted_cost),
            'forecasted_requests': forecast.forecasted_requests,
            'confidence': forecast.forecast_confidence,
            'budget_status': 'ok' if not forecast.budget_exceeded_at else 'exceeded',
        }
    
    def _analyze_weekly_trend(self):
        """Analyze weekly usage trends."""
        past_week = timezone.now() - timedelta(days=7)
        
        weekly_data = AIUsageLog.objects.filter(
            created_at__gte=past_week
        ).aggregate(
            total_requests=Count('id'),
            total_cost=Sum('estimated_cost'),
            avg_response_time=Avg('processing_time_seconds'),
            success_rate=Avg('success')
        )
        
        return {
            'total_requests': weekly_data['total_requests'] or 0,
            'total_cost': float(weekly_data['total_cost'] or 0),
            'avg_response_time': round(weekly_data['avg_response_time'] or 0, 2),
            'success_rate': round((weekly_data['success_rate'] or 1) * 100, 1),
        }
    
    def _project_monthly_cost(self):
        """Project monthly cost based on current trends."""
        # Get average daily cost from past week
        past_week = timezone.now() - timedelta(days=7)
        
        daily_avg = DailyCostSummary.objects.filter(
            date__gte=past_week.date()
        ).aggregate(avg=Avg('total_estimated_cost'))
        
        daily_cost = daily_avg['avg'] or Decimal('0')
        days_in_month = 30  # Simplified
        
        return {
            'projected_monthly_cost': float(daily_cost * days_in_month),
            'daily_average': float(daily_cost),
            'confidence': 75.0,  # Could be more sophisticated
        }
    
    def _calculate_daily_forecast_cost(self):
        """Calculate forecasted daily cost."""
        # Simple average of past 7 days
        past_week = timezone.now() - timedelta(days=7)
        
        avg_cost = DailyCostSummary.objects.filter(
            date__gte=past_week.date()
        ).aggregate(avg=Avg('total_estimated_cost'))
        
        return avg_cost['avg'] or Decimal('5.00')
    
    def _calculate_daily_forecast_requests(self):
        """Calculate forecasted daily requests."""
        # Simple average of past 7 days
        past_week = timezone.now() - timedelta(days=7)
        
        daily_requests = AIUsageLog.objects.filter(
            created_at__gte=past_week
        ).count() / 7
        
        return int(daily_requests)
    
    def _generate_recommendations(self):
        """Generate optimization recommendations based on current metrics."""
        recommendations = []
        
        # Check response time
        avg_response_time = self._get_current_avg_response_time()
        if avg_response_time > 3.0:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'title': 'Slow Response Times Detected',
                'description': f'Average response time is {avg_response_time:.1f}s. Consider scaling up or optimizing queries.',
                'action': 'Review slow queries and consider caching improvements'
            })
        
        # Check error rate
        error_rate = self._get_current_error_rate()
        if error_rate > 2:
            recommendations.append({
                'type': 'reliability',
                'priority': 'high' if error_rate > 5 else 'medium',
                'title': 'Elevated Error Rate',
                'description': f'Error rate is {error_rate:.1f}%. Investigate failing requests.',
                'action': 'Check API logs and recent deployments'
            })
        
        # Check cost efficiency
        hourly_cost = float(self._get_current_hour_cost())
        avg_cost = float(self._get_average_hour_cost())
        
        if hourly_cost > avg_cost * 1.3:
            recommendations.append({
                'type': 'cost',
                'priority': 'medium',
                'title': 'Higher Than Average Costs',
                'description': f'Current hourly cost (£{hourly_cost:.2f}) is above average (£{avg_cost:.2f})',
                'action': 'Review request patterns and consider rate limiting'
            })
        
        # Check cache performance
        cache_hit_rate = self._calculate_cache_hit_rate()
        if cache_hit_rate < 80:
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'title': 'Low Cache Hit Rate',
                'description': f'Cache hit rate is {cache_hit_rate:.1f}%. Improve caching strategy.',
                'action': 'Review cache TTL settings and warming schedules'
            })
        
        if not recommendations:
            recommendations.append({
                'type': 'info',
                'priority': 'low',
                'title': 'System Operating Normally',
                'description': 'All metrics are within expected ranges.',
                'action': 'Continue monitoring'
            })
        
        return recommendations