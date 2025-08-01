"""
Site-wide Factoids API

Provides REST endpoints for AI-generated cross-council factoids for homepage display.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from council_finance.services.sitewide_factoid_generator import SitewideFactoidGenerator

logger = logging.getLogger(__name__)


class SitewideFactoidRateThrottle(AnonRateThrottle):
    """
    Custom throttle for site-wide factoid requests.
    
    Limits API calls to prevent excessive usage.
    Rate: 20 requests per hour for anonymous users.
    """
    scope = 'sitewide_factoids'
    rate = '20/hour'


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([SitewideFactoidRateThrottle])
@cache_page(1800)  # Cache for 30 minutes
def get_sitewide_factoids(request):
    """
    Get AI-generated cross-council factoids for homepage display.
    
    Query Parameters:
        limit (int): Number of factoids to return (default: 3, max: 5)
        
    Returns:
        JSON response with factoids array containing:
        - text: Factoid text with council links
        - councils_mentioned: Array of council slugs
        - field: Financial field being compared
        - insight_type: Type of comparison/insight
        - generated_at: Timestamp
        - data_year: Year of data used
    """
    try:
        # Parse limit parameter
        limit = min(int(request.GET.get('limit', 3)), 5)  # Max 5 factoids
        
        logger.info(f"🔍 Generating {limit} site-wide factoids for homepage")
        
        # Generate factoids using AI service
        generator = SitewideFactoidGenerator()
        factoids = generator.generate_sitewide_factoids(limit=limit)
        
        if not factoids:
            logger.warning("❌ No site-wide factoids generated")
            return Response({
                'success': False,
                'error': 'No factoids available at this time',
                'factoids': [],
                'count': 0
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Format response
        response_data = {
            'success': True,
            'count': len(factoids),
            'factoids': factoids,
            'generated_at': timezone.now().isoformat(),
            'cache_info': {
                'cached': True,
                'expires_in_minutes': 30
            }
        }
        
        logger.info(f"✅ Returned {len(factoids)} site-wide factoids successfully")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f"❌ Invalid parameter in site-wide factoids request: {e}")
        return Response({
            'success': False,
            'error': 'Invalid parameters provided',
            'factoids': [],
            'count': 0
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"❌ Site-wide factoids API error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error generating factoids',
            'factoids': [],
            'count': 0
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_sitewide_factoids_health(request):
    """
    Health check endpoint for site-wide factoids system.
    
    Returns:
        JSON response with system status and availability
    """
    try:
        generator = SitewideFactoidGenerator()
        
        # Quick health check - try to generate one factoid
        test_factoids = generator.generate_sitewide_factoids(limit=1)
        
        ai_available = bool(generator.client)
        
        health_data = {
            'status': 'healthy' if test_factoids else 'degraded',
            'ai_service_available': ai_available,
            'cache_working': bool(cache.get('test_key') == cache.set('test_key', 'test', 1)),
            'test_generation_successful': len(test_factoids) > 0,
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(health_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Site-wide factoids health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# Legacy Django view support (for backwards compatibility)
@require_http_methods(["GET"])
@csrf_exempt  
@cache_page(1800)
def sitewide_factoids_view(request):
    """
    Django view wrapper for site-wide factoids API.
    
    Provides backwards compatibility with Django view patterns.
    """
    try:
        limit = min(int(request.GET.get('limit', 3)), 5)
        
        generator = SitewideFactoidGenerator()
        factoids = generator.generate_sitewide_factoids(limit=limit)
        
        return JsonResponse({
            'success': True,
            'count': len(factoids),
            'factoids': factoids,
            'generated_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Site-wide factoids Django view error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'factoids': [],
            'count': 0
        }, status=500)