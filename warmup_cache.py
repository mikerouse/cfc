"""
Cache warmup function for AI factoids.
Temporary file to add functionality - should be moved to appropriate views file.
"""

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils import timezone
import json
import logging

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer

logger = logging.getLogger(__name__)


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