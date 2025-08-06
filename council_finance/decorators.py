"""
Custom decorators for council_finance app.
Includes OSA compliance decorators for content restrictions.
"""
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


def comments_access_required(view_func):
    """
    Decorator to ensure users can access comments (OSA compliance).
    Blocks access for users under 18.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        
        # Check if user can access comments
        if not profile or not profile.can_access_comments:
            return JsonResponse({
                'success': False,
                'error': 'comment_access_restricted',
                'message': 'Comments are restricted for users under 18 in compliance with the Online Safety Act.',
                'details': {
                    'reason': 'age_restriction',
                    'user_age': profile.age() if profile and profile.date_of_birth else None,
                    'restriction_type': 'osa_compliance',
                }
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def feed_access_required(view_func):
    """
    Decorator to ensure users can access feed content (OSA compliance).
    Currently same as comments_access_required but separated for potential future differences.
    """
    @wraps(view_func)
    @login_required 
    def _wrapped_view(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        
        # Check if user can access feed content
        if not profile or not profile.can_access_comments:
            return JsonResponse({
                'success': False,
                'error': 'feed_access_restricted', 
                'message': 'Feed content is restricted for users under 18 in compliance with the Online Safety Act.',
                'details': {
                    'reason': 'age_restriction',
                    'user_age': profile.age() if profile and profile.date_of_birth else None,
                    'restriction_type': 'osa_compliance',
                }
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view