"""
Enhanced AI Monitoring Dashboard with Real-time Metrics and Predictive Analytics

Provides comprehensive monitoring, live metrics, and predictive insights
for the AI factoid system production optimization.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import json

from council_finance.services.realtime_monitoring import RealtimeMonitoringService
from council_finance.models import (
    AIUsageLog, PerformanceAnomaly, CostForecast,
    LoadBalancerConfig, AIUsageTrend
)


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def ai_monitoring_dashboard(request):
    """Enhanced monitoring dashboard with real-time metrics."""
    
    monitoring_service = RealtimeMonitoringService()
    
    # Get live metrics
    live_metrics = monitoring_service.get_live_metrics()
    
    # Detect current anomalies
    anomalies = monitoring_service.detect_anomalies()
    
    # Get predictive insights
    predictions = monitoring_service.get_predictive_insights()
    
    # Get load balancer status
    load_balancer_status = monitoring_service.get_load_balancer_status()
    
    # Get recent anomaly history
    recent_anomalies = PerformanceAnomaly.objects.filter(
        detected_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-detected_at')[:10]
    
    # Get cost forecasts
    cost_forecasts = CostForecast.objects.filter(
        period_type__in=['daily', 'weekly', 'monthly']
    ).order_by('-period_start')[:5]
    
    context = {
        'page_title': 'AI Monitoring Dashboard',
        'live_metrics': live_metrics,
        'active_anomalies': anomalies,
        'predictions': predictions,
        'load_balancer': load_balancer_status,
        'recent_anomalies': recent_anomalies,
        'cost_forecasts': cost_forecasts,
        'last_updated': timezone.now(),
    }
    
    return render(request, 'council_finance/ai_monitoring/dashboard.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_live_metrics(request):
    """API endpoint for live metrics updates."""
    monitoring_service = RealtimeMonitoringService()
    
    metrics = monitoring_service.get_live_metrics()
    anomalies = monitoring_service.detect_anomalies()
    
    # Format anomalies for JSON response
    anomaly_data = []
    for anomaly in anomalies:
        anomaly_data.append({
            'type': anomaly.anomaly_type,
            'metric': anomaly.metric_name,
            'severity': anomaly.severity,
            'expected': anomaly.expected_value,
            'actual': anomaly.actual_value,
            'deviation': round(anomaly.deviation_percentage, 1),
        })
    
    return JsonResponse({
        'success': True,
        'metrics': metrics,
        'anomalies': anomaly_data,
        'timestamp': timezone.now().isoformat(),
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_hourly_trends(request):
    """Get hourly trend data for charts."""
    hours = int(request.GET.get('hours', 24))
    
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Get hourly trends
    trends = AIUsageTrend.objects.filter(
        date__gte=start_time.date()
    ).order_by('date', 'hour')
    
    # Format for charts
    chart_data = {
        'labels': [],
        'requests': [],
        'costs': [],
        'response_times': [],
        'success_rates': [],
    }
    
    for trend in trends:
        timestamp = f"{trend.date} {trend.hour:02d}:00"
        chart_data['labels'].append(timestamp)
        chart_data['requests'].append(trend.request_count)
        chart_data['costs'].append(float(trend.total_cost))
        chart_data['response_times'].append(trend.avg_response_time)
        chart_data['success_rates'].append(trend.success_rate)
    
    return JsonResponse({
        'success': True,
        'data': chart_data,
        'period': f'{hours} hours',
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def resolve_anomaly(request):
    """Mark an anomaly as resolved."""
    try:
        data = json.loads(request.body)
        anomaly_id = data.get('anomaly_id')
        notes = data.get('notes', '')
        
        anomaly = PerformanceAnomaly.objects.get(id=anomaly_id)
        anomaly.auto_resolved = False
        anomaly.resolved_at = timezone.now()
        anomaly.resolution_notes = notes
        anomaly.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Anomaly resolved successfully'
        })
        
    except PerformanceAnomaly.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Anomaly not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def update_load_balancer(request):
    """Update load balancer configuration."""
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'scale_up' or 'scale_down'
        
        config = LoadBalancerConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({
                'success': False,
                'error': 'No active load balancer configuration'
            }, status=404)
        
        if action == 'scale_up' and config.current_instances < config.max_instances:
            config.current_instances += 1
            config.last_scaled_at = timezone.now()
            config.save()
            message = f'Scaled up to {config.current_instances} instances'
            
        elif action == 'scale_down' and config.current_instances > config.min_instances:
            config.current_instances -= 1
            config.last_scaled_at = timezone.now()
            config.save()
            message = f'Scaled down to {config.current_instances} instances'
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action or limit reached'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'current_instances': config.current_instances
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def update_budget_alert(request):
    """Update budget alert settings."""
    try:
        data = json.loads(request.body)
        period_type = data.get('period_type')
        budget_limit = data.get('budget_limit')
        
        # Get or create forecast for current period
        if period_type == 'daily':
            period_start = timezone.now().date()
            period_end = period_start
        elif period_type == 'weekly':
            period_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
            period_end = period_start + timedelta(days=6)
        elif period_type == 'monthly':
            period_start = timezone.now().date().replace(day=1)
            # Calculate last day of month
            if period_start.month == 12:
                period_end = period_start.replace(day=31)
            else:
                period_end = period_start.replace(month=period_start.month + 1) - timedelta(days=1)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid period type'
            }, status=400)
        
        forecast, created = CostForecast.objects.get_or_create(
            period_type=period_type,
            period_start=period_start,
            defaults={
                'period_end': period_end,
                'forecasted_cost': 0,
                'forecasted_requests': 0,
                'forecast_confidence': 0,
            }
        )
        
        forecast.budget_limit = budget_limit
        forecast.save()
        
        # Check if alert should be triggered
        alert_triggered = forecast.check_budget_alert()
        
        return JsonResponse({
            'success': True,
            'message': f'Budget limit set to £{budget_limit}',
            'alert_triggered': alert_triggered
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)