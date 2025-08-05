"""
Event Viewer Admin Views

GOV.UK Design System inspired interface for superadmin monitoring.
Focuses on usability, accessibility, and clear information hierarchy.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from datetime import datetime, timedelta
import json
import csv

from .models import SystemEvent, EventSummary
from council_finance.models import ActivityLog
from .services.analytics_service import analytics_service
from .services.correlation_engine import correlation_engine


def superuser_required(view_func):
    """Decorator to ensure only superusers can access event viewer."""
    return user_passes_test(lambda u: u.is_superuser)(view_func)


@superuser_required
def dashboard(request):
    """
    Main event viewer dashboard - GOV.UK inspired design.
    Shows system health overview and recent activity.
    """
    # System health metrics
    now = timezone.now()
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)
    last_week = now - timedelta(days=7)
    
    # Enhanced health metrics with analytics
    recent_events = SystemEvent.objects.filter(timestamp__gte=last_24h)
    health_score_data = analytics_service.calculate_system_health_score(days_back=7)
    
    health_metrics = {
        'total_events_24h': recent_events.count(),
        'critical_events_24h': recent_events.filter(level='critical').count(),
        'error_events_24h': recent_events.filter(level='error').count(),
        'warning_events_24h': recent_events.filter(level='warning').count(),
        'unresolved_events': SystemEvent.objects.filter(resolved=False, level__in=['critical', 'error']).count(),
        'health_score': health_score_data['total_score'],
        'health_components': health_score_data['component_scores'],
    }
    
    # Get error patterns and trends
    error_patterns = correlation_engine.detect_error_patterns(hours_back=24)
    trend_analysis = analytics_service.get_trend_analysis(days_back=7)
    source_analysis = analytics_service.get_event_source_analysis(days_back=7)
    
    # Recent activity (mix of SystemEvents and ActivityLog)
    recent_system_events = SystemEvent.objects.select_related('user').filter(
        timestamp__gte=last_24h
    ).order_by('-timestamp')[:10]
    
    recent_user_activity = ActivityLog.objects.select_related('user').filter(
        created__gte=last_24h,
        activity_type__in=['create', 'update', 'delete']
    ).order_by('-created')[:10]
    
    # Event trends for the chart
    trend_data = []
    for i in range(7):
        date = (now - timedelta(days=i)).date()
        summary = EventSummary.objects.filter(date=date).first()
        trend_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'errors': summary.error_count + summary.critical_count if summary else 0,
            'warnings': summary.warning_count if summary else 0,
            'total': (summary.error_count + summary.critical_count + 
                     summary.warning_count + summary.info_count) if summary else 0,
        })
    
    trend_data.reverse()  # Show oldest to newest
    
    context = {
        'page_title': 'System Event Dashboard',
        'health_metrics': health_metrics,
        'recent_system_events': recent_system_events,
        'recent_user_activity': recent_user_activity,
        'trend_data': json.dumps(trend_data),
        'error_patterns': error_patterns[:5],  # Show top 5 patterns
        'trend_analysis': trend_analysis,
        'source_analysis': source_analysis[:10],  # Show top 10 sources
        'last_updated': now,
    }
    
    return render(request, 'event_viewer/dashboard.html', context)


@superuser_required
def event_list(request):
    """
    Event list view with filtering and search.
    GOV.UK table design with clear information hierarchy.
    """
    events = SystemEvent.objects.select_related('user', 'resolved_by').all()
    
    # Filtering
    level_filter = request.GET.get('level')
    source_filter = request.GET.get('source')
    category_filter = request.GET.get('category')
    resolved_filter = request.GET.get('resolved')
    search_query = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if level_filter:
        events = events.filter(level=level_filter)
    
    if source_filter:
        events = events.filter(source=source_filter)
    
    if category_filter:
        events = events.filter(category=category_filter)
    
    if resolved_filter:
        is_resolved = resolved_filter.lower() == 'true'
        events = events.filter(resolved=is_resolved)
    
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(exception_type__icontains=search_query)
        )
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            events = events.filter(timestamp__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            events = events.filter(timestamp__lte=to_date + timedelta(days=1))
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(events, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filter options for the form
    filter_options = {
        'levels': SystemEvent.EVENT_LEVELS,
        'sources': SystemEvent.EVENT_SOURCES,
        'categories': SystemEvent.EVENT_CATEGORIES,
    }
    
    context = {
        'page_title': 'System Events',
        'page_obj': page_obj,
        'filter_options': filter_options,
        'current_filters': {
            'level': level_filter,
            'source': source_filter,
            'category': category_filter,
            'resolved': resolved_filter,
            'search': search_query,
            'date_from': date_from,
            'date_to': date_to,
        },
        'total_events': events.count(),
    }
    
    return render(request, 'event_viewer/event_list.html', context)


@superuser_required
def event_detail(request, event_id):
    """
    Detailed view of a single event.
    Shows all available context and related events.
    """
    event = get_object_or_404(SystemEvent, id=event_id)
    
    # Get correlated events using the correlation engine
    related_events = correlation_engine.find_related_events(event)
    
    # Get similar events (fallback method)
    try:
        similar_events = event.get_similar_events(limit=5)
    except AttributeError:
        similar_events = []
    
    # Format details for display
    formatted_details = {}
    if event.details:
        formatted_details = json.dumps(event.details, indent=2)
    
    context = {
        'page_title': f'Event: {event.title}',
        'event': event,
        'related_events': related_events,
        'similar_events': similar_events,
        'formatted_details': formatted_details,
    }
    
    return render(request, 'event_viewer/event_detail.html', context)


@superuser_required
def resolve_event(request, event_id):
    """
    Mark an event as resolved.
    """
    if request.method == 'POST':
        event = get_object_or_404(SystemEvent, id=event_id)
        resolution_notes = request.POST.get('resolution_notes', '')
        
        event.mark_resolved(request.user, resolution_notes)
        
        messages.success(request, f'Event "{event.title}" marked as resolved.')
        
        # Return to event detail or list based on referrer
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        
        return redirect('event_viewer:event_detail', event_id=event.id)
    
    return redirect('event_viewer:event_list')


@superuser_required
def bulk_resolve(request):
    """
    Bulk resolve multiple events.
    """
    if request.method == 'POST':
        event_ids = request.POST.getlist('event_ids')
        resolution_notes = request.POST.get('bulk_resolution_notes', '')
        
        events = SystemEvent.objects.filter(id__in=event_ids, resolved=False)
        count = 0
        
        for event in events:
            event.mark_resolved(request.user, resolution_notes)
            count += 1
        
        messages.success(request, f'Resolved {count} events.')
    
    return redirect('event_viewer:event_list')


@superuser_required
def analytics(request):
    """
    Analytics dashboard showing trends and insights.
    """
    # Get date range (last 30 days by default)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Override with user selection if provided
    if request.GET.get('date_range'):
        days = int(request.GET.get('date_range', 30))
        start_date = end_date - timedelta(days=days)
    
    # Get summaries for the date range
    summaries = EventSummary.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Prepare chart data
    chart_data = {
        'dates': [],
        'errors': [],
        'warnings': [],
        'performance': [],
        'exceptions': [],
    }
    
    total_stats = {
        'total_events': 0,
        'total_errors': 0,
        'total_warnings': 0,
        'avg_resolution_hours': 0,
        'unique_users_affected': 0,
    }
    
    for summary in summaries:
        chart_data['dates'].append(summary.date.strftime('%Y-%m-%d'))
        chart_data['errors'].append(summary.error_count + summary.critical_count)
        chart_data['warnings'].append(summary.warning_count)
        chart_data['performance'].append(summary.performance_count)
        chart_data['exceptions'].append(summary.exception_count)
        
        total_stats['total_events'] += (summary.error_count + summary.critical_count + 
                                      summary.warning_count + summary.info_count)
        total_stats['total_errors'] += summary.error_count + summary.critical_count
        total_stats['total_warnings'] += summary.warning_count
        total_stats['unique_users_affected'] += summary.unique_users_affected
    
    # Calculate averages
    if summaries.count() > 0:
        avg_resolution = summaries.exclude(avg_resolution_hours__isnull=True).aggregate(
            avg=Count('avg_resolution_hours')
        )
        total_stats['avg_resolution_hours'] = avg_resolution.get('avg', 0) or 0
    
    # Top error types
    top_errors = SystemEvent.objects.filter(
        timestamp__gte=start_date,
        level__in=['error', 'critical']
    ).values('exception_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'page_title': 'Event Analytics',
        'chart_data': json.dumps(chart_data),
        'total_stats': total_stats,
        'top_errors': top_errors,
        'date_range_days': (end_date - start_date).days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'event_viewer/analytics.html', context)


@superuser_required
def export_events(request):
    """
    Export events to CSV for external analysis.
    """
    # Get the same filters as event_list
    events = SystemEvent.objects.select_related('user').all()
    
    # Apply same filtering logic as event_list view
    level_filter = request.GET.get('level')
    source_filter = request.GET.get('source')
    search_query = request.GET.get('search')
    
    if level_filter:
        events = events.filter(level=level_filter)
    if source_filter:
        events = events.filter(source=source_filter)
    if search_query:
        events = events.filter(title__icontains=search_query)
    
    # Limit to recent events for performance
    events = events.filter(
        timestamp__gte=timezone.now() - timedelta(days=30)
    ).order_by('-timestamp')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="system_events.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'Level', 'Source', 'Category', 'Title', 'Exception Type',
        'User', 'Request Path', 'Resolved', 'Resolution Notes'
    ])
    
    for event in events:
        writer.writerow([
            event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            event.get_level_display(),
            event.get_source_display(),
            event.get_category_display(),
            event.title,
            event.exception_type,
            event.user.username if event.user else '',
            event.request_path,
            'Yes' if event.resolved else 'No',
            event.resolution_notes,
        ])
    
    return response
