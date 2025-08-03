"""
AI Analytics Dashboard Views

Provides detailed analytics, cost tracking, performance monitoring,
and optimization recommendations for the AI factoid system.
"""

import json
import logging
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from django.db.models.functions import TruncDate, TruncHour

from council_finance.models import (
    Council, AIUsageLog, DailyCostSummary, CacheWarmupSchedule, PerformanceAlert
)
from council_finance.services.ai_factoid_generator import AIFactoidGenerator

logger = logging.getLogger(__name__)


@staff_member_required
def ai_analytics_dashboard(request):
    """
    Comprehensive AI analytics dashboard with usage patterns,
    cost analysis, and performance optimization recommendations.
    """
    # Time range for analytics (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get usage statistics
    usage_stats = _calculate_usage_statistics(start_date, end_date)
    cost_analysis = _calculate_cost_analysis(start_date, end_date)
    performance_metrics = _calculate_performance_metrics(start_date, end_date)
    optimization_recommendations = _generate_optimization_recommendations()
    
    # Get recent logs for troubleshooting
    recent_logs = AIUsageLog.objects.select_related('council', 'user').order_by('-created_at')[:20]
    
    # Get active performance alerts
    active_alerts = PerformanceAlert.objects.filter(is_active=True).order_by('-created_at')[:10]
    
    # Cache warming schedule status
    warmup_schedules = CacheWarmupSchedule.objects.filter(is_active=True).select_related('council').order_by('priority', '-popularity_score')[:10]
    
    context = {
        'usage_stats': usage_stats,
        'cost_analysis': cost_analysis,
        'performance_metrics': performance_metrics,
        'optimization_recommendations': optimization_recommendations,
        'recent_logs': recent_logs,
        'active_alerts': active_alerts,
        'warmup_schedules': warmup_schedules,
        'date_range': {
            'start': start_date,
            'end': end_date
        },
        'page_title': 'AI Analytics Dashboard'
    }
    
    return render(request, 'council_finance/ai_analytics/dashboard.html', context)


@staff_member_required
def usage_analytics_api(request):
    """
    API endpoint for usage analytics data (for charts and graphs).
    """
    try:
        # Get time range from request
        days = int(request.GET.get('days', 7))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Daily usage breakdown
        daily_usage = AIUsageLog.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            total_requests=Count('id'),
            successful_requests=Count('id', filter=Q(success=True)),
            failed_requests=Count('id', filter=Q(success=False)),
            total_cost=Sum('estimated_cost'),
            avg_response_time=Avg('processing_time_seconds')
        ).order_by('day')
        
        # Model usage breakdown
        model_usage = AIUsageLog.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('model_used').annotate(
            requests=Count('id'),
            total_cost=Sum('estimated_cost'),
            avg_response_time=Avg('processing_time_seconds')
        ).order_by('-requests')
        
        # Top councils by usage
        top_councils = AIUsageLog.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('council__name', 'council__slug').annotate(
            requests=Count('id'),
            total_cost=Sum('estimated_cost')
        ).order_by('-requests')[:10]
        
        # Hourly pattern (for current day)
        today = timezone.now().date()
        hourly_pattern = AIUsageLog.objects.filter(
            created_at__date=today
        ).extra(
            select={'hour': 'extract(hour from created_at)'}
        ).values('hour').annotate(
            requests=Count('id')
        ).order_by('hour')
        
        return JsonResponse({
            'success': True,
            'daily_usage': list(daily_usage),
            'model_usage': list(model_usage),
            'top_councils': list(top_councils),
            'hourly_pattern': list(hourly_pattern),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        logger.error(f"Usage analytics API error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def cost_tracking_api(request):
    """
    API endpoint for detailed cost tracking and budget analysis.
    """
    try:
        # Get budget threshold from request (default £50/month)
        monthly_budget = float(request.GET.get('budget', 50.0))
        
        # Current month costs
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_cost = AIUsageLog.objects.filter(
            created_at__gte=current_month_start,
            success=True
        ).aggregate(total=Sum('estimated_cost'))['total'] or 0
        
        # Projected monthly cost based on current usage
        days_in_month = (current_month_start.replace(month=current_month_start.month + 1) - current_month_start).days
        days_elapsed = (timezone.now() - current_month_start).days + 1
        projected_monthly_cost = (current_month_cost / days_elapsed) * days_in_month if days_elapsed > 0 else 0
        
        # Cost breakdown by model (current month)
        model_costs = AIUsageLog.objects.filter(
            created_at__gte=current_month_start,
            success=True
        ).values('model_used').annotate(
            total_cost=Sum('estimated_cost'),
            requests=Count('id')
        ).order_by('-total_cost')
        
        # Most expensive councils (current month)
        expensive_councils = AIUsageLog.objects.filter(
            created_at__gte=current_month_start,
            success=True
        ).values('council__name', 'council__slug').annotate(
            total_cost=Sum('estimated_cost'),
            requests=Count('id')
        ).order_by('-total_cost')[:10]
        
        # Budget alerts
        budget_status = 'healthy'
        if projected_monthly_cost > monthly_budget * 0.9:
            budget_status = 'warning'
        if projected_monthly_cost > monthly_budget:
            budget_status = 'exceeded'
        
        return JsonResponse({
            'success': True,
            'current_month_cost': float(current_month_cost),
            'projected_monthly_cost': float(projected_monthly_cost),
            'monthly_budget': monthly_budget,
            'budget_utilization': (projected_monthly_cost / monthly_budget * 100) if monthly_budget > 0 else 0,
            'budget_status': budget_status,
            'model_costs': list(model_costs),
            'expensive_councils': list(expensive_councils),
            'cost_per_factoid': _calculate_cost_per_factoid(current_month_start)
        })
        
    except Exception as e:
        logger.error(f"Cost tracking API error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def create_performance_alert(request):
    """
    Create a new performance alert based on thresholds.
    """
    try:
        data = json.loads(request.body)
        alert_type = data.get('alert_type')
        threshold = float(data.get('threshold', 0))
        
        # Check if we should create the alert based on current metrics
        should_alert = False
        title = ""
        description = ""
        recommendation = ""
        metric_value = 0
        
        if alert_type == 'high_cost':
            # Check current daily cost
            today = timezone.now().date()
            daily_cost = AIUsageLog.objects.filter(
                created_at__date=today,
                success=True
            ).aggregate(total=Sum('estimated_cost'))['total'] or 0
            
            if daily_cost > threshold:
                should_alert = True
                title = f"High Daily Cost Alert"
                description = f"Daily AI cost (£{daily_cost:.4f}) exceeds threshold (£{threshold:.4f})"
                recommendation = "Consider implementing stricter rate limiting or cache warming"
                metric_value = daily_cost
        
        elif alert_type == 'slow_response':
            # Check average response time today
            today = timezone.now().date()
            avg_time = AIUsageLog.objects.filter(
                created_at__date=today,
                success=True
            ).aggregate(avg=Avg('processing_time_seconds'))['avg'] or 0
            
            if avg_time > threshold:
                should_alert = True
                title = f"Slow Response Time Alert"
                description = f"Average response time ({avg_time:.2f}s) exceeds threshold ({threshold}s)"
                recommendation = "Check OpenAI API status and consider cache warming for popular councils"
                metric_value = avg_time
        
        if should_alert:
            alert = PerformanceAlert.objects.create(
                alert_type=alert_type,
                severity='medium',
                title=title,
                description=description,
                recommendation=recommendation,
                metric_value=metric_value,
                threshold_value=threshold
            )
            
            return JsonResponse({
                'success': True,
                'alert_created': True,
                'alert': {
                    'id': alert.id,
                    'title': alert.title,
                    'severity': alert.severity,
                    'created_at': alert.created_at.isoformat()
                }
            })
        else:
            return JsonResponse({
                'success': True,
                'alert_created': False,
                'message': 'Current metrics do not exceed threshold'
            })
        
    except Exception as e:
        logger.error(f"Create performance alert error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _calculate_usage_statistics(start_date, end_date):
    """Calculate comprehensive usage statistics for the given date range."""
    logs = AIUsageLog.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    total_requests = logs.count()
    successful_requests = logs.filter(success=True).count()
    failed_requests = logs.filter(success=False).count()
    cache_hits = logs.filter(cache_hit=True).count()
    
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
    cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    
    return {
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'cache_hits': cache_hits,
        'success_rate': round(success_rate, 1),
        'cache_hit_rate': round(cache_hit_rate, 1),
        'unique_councils': logs.values('council').distinct().count(),
        'unique_users': logs.exclude(user=None).values('user').distinct().count()
    }


def _calculate_cost_analysis(start_date, end_date):
    """Calculate cost analysis for the given date range."""
    logs = AIUsageLog.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        success=True
    )
    
    total_cost = logs.aggregate(total=Sum('estimated_cost'))['total'] or 0
    total_factoids = logs.aggregate(total=Sum('factoids_generated'))['total'] or 0
    total_tokens = logs.aggregate(total=Sum('tokens_used'))['total'] or 0
    
    cost_per_factoid = (total_cost / total_factoids) if total_factoids > 0 else 0
    cost_per_request = (total_cost / logs.count()) if logs.count() > 0 else 0
    
    # Daily average
    days = (end_date - start_date).days + 1
    avg_daily_cost = total_cost / days if days > 0 else 0
    avg_daily_requests = logs.count() / days if days > 0 else 0
    
    return {
        'total_cost': float(total_cost),
        'total_factoids': total_factoids,
        'total_tokens': total_tokens,
        'cost_per_factoid': float(cost_per_factoid),
        'cost_per_request': float(cost_per_request),
        'avg_daily_cost': float(avg_daily_cost),
        'avg_daily_requests': round(avg_daily_requests, 1),
        'projected_monthly_cost': float(avg_daily_cost * 30)
    }


def _calculate_performance_metrics(start_date, end_date):
    """Calculate performance metrics for the given date range."""
    logs = AIUsageLog.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        success=True
    )
    
    avg_response_time = logs.aggregate(avg=Avg('processing_time_seconds'))['avg'] or 0
    
    # Response time percentiles (simplified)
    response_times = list(logs.values_list('processing_time_seconds', flat=True))
    response_times.sort()
    
    percentiles = {}
    if response_times:
        percentiles['p50'] = response_times[int(len(response_times) * 0.5)]
        percentiles['p90'] = response_times[int(len(response_times) * 0.9)]
        percentiles['p95'] = response_times[int(len(response_times) * 0.95)]
    
    return {
        'avg_response_time': round(avg_response_time, 2),
        'response_time_percentiles': percentiles,
        'total_processing_time': float(logs.aggregate(total=Sum('processing_time_seconds'))['total'] or 0),
        'fastest_response': min(response_times) if response_times else 0,
        'slowest_response': max(response_times) if response_times else 0
    }


def _generate_optimization_recommendations():
    """Generate optimization recommendations based on current system performance."""
    recommendations = []
    
    # Check recent performance
    yesterday = timezone.now().date() - timedelta(days=1)
    recent_logs = AIUsageLog.objects.filter(created_at__date__gte=yesterday)
    
    if recent_logs.exists():
        # High failure rate check
        failure_rate = recent_logs.filter(success=False).count() / recent_logs.count() * 100
        if failure_rate > 10:
            recommendations.append({
                'type': 'error_rate',
                'severity': 'high',
                'title': 'High Error Rate Detected',
                'description': f'Failure rate is {failure_rate:.1f}% in the last 24 hours',
                'recommendation': 'Check OpenAI API status and error logs. Consider implementing circuit breaker pattern.',
                'action': 'investigate_errors'
            })
        
        # Slow response time check
        avg_time = recent_logs.filter(success=True).aggregate(avg=Avg('processing_time_seconds'))['avg'] or 0
        if avg_time > 10:
            recommendations.append({
                'type': 'performance',
                'severity': 'medium',
                'title': 'Slow Response Times',
                'description': f'Average response time is {avg_time:.1f} seconds',
                'recommendation': 'Implement cache warming for popular councils and consider reducing token limits.',
                'action': 'optimize_performance'
            })
        
        # Cost optimization check
        daily_cost = recent_logs.filter(success=True).aggregate(total=Sum('estimated_cost'))['total'] or 0
        if daily_cost > 5.0:  # £5 per day threshold
            recommendations.append({
                'type': 'cost',
                'severity': 'medium',
                'title': 'High Daily Costs',
                'description': f'Daily cost is £{daily_cost:.2f}',
                'recommendation': 'Consider implementing more aggressive caching and rate limiting.',
                'action': 'reduce_costs'
            })
        
        # Cache efficiency check
        cache_hit_rate = recent_logs.filter(cache_hit=True).count() / recent_logs.count() * 100 if recent_logs.count() > 0 else 0
        if cache_hit_rate < 30:
            recommendations.append({
                'type': 'cache',
                'severity': 'low',
                'title': 'Low Cache Hit Rate',
                'description': f'Cache hit rate is only {cache_hit_rate:.1f}%',
                'recommendation': 'Implement proactive cache warming for frequently accessed councils.',
                'action': 'improve_caching'
            })
    
    # If no issues found, add positive feedback
    if not recommendations:
        recommendations.append({
            'type': 'good',
            'severity': 'info',
            'title': 'System Running Smoothly',
            'description': 'No performance issues detected in recent activity',
            'recommendation': 'Continue monitoring and consider proactive optimizations.',
            'action': 'maintain'
        })
    
    return recommendations


def _calculate_cost_per_factoid(since_date):
    """Calculate cost per factoid since the given date."""
    logs = AIUsageLog.objects.filter(
        created_at__gte=since_date,
        success=True
    )
    
    total_cost = logs.aggregate(total=Sum('estimated_cost'))['total'] or 0
    total_factoids = logs.aggregate(total=Sum('factoids_generated'))['total'] or 0
    
    return float(total_cost / total_factoids) if total_factoids > 0 else 0