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
from council_finance.services.sitewide_factoid_generator import SitewideFactoidGenerator

logger = logging.getLogger(__name__)


@staff_member_required
def ai_factoid_management_dashboard(request):
    """
    Main dashboard for AI factoid management.
    
    Shows overview of councils, recent AI calls, and configuration options.
    """
    from datetime import datetime, timedelta
    
    # Get councils with recent factoid activity
    councils = Council.objects.all().order_by('name')[:50]
    
    # Get system status
    generator = AIFactoidGenerator()
    openai_available = generator.client is not None
    model_info = generator.get_model_info()
    
    # Calculate cache statistics
    cached_councils = 0
    stale_cached_councils = 0
    total_cached_factoids = 0
    
    for council in Council.objects.all()[:100]:  # Sample check
        cache_key = f"ai_factoids:{council.slug}"
        cache_key_stale = f"ai_factoids_stale:{council.slug}"
        
        if cache.get(cache_key):
            cached_councils += 1
            cached_data = cache.get(cache_key)
            if isinstance(cached_data, dict):
                total_cached_factoids += cached_data.get('factoid_count', 0)
        
        if cache.get(cache_key_stale):
            stale_cached_councils += 1
    
    # Estimate costs (rough approximation)
    estimated_tokens_per_request = 800  # Average tokens per API call
    requests_per_council = 1  # Initial request
    total_potential_requests = Council.objects.count() * requests_per_council
    cost_per_1k_tokens = model_info['cost_per_1k_tokens']
    estimated_total_cost = (total_potential_requests * estimated_tokens_per_request / 1000) * cost_per_1k_tokens
    
    context = {
        'councils': councils,
        'openai_available': openai_available,
        'total_councils': Council.objects.count(),
        'page_title': 'AI Factoid Management',
        'dashboard_stats': {
            'councils_total': Council.objects.count(),
            'openai_configured': openai_available,
            'cache_backend': str(cache.__class__.__name__),
            'cached_councils': cached_councils,
            'stale_cached_councils': stale_cached_councils,
            'total_cached_factoids': total_cached_factoids,
            'cache_hit_rate': round((cached_councils / Council.objects.count() * 100), 1) if Council.objects.count() > 0 else 0,
        },
        'ai_model_info': model_info,
        'cost_estimates': {
            'per_request': round(estimated_tokens_per_request / 1000 * cost_per_1k_tokens, 4),
            'per_council': round(estimated_tokens_per_request / 1000 * cost_per_1k_tokens * requests_per_council, 4),
            'total_potential': round(estimated_total_cost, 2),
            'monthly_estimate': round(estimated_total_cost * 30 / 7, 2),  # Assuming weekly cache refresh
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
    
    # Check cache status with more detail
    cache_key = f"ai_factoids:{council_slug}"
    cache_key_stale = f"ai_factoids_stale:{council_slug}"
    cached_factoids = cache.get(cache_key)
    stale_cached_factoids = cache.get(cache_key_stale)
    
    cache_status = {
        'primary_cache': 'cached' if cached_factoids else 'not_cached',
        'stale_cache': 'cached' if stale_cached_factoids else 'not_cached',
        'primary_cache_key': cache_key,
        'stale_cache_key': cache_key_stale,
        'primary_factoids': cached_factoids,
        'stale_factoids': stale_cached_factoids
    }
    
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
    
    # Get AI generator for current model info
    generator = AIFactoidGenerator()
    model_info = generator.get_model_info()
    
    # Get available models for selection
    available_models = [
        {
            'name': 'gpt-4o-mini',
            'display_name': 'GPT-4o Mini',
            'cost_per_1k': 0.000150,
            'description': 'Most cost-effective option, excellent for factoid generation',
            'recommended': True
        },
        {
            'name': 'gpt-4o',
            'display_name': 'GPT-4o',
            'cost_per_1k': 0.0025,
            'description': 'Latest high-performance model with excellent reasoning'
        },
        {
            'name': 'gpt-4-turbo',
            'display_name': 'GPT-4 Turbo',
            'cost_per_1k': 0.01,
            'description': 'Fast, high-capability model with large context window'
        },
        {
            'name': 'gpt-4',
            'display_name': 'GPT-4',
            'cost_per_1k': 0.03,
            'description': 'Original GPT-4 model with strong reasoning capabilities'
        },
        {
            'name': 'gpt-3.5-turbo',
            'display_name': 'GPT-3.5 Turbo',
            'cost_per_1k': 0.0015,
            'description': 'Fast and economical model for simpler tasks'
        }
    ]
    
    # Get current configuration with dynamic model info
    current_config = {
        'openai_model': model_info['name'],
        'openai_model_display': model_info['display_name'],
        'openai_model_cost': model_info['cost_per_1k_tokens'],
        'openai_model_description': model_info['description'],
        'default_factoid_limit': 3,
        'cache_timeout': 21600,  # 6 hours
        'rate_limit': '5/hour',  # Updated to match actual rate limit
        'temperature': generator.temperature,
        'max_tokens': generator.max_tokens
    }
    
    # Get REST framework throttling settings
    rest_settings = getattr(settings, 'REST_FRAMEWORK', {})
    throttle_rates = rest_settings.get('DEFAULT_THROTTLE_RATES', {})
    
    # Check OpenAI API key status
    openai_configured = generator.client is not None
    
    context = {
        'current_config': current_config,
        'available_models': available_models,
        'current_model_info': model_info,
        'throttle_rates': throttle_rates,
        'cache_backend': str(cache.__class__.__name__),
        'openai_configured': openai_configured,
        'page_title': 'AI Configuration'
    }
    
    return render(request, 'council_finance/ai_factoid_management/configuration.html', context)


@staff_member_required
def sitewide_factoid_inspector(request):
    """
    Inspector for site-wide factoids system.
    
    Shows the cross-council data gathered, AI prompts sent, and generated factoids
    for the homepage site-wide factoid display.
    """
    generator = SitewideFactoidGenerator()
    
    # Gather the same cross-council data that would be sent to AI
    cross_council_data = generator._gather_cross_council_data()
    
    # Build the actual prompt that would be sent to OpenAI
    sample_prompt = None
    if cross_council_data and cross_council_data.get('total_councils', 0) >= 2:
        sample_prompt = generator._build_sitewide_analysis_prompt(cross_council_data, limit=3)
    
    # Get current cached factoids
    cache_key = "sitewide_factoids_3"
    cached_factoids = cache.get(cache_key)
    cache_status = 'cached' if cached_factoids else 'not_cached'
    
    # Debug logging
    logger.info(f"[SITEWIDE_INSPECTOR] Cross-council data keys: {list(cross_council_data.keys()) if cross_council_data else 'None'}")
    if cross_council_data:
        logger.info(f"[SITEWIDE_INSPECTOR] Total councils: {cross_council_data.get('total_councils', 0)}")
        logger.info(f"[SITEWIDE_INSPECTOR] Fields data: {len(cross_council_data.get('fields_data', {}))}")
    
    context = {
        'cross_council_data': cross_council_data,
        'ai_prompt': sample_prompt,
        'cache_status': cache_status,
        'cached_factoids': cached_factoids,
        'data_keys': list(cross_council_data.keys()) if cross_council_data else [],
        'total_councils': cross_council_data.get('total_councils', 0) if cross_council_data else 0,
        'analysis_year': cross_council_data.get('year', 'Unknown') if cross_council_data else 'Unknown',
        'comparison_fields': generator.comparison_fields,
        'page_title': 'Site-wide AI Factoids Inspector'
    }
    
    return render(request, 'council_finance/ai_factoid_management/sitewide_inspector.html', context)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def test_sitewide_generation(request):
    """
    Test site-wide AI factoid generation with custom parameters.
    
    Allows testing different numbers of factoids and viewing
    the complete request/response cycle for site-wide factoids.
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        limit = int(data.get('limit', 3))
        force_refresh = data.get('force_refresh', False)
        
        # Clear cache if requested
        if force_refresh:
            cache_key = f"sitewide_factoids_{limit}"
            cache.delete(cache_key)
        
        # Gather cross-council data
        generator = SitewideFactoidGenerator()
        cross_council_data = generator._gather_cross_council_data()
        
        # Generate AI prompt
        ai_prompt = None
        if cross_council_data and cross_council_data.get('total_councils', 0) >= 2:
            ai_prompt = generator._build_sitewide_analysis_prompt(cross_council_data, limit=limit)
        
        # Track start time
        start_time = timezone.now()
        
        # Generate factoids
        factoids = generator.generate_sitewide_factoids(limit=limit)
        
        # Calculate processing time
        end_time = timezone.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Determine factoid source
        has_ai_factoids = any(f.get('insight_type') not in ['basic', 'system'] for f in factoids)
        factoid_source = 'openai_api' if has_ai_factoids else 'fallback'
        
        response_data = {
            'success': True,
            'request_params': {
                'limit': limit,
                'force_refresh': force_refresh
            },
            'cross_council_data_summary': {
                'total_councils': cross_council_data.get('total_councils', 0) if cross_council_data else 0,
                'analysis_year': cross_council_data.get('year', 'Unknown') if cross_council_data else 'Unknown',
                'fields_analysed': list(cross_council_data.get('fields_data', {}).keys()) if cross_council_data else [],
                'has_type_comparisons': bool(cross_council_data.get('type_comparisons')) if cross_council_data else False,
                'has_nation_comparisons': bool(cross_council_data.get('nation_comparisons')) if cross_council_data else False,
                'data_quality': 'good' if cross_council_data and cross_council_data.get('total_councils', 0) >= 10 else 'limited'
            },
            'ai_prompt': ai_prompt,
            'ai_prompt_length': len(ai_prompt) if ai_prompt else 0,
            'factoids': factoids,
            'factoid_count': len(factoids),
            'factoid_source': factoid_source,
            'processing_time_seconds': processing_time,
            'generated_at': timezone.now().isoformat(),
            'openai_available': generator.client is not None
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Site-wide AI generation test failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def clear_sitewide_cache(request):
    """
    Clear site-wide factoid cache.
    """
    try:
        data = json.loads(request.body)
        
        cleared_keys = []
        
        # Clear site-wide factoid caches for different limits
        for limit in [1, 2, 3, 4, 5]:
            cache_key = f"sitewide_factoids_{limit}"
            if cache.delete(cache_key):
                cleared_keys.append(cache_key)
        
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
@require_http_methods(["POST"])
@csrf_exempt
def warmup_council_cache(request):
    """
    Warmup AI factoid cache for a specific council.
    
    Forces fresh generation and caches the result.
    Useful for testing and ensuring cached data is available.
    """
    try:
        data = json.loads(request.body)
        council_slug = data.get('council_slug')
        
        if not council_slug:
            return JsonResponse({
                'success': False,
                'error': 'council_slug is required'
            }, status=400)
        
        council = get_object_or_404(Council, slug=council_slug)
        
        # Clear existing cache
        cache_key = f"ai_factoids:{council_slug}"
        cache_key_stale = f"ai_factoids_stale:{council_slug}"
        cache_key_data = f"ai_council_data:{council_slug}"
        
        cache.delete(cache_key)
        cache.delete(cache_key_stale)
        cache.delete(cache_key_data)
        
        # Force fresh generation
        gatherer = CouncilDataGatherer()
        council_data = gatherer.gather_council_data(council)
        
        generator = AIFactoidGenerator()
        start_time = timezone.now()
        
        try:
            factoids = generator.generate_insights(
                council_data=council_data,
                limit=10,
                style='news_ticker'
            )
            
            end_time = timezone.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Cache the results
            response_data = {
                'success': True,
                'council': council_slug,
                'factoids': factoids,
                'generated_at': timezone.now().isoformat(),
                'ai_model': generator.model,
                'cache_status': 'fresh',
                'factoid_count': len(factoids)
            }
            
            # Cache with same strategy as main API
            cache.set(cache_key, response_data, 604800)  # 7 days
            cache.set(cache_key_stale, response_data, 2592000)  # 30 days
            
            return JsonResponse({
                'success': True,
                'council': council_slug,
                'council_name': council.name,
                'factoids_generated': len(factoids),
                'processing_time_seconds': processing_time,
                'ai_model': generator.model,
                'cache_keys_set': [cache_key, cache_key_stale],
                'warmed_at': timezone.now().isoformat()
            })
            
        except Exception as ai_error:
            return JsonResponse({
                'success': False,
                'council': council_slug,
                'error': 'AI generation failed during warmup',
                'ai_error': str(ai_error),
                'error_type': type(ai_error).__name__
            }, status=500)
        
    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Cache warmup failed',
            'details': str(e)
        }, status=500)