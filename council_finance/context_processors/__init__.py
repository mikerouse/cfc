"""
Context Processors for Council Finance Counters

This module provides template context processors that make commonly used
data available to all templates throughout the application.
"""

from typing import Dict, Any
from django.http import HttpRequest
import os
from django.conf import settings


def compare_count(request: HttpRequest) -> Dict[str, int]:
    """
    Expose the number of councils in the comparison basket.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Contains compare_count integer
    """
    return {"compare_count": len(request.session.get("compare_basket", []))}


def user_preferences(request: HttpRequest) -> Dict[str, Any]:
    """
    Provide complete user preferences context to all templates.
    
    This replaces the old font_family processor with a comprehensive
    system supporting fonts, accessibility, and theming.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Complete user preferences context
    """
    try:
        from ..user_preferences import get_user_preferences_context
        return get_user_preferences_context(request)
    except ImportError:
        # Fallback for development/migration scenarios
        return {
            'font_family': 'Cairo',
            'font_size_css': '16px',
            'google_fonts_url': 'https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap',
            'css_variables': {
                '--font-family-primary': "'Cairo', sans-serif",
                '--font-size-base': '16px',
                '--color-background': '#ffffff',
                '--color-text': '#0b0c0c',
                '--color-primary': '#1d70b8',
            },
            'accessibility_classes': 'font-size-medium theme-auto',
            'high_contrast_mode': False,
            'color_theme': 'auto',
        }


def debug_flag(request: HttpRequest) -> Dict[str, bool]:
    """
    Expose the DEBUG setting to templates.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Contains debug boolean flag
    """
    # Check both Django DEBUG setting and .env DEBUG flag
    debug_mode = settings.DEBUG
    env_debug = os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')
    
    return {"debug": debug_mode or env_debug}


def tutorial_context(request: HttpRequest) -> Dict[str, Dict]:
    """
    Provide tutorial configuration to all templates.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Tutorial configuration context
    """
    try:
        from ..tutorial_engine import TutorialEngine
        engine = TutorialEngine()
        
        # Determine which tutorials are relevant for this page
        page_path = request.path
        tutorials = {}
        
        # Check for specific tutorials based on page
        if page_path.startswith('/contribute'):
            tutorials['contribute'] = engine.get_tutorial_config('contribute')
        
        return {
            "tutorial_config": {
                "engine": engine,
                "debug_mode": engine.debug_mode or engine.force_debug_tutorials,
                "tutorials": tutorials,
                "current_page": page_path
            }
        }
    except ImportError:
        # Fallback if tutorial_engine doesn't exist yet
        return {"tutorial_config": {}}


def dev_cache_buster(request: HttpRequest) -> Dict[str, Any]:
    """
    Add cache busting for development.
    
    In development, this adds a timestamp to help with cache busting.
    In production, this should be replaced with actual versioning.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Contains cache_version and debug_mode
    """
    import time
    
    if settings.DEBUG:
        # Use current timestamp for cache busting in development
        cache_version = str(int(time.time()))
    else:
        # In production, use a static version or git commit hash
        cache_version = getattr(settings, 'STATIC_VERSION', '1.0.0')
    
    return {
        'cache_version': cache_version,
        'debug_mode': settings.DEBUG,
    }


def user_permissions(request: HttpRequest) -> Dict[str, Any]:
    """
    Add user permission flags to template context.
    Primarily used for OSA compliance - restricting comments/feed for users under 18.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Contains user permission flags for OSA compliance
    """
    context = {
        'can_access_comments': True,  # Default for anonymous users (they see login prompt)
        'is_minor': False,
        'osa_restricted': False,
    }
    
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        
        if profile:
            # Check if user can access comments based on age and verification
            can_access = profile.can_access_comments
            is_minor = not profile.is_adult() if profile.date_of_birth and profile.age_verified else False
            
            context.update({
                'can_access_comments': can_access,
                'is_minor': is_minor,
                'osa_restricted': is_minor and not can_access,
                'user_age': profile.age() if profile.date_of_birth else None,
                'age_verified': profile.age_verified,
            })
    
    return context
