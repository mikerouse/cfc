"""
API endpoints for cache warming progress tracking.

Provides real-time updates on counter cache warming status for the frontend.
"""

import json
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required

from council_finance.services.counter_cache_service import counter_cache_service
from council_finance.models import SiteCounter, GroupCounter


@never_cache
@require_http_methods(["GET"])
def cache_warming_progress(request):
    """
    Get current cache warming progress.
    
    Returns:
    - status: 'idle', 'running', 'completed', 'failed'
    - progress details if warming is active
    - current counter states
    """
    progress_key = request.GET.get('progress_key', 'counter_cache_warming_progress')
    progress_info = cache.get(progress_key)
    
    # Check current counter states
    counter_states = []
    
    # Check site counters
    for sc in SiteCounter.objects.filter(promote_homepage=True):
        year_label = sc.year.label if sc.year else None
        
        try:
            value = counter_cache_service.get_counter_value(
                counter_slug=sc.counter.slug,
                year_label=year_label,
                allow_expensive_calculation=False
            )
            if value == -1:
                # Check if calculation has been stuck for too long (>20 minutes)
                lock_key = "site_totals_agent_run_lock"
                if cache.get(lock_key):
                    # Get lock timestamp if possible
                    state = 'calculating'
                    display_value = 'Calculating...'
                else:
                    # No lock found but still returning -1, this indicates a problem
                    # Try allowing one expensive calculation 
                    try:
                        value = counter_cache_service.get_counter_value(
                            counter_slug=sc.counter.slug,
                            year_label=year_label,
                            allow_expensive_calculation=True
                        )
                        if value == -1:
                            state = 'error'  
                            display_value = 'Calculation failed'
                        else:
                            state = 'ready'
                            display_value = sc.counter.format_value(float(value))
                    except Exception as e:
                        state = 'error'
                        display_value = 'Error'
            else:
                state = 'ready'
                display_value = sc.counter.format_value(float(value))
        except Exception:
            state = 'error'
            display_value = 'Error'
        
        counter_states.append({
            'slug': sc.slug,
            'name': sc.name,
            'counter_slug': sc.counter.slug,
            'state': state,
            'display_value': display_value
        })
    
    # Check group counters
    for gc in GroupCounter.objects.filter(promote_homepage=True):
        year_label = gc.year.label if gc.year else None
        
        try:
            value = counter_cache_service.get_counter_value(
                counter_slug=gc.counter.slug,
                year_label=year_label,
                allow_expensive_calculation=False
            )
            if value == -1:
                # Check if calculation has been stuck for too long (>20 minutes)
                lock_key = "site_totals_agent_run_lock"
                if cache.get(lock_key):
                    state = 'calculating'
                    display_value = 'Calculating...'
                else:
                    # No lock found but still returning -1, try expensive calculation
                    try:
                        value = counter_cache_service.get_counter_value(
                            counter_slug=gc.counter.slug,
                            year_label=year_label,
                            allow_expensive_calculation=True
                        )
                        if value == -1:
                            state = 'error'
                            display_value = 'Calculation failed'
                        else:
                            state = 'ready'
                            display_value = gc.counter.format_value(float(value))
                    except Exception as e:
                        state = 'error'
                        display_value = 'Error'
            else:
                state = 'ready'
                display_value = gc.counter.format_value(float(value))
        except Exception:
            state = 'error'
            display_value = 'Error'
        
        counter_states.append({
            'slug': gc.slug,
            'name': gc.name,
            'counter_slug': gc.counter.slug,
            'state': state,
            'display_value': display_value
        })
    
    response_data = {
        'counter_states': counter_states,
        'warming_progress': progress_info,
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(response_data)


@never_cache
@staff_member_required
@require_http_methods(["POST"]) 
def trigger_cache_warming(request):
    """
    Trigger background cache warming process.
    
    Only available to staff members to prevent abuse.
    """
    import subprocess
    import threading
    from django.conf import settings
    
    def run_warming():
        """Run cache warming in background thread"""
        try:
            # Run the management command in background
            subprocess.run([
                'python', 'manage.py', 'warmup_counter_cache', 
                '--background'
            ], cwd=settings.BASE_DIR, timeout=600)  # 10 minute timeout
        except subprocess.TimeoutExpired:
            # Update progress with timeout error
            progress_info = {
                'status': 'failed',
                'current_step': 'Cache warming timed out after 10 minutes',
                'error': 'Timeout',
                'failed_at': timezone.now().isoformat(),
                'last_updated': timezone.now().isoformat()
            }
            cache.set('counter_cache_warming_progress', progress_info, 3600)
        except Exception as e:
            # Update progress with error
            progress_info = {
                'status': 'failed', 
                'current_step': f'Cache warming failed: {str(e)}',
                'error': str(e),
                'failed_at': timezone.now().isoformat(),
                'last_updated': timezone.now().isoformat()
            }
            cache.set('counter_cache_warming_progress', progress_info, 3600)
    
    # Check if warming is already in progress
    progress_info = cache.get('counter_cache_warming_progress')
    if progress_info and progress_info.get('status') == 'running':
        return JsonResponse({
            'status': 'already_running',
            'message': 'Cache warming is already in progress'
        })
    
    # Initialize progress tracking
    progress_info = {
        'status': 'running',
        'started_at': timezone.now().isoformat(),
        'current_step': 'Starting cache warming...',
        'counters_completed': 0,
        'counters_total': 0,
        'counters_failed': 0,
        'last_updated': timezone.now().isoformat()
    }
    cache.set('counter_cache_warming_progress', progress_info, 3600)
    
    # Start background thread
    thread = threading.Thread(target=run_warming)
    thread.daemon = True
    thread.start()
    
    return JsonResponse({
        'status': 'started',
        'message': 'Cache warming started in background',
        'progress_key': 'counter_cache_warming_progress'
    })


@never_cache
@require_http_methods(["GET"])
def counter_health_check(request):
    """
    Quick health check for homepage counters.
    
    Returns summary of which counters are ready vs calculating.
    """
    calculating_count = 0
    ready_count = 0
    error_count = 0
    
    # Check all promoted counters
    promoted_counters = list(SiteCounter.objects.filter(promote_homepage=True)) + \
                      list(GroupCounter.objects.filter(promote_homepage=True))
    
    for counter in promoted_counters:
        if hasattr(counter, 'year'):  # SiteCounter
            year_label = counter.year.label if counter.year else None
            counter_slug = counter.counter.slug
        else:  # GroupCounter
            year_label = counter.year.label if counter.year else None
            counter_slug = counter.counter.slug
        
        try:
            value = counter_cache_service.get_counter_value(
                counter_slug=counter_slug,
                year_label=year_label,
                allow_expensive_calculation=False
            )
            if value == -1:
                calculating_count += 1
            else:
                ready_count += 1
        except Exception:
            error_count += 1
    
    return JsonResponse({
        'ready': ready_count,
        'calculating': calculating_count,
        'error': error_count,
        'total': len(promoted_counters),
        'all_ready': calculating_count == 0 and error_count == 0,
        'timestamp': timezone.now().isoformat()
    })