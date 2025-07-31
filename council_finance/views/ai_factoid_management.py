"""
AI Factoid Management Views

Provides administrative interface for managing AI factoid generation,
viewing data passed to AI, and configuring AI parameters.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.utils import timezone

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer

logger = logging.getLogger(__name__)


@staff_member_required
def ai_factoid_management_dashboard(request):
    """
    Main dashboard for AI factoid management.
    
    Shows overview of councils, recent AI calls, and configuration options.
    """
    # Get councils with recent factoid activity
    councils = Council.objects.all().order_by('name')[:50]
    
    # Get system status
    generator = AIFactoidGenerator()
    openai_available = generator.client is not None
    
    context = {
        'councils': councils,
        'openai_available': openai_available,
        'total_councils': Council.objects.count(),
        'page_title': 'AI Factoid Management',
        'dashboard_stats': {
            'councils_total': Council.objects.count(),
            'openai_configured': openai_available,
            'cache_backend': str(cache.__class__.__name__),
        }
    }
    
    return render(request, 'council_finance/ai_factoid_management/dashboard.html', context)


@staff_member_required
def council_ai_data_inspector(request, council_slug):
    """
    Detailed inspector for council data that gets sent to AI.
    
    Shows the complete data structure, financial time series,
    and peer comparisons that would be sent to OpenAI.
    """
    council = get_object_or_404(Council, slug=council_slug)
    
    # Gather the same data that would be sent to AI
    gatherer = CouncilDataGatherer()
    council_data = gatherer.gather_council_data(council)
    
    # Debug logging
    logger.info(f"[INSPECTOR] Council: {council.slug}")
    logger.info(f"[INSPECTOR] Council data keys: {list(council_data.keys())}")
    fts = council_data.get('financial_time_series', {})
    logger.info(f"[INSPECTOR] Financial time series fields: {len(fts)}")
    if fts:
        logger.info(f"[INSPECTOR] First FTS field: {list(fts.keys())[0]} = {fts[list(fts.keys())[0]]}")
    else:
        logger.warning(f"[INSPECTOR] No financial time series data found for {council.slug}")
    
    # Get AI generator for prompt building
    generator = AIFactoidGenerator()
    
    # Build the actual prompt that would be sent to OpenAI
    sample_prompt = generator._build_analysis_prompt(council_data, limit=3, style='news_ticker')
    
    # More debug logging
    if "financial_data\": {}" in sample_prompt:
        logger.warning(f"[INSPECTOR] Empty financial_data detected in prompt for {council.slug}")
        # Log more details when this happens
        logger.warning(f"[INSPECTOR] Raw financial_time_series: {council_data.get('financial_time_series', 'NOT_FOUND')}")
    else:
        logger.info(f"[INSPECTOR] Prompt contains financial data for {council.slug}")
    
    # Check cache status
    cache_key = f"ai_factoids:{council_slug}"
    cached_factoids = cache.get(cache_key)
    cache_status = 'cached' if cached_factoids else 'not_cached'
    
    # Calculate financial_metrics carefully
    financial_metrics = []
    if council_data and council_data.get('financial_time_series'):
        fts = council_data.get('financial_time_series', {})
        financial_metrics = list(fts.keys())
        logger.info(f"[INSPECTOR] Setting financial_metrics: {len(financial_metrics)} items")
    else:
        logger.warning(f"[INSPECTOR] No financial_time_series data for context")
    
    context = {
        'council': council,
        'council_data': council_data,
        'ai_prompt': sample_prompt,
        'cache_status': cache_status,
        'cached_factoids': cached_factoids,
        'data_keys': list(council_data.keys()) if council_data else [],
        'financial_metrics': financial_metrics,
        'page_title': f'AI Data Inspector - {council.name}'
    }
    
    return render(request, 'council_finance/ai_factoid_management/data_inspector.html', context)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def test_ai_generation(request):
    """
    Test AI factoid generation with custom parameters.
    
    Allows testing different numbers of factoids, styles, and viewing
    the complete request/response cycle.
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        council_slug = data.get('council_slug')
        limit = int(data.get('limit', 3))
        style = data.get('style', 'news_ticker')
        force_refresh = data.get('force_refresh', False)
        
        council = get_object_or_404(Council, slug=council_slug)
        
        # Clear cache if requested
        if force_refresh:
            cache_key = f"ai_factoids:{council_slug}"
            cache.delete(cache_key)
            cache_key_data = f"ai_council_data:{council_slug}"
            cache.delete(cache_key_data)
        
        # Gather council data
        gatherer = CouncilDataGatherer()
        council_data = gatherer.gather_council_data(council)
        
        # Generate AI prompt
        generator = AIFactoidGenerator()
        ai_prompt = generator._build_analysis_prompt(council_data, limit=limit, style=style)
        
        # Track start time
        start_time = timezone.now()
        
        # Generate factoids
        factoids = generator.generate_insights(
            council_data=council_data,
            limit=limit,
            style=style
        )
        
        # Calculate processing time
        end_time = timezone.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Determine factoid source
        has_ai_factoids = any(f.get('insight_type') not in ['basic', 'system'] for f in factoids)
        factoid_source = 'openai_api' if has_ai_factoids else 'fallback'
        
        response_data = {
            'success': True,
            'council': council_slug,
            'council_name': council.name,
            'request_params': {
                'limit': limit,
                'style': style,
                'force_refresh': force_refresh
            },
            'council_data_summary': {
                'keys': list(council_data.keys()),
                'financial_metrics': list(council_data.get('financial_time_series', {}).keys()),
                'has_population': bool(council_data.get('population_data', {}).get('latest')),
                'data_quality': 'good' if council_data.get('financial_time_series') else 'limited'
            },
            'ai_prompt': ai_prompt,
            'ai_prompt_length': len(ai_prompt),
            'factoids': factoids,
            'factoid_count': len(factoids),
            'factoid_source': factoid_source,
            'processing_time_seconds': processing_time,
            'generated_at': timezone.now().isoformat(),
            'openai_available': generator.client is not None
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"AI generation test failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def clear_factoid_cache(request):
    """
    Clear factoid cache for specific council or all councils.
    """
    try:
        data = json.loads(request.body)
        council_slug = data.get('council_slug')
        clear_all = data.get('clear_all', False)
        
        cleared_keys = []
        
        if clear_all:
            # Clear all factoid caches (this is a simplified approach)
            councils = Council.objects.all()
            for council in councils:
                cache_key = f"ai_factoids:{council.slug}"
                data_key = f"ai_council_data:{council.slug}"
                if cache.delete(cache_key):
                    cleared_keys.append(cache_key)
                if cache.delete(data_key):
                    cleared_keys.append(data_key)
        else:
            # Clear specific council cache
            if council_slug:
                cache_key = f"ai_factoids:{council_slug}"
                data_key = f"ai_council_data:{council_slug}"
                if cache.delete(cache_key):
                    cleared_keys.append(cache_key)
                if cache.delete(data_key):
                    cleared_keys.append(data_key)
        
        return JsonResponse({
            'success': True,
            'cleared_keys': cleared_keys,
            'count': len(cleared_keys),
            'cleared_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def council_financial_data_viewer(request, council_slug):
    """
    Detailed viewer for council financial data over time.
    
    Shows the raw financial time series data that gets formatted
    for AI analysis.
    """
    council = get_object_or_404(Council, slug=council_slug)
    
    # Get raw financial data
    gatherer = CouncilDataGatherer()
    financial_data = gatherer._get_financial_time_series(council)
    
    # Format for display
    formatted_data = {}
    for metric, metric_info in financial_data.items():
        if metric_info and 'years' in metric_info:
            years_data = metric_info['years']
            if years_data:
                # Convert years data to lists for easier template access
                years_list = []
                values_list = []
                for year in sorted(years_data.keys()):
                    years_list.append(year)
                    values_list.append(years_data[year])
                
                formatted_data[metric] = {
                    'field_name': metric_info.get('field_name', metric),
                    'years': years_list,
                    'values': values_list,
                    'year_count': len(years_data),
                    'latest_year': years_list[-1] if years_list else None,
                    'latest_value': values_list[-1] if values_list else None
                }
    
    context = {
        'council': council,
        'financial_data': formatted_data,
        'raw_financial_data': financial_data,
        'metrics_count': len(formatted_data),
        'page_title': f'Financial Data - {council.name}'
    }
    
    return render(request, 'council_finance/ai_factoid_management/financial_data_viewer.html', context)


@staff_member_required
def ai_configuration(request):
    """
    Configuration interface for AI factoid system settings.
    
    Allows adjusting default parameters, cache settings, etc.
    """
    from django.conf import settings
    
    # Get current configuration
    current_config = {
        'openai_model': 'gpt-4',
        'default_factoid_limit': 3,
        'cache_timeout': 21600,  # 6 hours
        'rate_limit': '10/hour',
        'temperature': 0.7,
        'max_tokens': 500
    }
    
    # Get REST framework throttling settings
    rest_settings = getattr(settings, 'REST_FRAMEWORK', {})
    throttle_rates = rest_settings.get('DEFAULT_THROTTLE_RATES', {})
    
    context = {
        'current_config': current_config,
        'throttle_rates': throttle_rates,
        'cache_backend': str(cache.__class__.__name__),
        'page_title': 'AI Configuration'
    }
    
    return render(request, 'council_finance/ai_factoid_management/configuration.html', context)