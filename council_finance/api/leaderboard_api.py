"""
Leaderboard API Endpoints
Provides REST API access to leaderboard data
"""

import logging
from typing import Optional

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.utils import timezone
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from council_finance.services.leaderboard_service import LeaderboardService

logger = logging.getLogger(__name__)


class LeaderboardRateThrottle(AnonRateThrottle):
    """
    Custom throttle for leaderboard API requests.
    Rate: 60 requests per hour for anonymous users.
    """
    scope = 'leaderboard_api'
    rate = '60/hour'


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([LeaderboardRateThrottle])
@cache_page(300)  # Cache for 5 minutes
def get_leaderboard(request, category: Optional[str] = None):
    """
    Get leaderboard data for a specific category.
    
    Query Parameters:
        category (str): Leaderboard category (optional in URL)
        year (str): Financial year (optional)
        per_capita (bool): Calculate per capita values (optional)
        limit (int): Number of entries to return (max 100, default 50)
        
    Returns:
        JSON response with leaderboard data
    """
    try:
        # Get parameters
        category = category or request.GET.get('category', 'contributors')
        year = request.GET.get('year')
        per_capita = request.GET.get('per_capita', 'false').lower() == 'true'
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 entries
        
        logger.info(f"🔍 Fetching leaderboard: {category}, year={year}, per_capita={per_capita}, limit={limit}")
        
        # Get leaderboard data
        service = LeaderboardService()
        leaderboard_data = service.get_leaderboard(category, year, per_capita, limit)
        
        if not leaderboard_data:
            return Response({
                'success': False,
                'error': f'No data available for category: {category}',
                'category': category,
                'available_categories': list(service.CATEGORIES.keys())
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Format response
        response_data = {
            'success': True,
            'data': leaderboard_data.to_dict(),
            'meta': {
                'cached': True,
                'cache_expires_in_seconds': 300,
                'generated_at': timezone.now().isoformat(),
                'api_version': '1.0'
            }
        }
        
        logger.info(f"✅ Returned leaderboard with {len(leaderboard_data.entries)} entries")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f"❌ Invalid parameter in leaderboard request: {e}")
        return Response({
            'success': False,
            'error': 'Invalid parameters provided',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"❌ Leaderboard API error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'category': category
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([LeaderboardRateThrottle])
@cache_page(600)  # Cache for 10 minutes
def get_council_rankings(request, council_slug: str):
    """
    Get all rankings for a specific council across all categories.
    
    Parameters:
        council_slug (str): Council slug
        
    Query Parameters:
        year (str): Financial year (optional)
        
    Returns:
        JSON response with council rankings across all categories
    """
    try:
        year = request.GET.get('year')
        
        logger.info(f"🔍 Fetching rankings for council: {council_slug}, year={year}")
        
        # Get council rankings
        service = LeaderboardService()
        rankings = service.get_council_rankings(council_slug, year)
        
        if not rankings:
            return Response({
                'success': False,
                'error': f'No rankings found for council: {council_slug}',
                'council_slug': council_slug
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Format response
        response_data = {
            'success': True,
            'council_slug': council_slug,
            'year': year,
            'rankings': rankings,
            'summary': {
                'total_categories': len(rankings),
                'best_rank': min(r['rank'] for r in rankings.values()) if rankings else None,
                'average_percentile': sum(r['percentile'] for r in rankings.values() if r['percentile']) / len(rankings) if rankings else None
            },
            'meta': {
                'generated_at': timezone.now().isoformat(),
                'cache_expires_in_seconds': 600
            }
        }
        
        logger.info(f"✅ Returned rankings for {council_slug}: {len(rankings)} categories")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Council rankings API error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'council_slug': council_slug
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_categories(request):
    """
    Get available leaderboard categories.
    
    Returns:
        JSON response with available categories and their metadata
    """
    try:
        service = LeaderboardService()
        
        # Format categories for API response
        categories_data = {}
        for key, info in service.CATEGORIES.items():
            categories_data[key] = {
                'name': info['name'],
                'description': info['description'],
                'icon': info.get('icon'),
                'type': info.get('type', 'financial'),
                'supports_per_capita': 'field_slug' in info,
                'field_slug': info.get('field_slug'),
                'reverse_order': info.get('reverse', True)
            }
        
        response_data = {
            'success': True,
            'categories': categories_data,
            'meta': {
                'total_categories': len(categories_data),
                'generated_at': timezone.now().isoformat()
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Categories API error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Legacy Django view support
@require_http_methods(["GET"])
@cache_page(300)
def leaderboard_view(request, category: Optional[str] = None):
    """
    Django view wrapper for leaderboard API.
    Provides backwards compatibility.
    """
    try:
        category = category or request.GET.get('category', 'contributors')
        year = request.GET.get('year')
        per_capita = request.GET.get('per_capita', 'false').lower() == 'true'
        limit = min(int(request.GET.get('limit', 50)), 100)
        
        service = LeaderboardService()
        leaderboard_data = service.get_leaderboard(category, year, per_capita, limit)
        
        if not leaderboard_data:
            return JsonResponse({
                'success': False,
                'error': f'No data available for category: {category}'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'data': leaderboard_data.to_dict(),
            'generated_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Leaderboard Django view error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)