"""
Event Viewer Analytics Service

Provides advanced analytics, health scoring, and trend analysis
for system monitoring and performance assessment.
"""

import logging
from datetime import timedelta, date, datetime
from statistics import mean, stdev
from django.utils import timezone
from django.db.models import Count, Q, Avg, Max, Min
from django.core.cache import cache
from ..models import SystemEvent, EventSummary
from ..settings import event_viewer_config

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Provides analytics capabilities including health scoring,
    trend analysis, and performance metrics.
    """
    
    def __init__(self):
        self.config = event_viewer_config
    
    def calculate_system_health_score(self, days_back=7):
        """
        Calculate a comprehensive system health score (0-100).
        Higher scores indicate better system health.
        """
        cache_key = f'event_viewer_health_score_{days_back}d'
        cached_score = cache.get(cache_key)
        if cached_score is not None:
            return cached_score
        
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        # Get weights from configuration
        weights = self.config.get_health_score_weights()
        if not weights:
            weights = {
                'error_rate': 0.4,
                'critical_events': 0.3,
                'security_incidents': 0.2,
                'system_availability': 0.1,
            }
        
        scores = {}
        
        # 1. Error Rate Score (0-100, lower error rate = higher score)
        total_events = SystemEvent.objects.filter(timestamp__gte=cutoff_date).count()
        error_events = SystemEvent.objects.filter(
            timestamp__gte=cutoff_date,
            level__in=['error', 'critical']
        ).count()
        
        if total_events > 0:
            error_rate = error_events / total_events
            # Convert error rate to score (inverse relationship)
            scores['error_rate'] = max(0, min(100, 100 - (error_rate * 200)))
        else:
            scores['error_rate'] = 100  # No events = perfect score
        
        # 2. Critical Events Score (fewer critical events = higher score)
        critical_events = SystemEvent.objects.filter(
            timestamp__gte=cutoff_date,
            level='critical'
        ).count()
        
        # Score based on critical events per day
        critical_per_day = critical_events / days_back
        scores['critical_events'] = max(0, min(100, 100 - (critical_per_day * 10)))
        
        # 3. Security Incidents Score (fewer security incidents = higher score)
        security_events = SystemEvent.objects.filter(
            timestamp__gte=cutoff_date,
            category='security',
            level__in=['warning', 'error', 'critical']
        ).count()
        
        security_per_day = security_events / days_back
        scores['security_incidents'] = max(0, min(100, 100 - (security_per_day * 15)))
        
        # 4. System Availability Score (based on uptime indicators)
        # For now, we'll use a simple heuristic based on error patterns
        # In a full implementation, this would integrate with actual uptime monitoring
        daily_error_counts = []
        for i in range(days_back):
            day_start = cutoff_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            daily_errors = SystemEvent.objects.filter(
                timestamp__range=(day_start, day_end),
                level__in=['error', 'critical']
            ).count()
            daily_error_counts.append(daily_errors)
        
        if daily_error_counts:
            # Days with very high error counts indicate potential downtime/issues
            high_error_days = sum(1 for count in daily_error_counts if count > 20)
            availability_score = max(0, 100 - (high_error_days / days_back * 50))
        else:
            availability_score = 100
        
        scores['system_availability'] = availability_score
        
        # Calculate weighted total score
        total_score = sum(
            scores[component] * weights.get(component, 0)
            for component in scores
        )
        
        # Cache the result for 1 hour
        cache.set(cache_key, {
            'total_score': round(total_score, 1),
            'component_scores': scores,
            'weights': weights,
            'calculated_at': timezone.now(),
            'days_analyzed': days_back
        }, 3600)
        
        return cache.get(cache_key)
    
    def get_trend_analysis(self, days_back=30):
        """
        Analyze trends in system events over the specified time period.
        """
        cache_key = f'event_viewer_trends_{days_back}d'
        cached_trends = cache.get(cache_key)
        if cached_trends is not None:
            return cached_trends
        
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        # Daily event counts
        daily_stats = []
        for i in range(days_back):
            day_start = cutoff_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_stats = {
                'date': day_start.date(),
                'total_events': SystemEvent.objects.filter(
                    timestamp__range=(day_start, day_end)
                ).count(),
                'error_events': SystemEvent.objects.filter(
                    timestamp__range=(day_start, day_end),
                    level__in=['error', 'critical']
                ).count(),
                'critical_events': SystemEvent.objects.filter(
                    timestamp__range=(day_start, day_end),
                    level='critical'
                ).count(),
                'unique_users': SystemEvent.objects.filter(
                    timestamp__range=(day_start, day_end),
                    user__isnull=False
                ).values('user').distinct().count()
            }
            daily_stats.append(day_stats)
        
        # Calculate trends
        error_counts = [day['error_events'] for day in daily_stats]
        total_counts = [day['total_events'] for day in daily_stats]
        
        trends = {
            'daily_stats': daily_stats,
            'error_trend': self._calculate_trend(error_counts),
            'total_events_trend': self._calculate_trend(total_counts),
            'average_errors_per_day': mean(error_counts) if error_counts else 0,
            'average_total_per_day': mean(total_counts) if total_counts else 0,
            'peak_error_day': max(daily_stats, key=lambda x: x['error_events']) if daily_stats else None,
            'quietest_day': min(daily_stats, key=lambda x: x['total_events']) if daily_stats else None,
        }
        
        # Cache for 2 hours
        cache.set(cache_key, trends, 7200)
        return trends
    
    def _calculate_trend(self, values):
        """Calculate trend direction and strength for a series of values."""
        if len(values) < 2:
            return {'direction': 'stable', 'strength': 0}
        
        # Simple linear trend calculation
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = mean(values)
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine direction and strength
        if abs(slope) < 0.1:
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        strength = min(abs(slope), 5) / 5  # Normalize to 0-1
        
        return {
            'direction': direction,
            'strength': round(strength, 2),
            'slope': round(slope, 3)
        }
    
    def get_event_source_analysis(self, days_back=7):
        """Analyze events by source to identify problematic systems."""
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        source_stats = SystemEvent.objects.filter(
            timestamp__gte=cutoff_date
        ).values(
            'source'
        ).annotate(
            total_events=Count('id'),
            error_events=Count('id', filter=Q(level__in=['error', 'critical'])),
            critical_events=Count('id', filter=Q(level='critical')),
            unique_users=Count('user', distinct=True, filter=Q(user__isnull=False))
        ).order_by('-error_events')
        
        # Calculate error rates and risk scores
        for stat in source_stats:
            if stat['total_events'] > 0:
                stat['error_rate'] = round(stat['error_events'] / stat['total_events'] * 100, 1)
                # Risk score based on error rate and volume
                stat['risk_score'] = min(100, stat['error_rate'] + (stat['critical_events'] * 5))
            else:
                stat['error_rate'] = 0
                stat['risk_score'] = 0
        
        return list(source_stats)
    
    def get_user_activity_analysis(self, days_back=7):
        """Analyze user-related events to identify problematic patterns."""
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        user_stats = SystemEvent.objects.filter(
            timestamp__gte=cutoff_date,
            user__isnull=False
        ).values(
            'user__username', 'user__id'
        ).annotate(
            total_events=Count('id'),
            error_events=Count('id', filter=Q(level__in=['error', 'critical'])),
            security_events=Count('id', filter=Q(category='security'))
        ).filter(
            total_events__gte=5  # Only users with significant activity
        ).order_by('-error_events')
        
        return list(user_stats)
    
    def create_daily_summary(self, target_date=None):
        """Create or update a daily summary for the specified date."""
        if target_date is None:
            target_date = timezone.now().date() - timedelta(days=1)
        
        # Check if summary already exists
        summary, created = EventSummary.objects.get_or_create(
            date=target_date,
            defaults={}
        )
        
        # Calculate stats for the day
        day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        
        events = SystemEvent.objects.filter(timestamp__range=(day_start, day_end))
        
        # Update summary fields
        summary.total_events = events.count()
        summary.critical_events = events.filter(level='critical').count()
        summary.error_events = events.filter(level='error').count()
        summary.warning_events = events.filter(level='warning').count()
        summary.info_events = events.filter(level='info').count()
        summary.debug_events = events.filter(level='debug').count()
        
        summary.unique_users = events.filter(user__isnull=False).values('user').distinct().count()
        summary.unique_sources = events.values('source').distinct().count()
        
        # Top event sources
        top_sources = events.values('source').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        summary.top_sources = {item['source']: item['count'] for item in top_sources}
        
        # Top error categories
        top_categories = events.filter(
            level__in=['error', 'critical']
        ).values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        summary.top_error_categories = {item['category']: item['count'] for item in top_categories}
        
        # Calculate health score for this day
        if summary.total_events > 0:
            error_rate = (summary.error_events + summary.critical_events) / summary.total_events
            health_score = max(0, min(100, 100 - (error_rate * 100)))
        else:
            health_score = 100
        
        summary.health_score = round(health_score, 1)
        summary.updated_at = timezone.now()
        
        summary.save()
        return summary
    
    def get_performance_metrics(self, days_back=7):
        """Get performance metrics for the Event Viewer system itself."""
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        events = SystemEvent.objects.filter(timestamp__gte=cutoff_date)
        
        metrics = {
            'total_events_captured': events.count(),
            'events_per_day': events.count() / days_back,
            'storage_efficiency': {
                'unique_fingerprints': events.values('fingerprint').distinct().count(),
                'total_events': events.count(),
                'deduplication_ratio': 0
            },
            'source_distribution': list(events.values('source').annotate(
                count=Count('id')
            ).order_by('-count')),
            'response_times': {
                # These would be populated by actual performance monitoring
                'dashboard_load_time': 'Not implemented',
                'search_performance': 'Not implemented',
                'export_performance': 'Not implemented'
            }
        }
        
        # Calculate deduplication efficiency
        if metrics['storage_efficiency']['total_events'] > 0:
            metrics['storage_efficiency']['deduplication_ratio'] = round(
                (1 - metrics['storage_efficiency']['unique_fingerprints'] / 
                 metrics['storage_efficiency']['total_events']) * 100, 1
            )
        
        return metrics


# Global analytics service instance
analytics_service = AnalyticsService()