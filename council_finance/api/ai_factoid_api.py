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
from council_finance.utils.email_alerts import send_error_alert
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import Throttled

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer

logger = logging.getLogger(__name__)

# Track quota notifications to avoid spam
_quota_notification_cache_key = 'openai_quota_notification_sent'
_quota_notification_cooldown = 3600  # 1 hour cooldown between notifications


def notify_quota_exceeded(council, error, attempt_number):
    """
    Send email notification to admins when OpenAI quota is exceeded.
    Uses cache to prevent spam - only sends one email per hour.
    """
    # Check if we've already sent a notification recently
    if cache.get(_quota_notification_cache_key):
        logger.info("Quota notification already sent recently, skipping email")
        return
        
    try:
        # Create a custom exception for the quota error
        quota_exception = Exception(f"OpenAI Quota Exceeded: {str(error)}")
        
        # Add context for the error alert
        context = {
            'alert_type': 'OpenAI Quota Exceeded',
            'council': f"{council.name} ({council.slug})",
            'attempt': f"{attempt_number} of 3",
            'error_details': str(error),
            'impact': 'AI factoid generation is failing for all councils',
            'current_behavior': 'System is serving cached AI factoids where available',
            'user_impact': 'Users without cached factoids see "being generated" message',
            'suggested_action': '''
To resolve OpenAI quota exceeded error:

1. Check OpenAI billing and usage:
   https://platform.openai.com/account/billing
   
2. Options to resolve:
   - Increase quota limits in OpenAI account
   - Wait for billing cycle to reset
   - Add payment method if needed
   
3. Monitor logs for continued failures

Note: Cached factoids will continue to be served for up to 30 days.
The system attempted {attempt_number} retries before giving up.
'''.strip(),
            'priority': 'HIGH',
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Send using the existing error alert system
        success = send_error_alert(quota_exception, request=None, context=context)
        
        if success:
            logger.info(f"Sent OpenAI quota exceeded notification via Brevo")
            # Set cache to prevent spam
            cache.set(_quota_notification_cache_key, True, _quota_notification_cooldown)
        else:
            logger.warning("Failed to send quota notification - check email configuration")
            
    except Exception as e:
        logger.error(f"Failed to send quota exceeded notification: {e}")


class AIFactoidRateThrottle(UserRateThrottle):
    """
    Custom throttle for AI factoid requests.
    
    Limits API calls to prevent excessive OpenAI usage costs.
    Rate: 5 requests per hour per council (reduced for efficiency).
    """
    scope = 'ai_factoids'
    rate = '5/hour'
    
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
        
        # Enhanced caching strategy - longer cache, fallback on rate limit
        cache_key = f"ai_factoids:{council_slug}"
        cache_key_stale = f"ai_factoids_stale:{council_slug}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            logger.info(f"✅ Serving cached AI factoids for {council.name}")
            cached_response['cache_status'] = 'cached'
            cached_response['served_at'] = timezone.now().isoformat()
            return Response(cached_response, status=status.HTTP_200_OK)
        
        # Check if we're rate limited and have stale cache
        stale_cached_response = cache.get(cache_key_stale)
        
        # Check rate limit manually before attempting AI generation
        throttle = AIFactoidRateThrottle()
        
        # Create a mock view object for throttle checking
        class MockView:
            def __init__(self, council_slug):
                self.kwargs = {'council_slug': council_slug}
        
        mock_view = MockView(council_slug)
        
        if not throttle.allow_request(request, mock_view):
            # Rate limited - fallback to stale cache
            if stale_cached_response:
                logger.info(f"⏱️ Rate limited for {council.name} - serving stale cached AI factoids")
                stale_cached_response['cache_status'] = 'rate_limited_fallback'
                stale_cached_response['served_at'] = timezone.now().isoformat()
                stale_cached_response['fallback_reason'] = 'Rate limit exceeded - serving cached data'
                return Response(stale_cached_response, status=status.HTTP_200_OK)
            
            # No stale cache available during rate limit
            logger.warning(f"⏱️ Rate limited for {council.name} with no cached fallback")
            return Response({
                'success': True,
                'no_factoids': True,
                'rate_limited': True,
                'message': f'AI analysis for {council.name} is temporarily rate limited. Fresh insights will be available in about an hour.',
                'council': council_slug,
                'factoids': [],  # Empty array - no factoids to show
                'cache_status': 'rate_limited',
                'retry_after': throttle.wait()
            }, status=status.HTTP_200_OK)
        
        # Try to generate fresh AI factoids with up to 3 retry attempts
        factoids = None
        generation_success = False
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries and not generation_success:
            try:
                retry_count += 1
                logger.info(f"🤖 AI factoid generation attempt {retry_count}/{max_retries} for {council.name}")
                
                # Gather comprehensive council data
                data_gatherer = CouncilDataGatherer()
                council_data = data_gatherer.gather_council_data(council)
                
                # Generate AI insights - increased to 10 factoids as requested
                ai_generator = AIFactoidGenerator()
                factoids = ai_generator.generate_insights(
                    council_data=council_data,
                    limit=10,
                    style='news_ticker'
                )
                
                # Check if we got real AI factoids (not fallback)
                if factoids and not all(f.get('insight_type') in ['basic', 'system'] for f in factoids):
                    generation_success = True
                    logger.info(f"✅ AI generation successful on attempt {retry_count} for {council.name}")
                else:
                    logger.warning(f"⚠️ Attempt {retry_count} returned fallback factoids for {council.name}")
                    
            except Exception as ai_error:
                logger.warning(f"⚠️ AI generation attempt {retry_count} failed for {council.name}: {ai_error}")
                
                # Check if this is a quota error and send notification
                if 'insufficient_quota' in str(ai_error) or '429' in str(ai_error):
                    notify_quota_exceeded(council, ai_error, retry_count)
                
                if retry_count < max_retries:
                    # Wait a bit before retrying
                    import time
                    time.sleep(1)
        
        # If AI generation failed after retries, use cached data
        if not generation_success:
            if stale_cached_response:
                logger.info(f"🔄 Serving cached AI factoids for {council.name} after {retry_count} failed attempts")
                stale_cached_response['cache_status'] = 'cached_after_retry_failure'
                stale_cached_response['served_at'] = timezone.now().isoformat()
                stale_cached_response['retry_attempts'] = retry_count
                return Response(stale_cached_response, status=status.HTTP_200_OK)
            
            # No cache available - return message instead of poor quality factoids
            logger.warning(f"❌ No AI factoids available for {council.name} after {retry_count} attempts")
            return Response({
                'success': True,
                'no_factoids': True,
                'message': f'AI analysis for {council.name} is being generated. Please check back in a few minutes.',
                'council': council_slug,
                'factoids': [],  # Empty array instead of fallback factoids
                'cache_status': 'none_available',
                'retry_attempts': retry_count
            }, status=status.HTTP_200_OK)
        
        # At this point we have successful AI-generated factoids
        # No need to check for fallback factoids anymore
        
        # Build response for successful AI generation
        response_data = {
            'success': True,
            'council': council_slug,
            'factoids': factoids,
            'generated_at': timezone.now().isoformat(),
            'data_period': _get_data_period(council_data),
            'ai_model': ai_generator.model,
            'cache_status': 'fresh',
            'factoid_count': len(factoids)
        }
        
        # Enhanced caching strategy:
        # - Primary cache: 7 days (604800 seconds) - only invalidated when data changes
        # - Stale cache: 30 days (2592000 seconds) - for fallback when AI service unavailable
        cache.set(cache_key, response_data, 604800)  # 7 days primary cache
        cache.set(cache_key_stale, response_data, 2592000)  # 30 days stale cache for fallback
        
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