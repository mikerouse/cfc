"""
AI Factoids API

Provides REST endpoints for AI-generated council factoids.
Replaces counter-based factoid API with single council-wide insights.
"""

import logging
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer

logger = logging.getLogger(__name__)


class AIFactoidRateThrottle(UserRateThrottle):
    """
    Custom throttle for AI factoid requests.
    
    Limits API calls to prevent excessive OpenAI usage costs.
    Rate: 25 requests per hour per council.
    """
    scope = 'ai_factoids'
    rate = '25/hour'
    
    def get_cache_key(self, request, view):
        """Generate cache key based on council slug rather than user."""
        council_slug = view.kwargs.get('council_slug', 'unknown')
        ident = f"ai_factoids_{council_slug}"
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AIFactoidRateThrottle])
def ai_council_factoids(request, council_slug):
    """
    Generate AI factoids for a specific council.
    
    Returns AI-generated insights based on comprehensive financial analysis.
    Replaces counter-specific factoids with single council-wide insights.
    
    URL: GET /api/factoids/ai/{council_slug}/
    
    Response:
    {
        "success": true,
        "council": "worcestershire", 
        "factoids": [
            {
                "text": "Interest payments peaked in 2023 at £3.8M, up 58% from 2019",
                "insight_type": "trend",
                "confidence": 0.95
            }
        ],
        "generated_at": "2025-07-31T12:30:00Z",
        "ai_model": "gpt-4",
        "cache_status": "fresh"
    }
    """
    try:
        # Get council or return 404
        council = get_object_or_404(Council, slug=council_slug)
        
        # Check cache first (6-hour cache as per spec)
        cache_key = f"ai_factoids:{council_slug}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            logger.info(f"✅ Serving cached AI factoids for {council.name}")
            cached_response['cache_status'] = 'cached'
            cached_response['served_at'] = timezone.now().isoformat()
            return Response(cached_response, status=status.HTTP_200_OK)
        
        # Generate fresh AI factoids
        logger.info(f"🤖 Generating fresh AI factoids for {council.name}")
        
        # Gather comprehensive council data
        data_gatherer = CouncilDataGatherer()
        council_data = data_gatherer.gather_council_data(council)
        
        # Generate AI insights
        ai_generator = AIFactoidGenerator()
        factoids = ai_generator.generate_insights(
            council_data=council_data,
            limit=3,
            style='news_ticker'
        )
        
        # Check if these are fallback factoids
        are_fallback_factoids = all(
            f.get('insight_type') in ['basic', 'system'] for f in factoids
        )
        
        if are_fallback_factoids:
            # Don't cache fallback factoids - return error response instead
            logger.warning(f"❌ AI generation failed for {council.name}, not caching fallback factoids")
            return Response({
                'success': False,
                'error': 'AI analysis temporarily unavailable',
                'council': council_slug,
                'factoids': [{
                    'text': f"AI analysis temporarily unavailable for {council.name}",
                    'insight_type': 'error',
                    'confidence': 1.0,
                    'show_retry': True
                }],
                'cache_status': 'not_cached'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Build response for successful AI generation
        response_data = {
            'success': True,
            'council': council_slug,
            'factoids': factoids,
            'generated_at': timezone.now().isoformat(),
            'data_period': _get_data_period(council_data),
            'ai_model': 'gpt-4',
            'cache_status': 'fresh',
            'factoid_count': len(factoids)
        }
        
        # Cache successful AI responses for 6 hours (21600 seconds)
        cache.set(cache_key, response_data, 21600)
        
        logger.info(f"✅ Generated {len(factoids)} AI factoids for {council.name}")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Council.DoesNotExist:
        logger.warning(f"❌ Council not found: {council_slug}")
        return Response({
            'success': False,
            'error': 'Council not found',
            'council': council_slug
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"❌ AI factoid generation failed for {council_slug}: {str(e)}")
        
        # Return error response with fallback
        return Response({
            'success': False,
            'error': 'AI factoid generation failed',
            'council': council_slug,
            'fallback_message': f"Financial insights for {council_slug} are being processed",
            'factoids': [{
                'text': f"Financial data for {council_slug} is being analysed",
                'insight_type': 'system',
                'confidence': 1.0
            }]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AIFactoidRateThrottle])
def ai_batch_factoids(request):
    """
    Generate AI factoids for multiple councils in batch.
    
    Useful for bulk operations and administrative tools.
    Limited to 5 councils per request to manage API costs.
    
    URL: POST /api/factoids/ai/batch/
    Body: {"councils": ["council-1", "council-2"]}
    
    Response:
    {
        "success": true,
        "results": {
            "council-1": { factoids... },
            "council-2": { factoids... }
        },
        "processed": 2,
        "generated_at": "2025-07-31T12:30:00Z"
    }
    """
    try:
        council_slugs = request.data.get('councils', [])
        
        if not council_slugs or len(council_slugs) > 5:
            return Response({
                'success': False,
                'error': 'Invalid request - provide 1-5 council slugs'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {}
        processed_count = 0
        
        # Initialize generators once
        data_gatherer = CouncilDataGatherer()
        ai_generator = AIFactoidGenerator()
        
        for council_slug in council_slugs:
            try:
                council = Council.objects.get(slug=council_slug)
                
                # Gather data and generate factoids
                council_data = data_gatherer.gather_council_data(council)
                factoids = ai_generator.generate_insights(
                    council_data=council_data,
                    limit=3,
                    style='news_ticker'
                )
                
                results[council_slug] = {
                    'success': True,
                    'factoids': factoids,
                    'count': len(factoids)
                }
                processed_count += 1
                
            except Council.DoesNotExist:
                results[council_slug] = {
                    'success': False,
                    'error': 'Council not found'
                }
            except Exception as e:
                logger.error(f"Batch processing failed for {council_slug}: {e}")
                results[council_slug] = {
                    'success': False,
                    'error': 'Processing failed'
                }
        
        return Response({
            'success': True,
            'results': results,
            'processed': processed_count,
            'requested': len(council_slugs),
            'generated_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Batch AI factoid generation failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Batch processing failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def clear_ai_factoid_cache(request, council_slug):
    """
    Clear cached AI factoids for a council.
    
    Useful for forcing regeneration after data updates.
    Requires staff permissions.
    
    URL: DELETE /api/factoids/ai/{council_slug}/cache/
    """
    if not request.user.is_staff:
        return Response({
            'success': False,
            'error': 'Staff access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Clear cache
        cache_key = f"ai_factoids:{council_slug}"
        cache_was_cleared = cache.delete(cache_key)
        
        # Also clear data gathering cache
        data_cache_key = f"ai_council_data:{council_slug}"
        cache.delete(data_cache_key)
        
        logger.info(f"🗑️ Cleared AI factoid cache for {council.name}")
        
        return Response({
            'success': True,
            'council': council_slug,
            'cache_cleared': cache_was_cleared,
            'cleared_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to clear cache for {council_slug}: {str(e)}")
        return Response({
            'success': False,
            'error': 'Cache clearing failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def ai_factoid_status(request):
    """
    Get status of AI factoid system.
    
    Shows configuration, rate limits, and system health.
    Useful for monitoring and debugging.
    
    URL: GET /api/factoids/ai/status/
    """
    try:
        # Check OpenAI configuration
        ai_generator = AIFactoidGenerator()
        openai_available = ai_generator.client is not None
        
        # Get cache statistics (simplified)
        cache_info = {
            'backend': str(cache.__class__.__name__),
            'default_timeout': getattr(settings, 'CACHE_DEFAULT_TIMEOUT', 300),
        }
        
        # Rate limiting info
        rate_limit_info = {
            'rate': AIFactoidRateThrottle.rate,
            'scope': AIFactoidRateThrottle.scope,
        }
        
        status_data = {
            'success': True,
            'system_status': 'operational' if openai_available else 'limited',
            'openai_available': openai_available,
            'cache_info': cache_info,
            'rate_limiting': rate_limit_info,
            'features': {
                'ai_generation': openai_available,
                'fallback_factoids': True,
                'caching': True,
                'batch_processing': True
            },
            'checked_at': timezone.now().isoformat()
        }
        
        return Response(status_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"AI factoid status check failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Status check failed',
            'system_status': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_data_period(council_data):
    """
    Extract data period from council data for response metadata.
    
    Returns string indicating the time range of data used for analysis.
    """
    try:
        financial_data = council_data.get('financial_time_series', {})
        if not financial_data:
            return 'Limited data available'
        
        all_years = set()
        for metric_data in financial_data.values():
            if isinstance(metric_data, dict):
                all_years.update(metric_data.keys())
        
        if all_years:
            sorted_years = sorted(all_years)
            if len(sorted_years) >= 2:
                return f"{sorted_years[0]}-{sorted_years[-1]}"
            else:
                return sorted_years[0]
        
        return 'Data period unknown'
        
    except Exception:
        return 'Data period unknown'