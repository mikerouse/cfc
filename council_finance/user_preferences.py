"""
User Preferences System for Council Finance Counters

This module provides a centralized system for managing user preferences
including font choices, accessibility options, and theme settings.
"""

from typing import Dict, Any, Optional
from django.http import HttpRequest
from django.conf import settings
import os


class UserPreferences:
    """
    Centralized user preferences management system.
    
    This class handles all user preference logic including:
    - Font family selection from Google Fonts
    - Font size for accessibility
    - High contrast mode
    - Color theme preferences
    - Fallback handling for anonymous users
    """
    
    # Available Google Fonts - curated for readability and government style
    GOOGLE_FONTS = {
        'Cairo': 'Cairo:wght@300;400;600;700',
        'Inter': 'Inter:wght@300;400;500;600;700',
        'Open Sans': 'Open+Sans:wght@300;400;600;700',
        'Roboto': 'Roboto:wght@300;400;500;700',
        'Lato': 'Lato:wght@300;400;700',
        'Source Sans Pro': 'Source+Sans+Pro:wght@300;400;600;700',
        'Nunito Sans': 'Nunito+Sans:wght@300;400;600;700',
        'Poppins': 'Poppins:wght@300;400;500;600;700',
        'Montserrat': 'Montserrat:wght@300;400;500;600;700',
        'PT Sans': 'PT+Sans:wght@400;700',
    }
    
    # Font size mappings to CSS values
    FONT_SIZES = {
        'small': '14px',
        'medium': '16px',
        'large': '18px',
        'extra-large': '20px',
    }
    
    # Default preferences for fallback
    DEFAULTS = {
        'font_family': 'Cairo',
        'font_size': 'medium',
        'high_contrast_mode': False,
        'color_theme': 'auto',
    }
    
    def __init__(self, request: HttpRequest):
        """
        Initialize preferences system with request context.
        
        Args:
            request: Django HttpRequest object
        """
        self.request = request
        self.user = request.user
        
    def get_preferences(self) -> Dict[str, Any]:
        """
        Get all user preferences with fallbacks.
        
        Returns:
            dict: Complete user preferences dictionary
        """
        preferences = self.DEFAULTS.copy()
        
        # Get preferences from user profile if authenticated
        if self.user.is_authenticated and hasattr(self.user, 'profile'):
            profile = self.user.profile
            preferences.update({
                'font_family': profile.preferred_font or self.DEFAULTS['font_family'],
                'font_size': getattr(profile, 'font_size', self.DEFAULTS['font_size']),
                'high_contrast_mode': getattr(profile, 'high_contrast_mode', self.DEFAULTS['high_contrast_mode']),
                'color_theme': getattr(profile, 'color_theme', self.DEFAULTS['color_theme']),
            })
        
        # Override with session preferences if available (for anonymous users)
        session_prefs = self.request.session.get('user_preferences', {})
        preferences.update(session_prefs)
        
        return preferences
    
    def get_font_family(self) -> str:
        """Get the user's preferred font family."""
        return self.get_preferences()['font_family']
    
    def get_font_size(self) -> str:
        """Get the user's preferred font size in CSS units."""
        size_key = self.get_preferences()['font_size']
        return self.FONT_SIZES.get(size_key, self.FONT_SIZES['medium'])
    
    def get_google_fonts_url(self) -> str:
        """
        Generate Google Fonts URL for the user's preferred font.
        
        Returns:
            str: Complete Google Fonts CSS URL
        """
        font_family = self.get_font_family()
        font_spec = self.GOOGLE_FONTS.get(font_family, self.GOOGLE_FONTS['Cairo'])
        return f"https://fonts.googleapis.com/css2?family={font_spec}&display=swap"
    
    def get_css_variables(self) -> Dict[str, str]:
        """
        Generate CSS custom properties for user preferences.
        
        Returns:
            dict: CSS variables for use in templates
        """
        prefs = self.get_preferences()
        
        variables = {
            '--font-family-primary': f"'{prefs['font_family']}', sans-serif",
            '--font-size-base': self.get_font_size(),
            '--theme-mode': prefs['color_theme'],
        }
        
        # Add high contrast variables if enabled
        if prefs['high_contrast_mode']:
            variables.update({
                '--color-background': '#000000',
                '--color-text': '#ffffff',
                '--color-primary': '#ffff00',
                '--color-secondary': '#00ffff',
                '--color-border': '#ffffff',
                '--contrast-mode': 'high',
            })
        else:
            # Standard GOV.UK inspired colors
            variables.update({
                '--color-background': '#ffffff',
                '--color-text': '#0b0c0c',
                '--color-primary': '#1d70b8',
                '--color-secondary': '#28a197',
                '--color-border': '#b1b4b6',
                '--contrast-mode': 'normal',
            })
        
        return variables
    
    def get_accessibility_classes(self) -> str:
        """
        Generate CSS classes for accessibility features.
        
        Returns:
            str: Space-separated CSS classes
        """
        prefs = self.get_preferences()
        classes = []
        
        if prefs['high_contrast_mode']:
            classes.append('high-contrast')
        
        classes.append(f"font-size-{prefs['font_size']}")
        classes.append(f"theme-{prefs['color_theme']}")
        
        return ' '.join(classes)
    
    def set_session_preference(self, key: str, value: Any) -> None:
        """
        Set a preference in the session (for anonymous users).
        
        Args:
            key: Preference key
            value: Preference value
        """
        if 'user_preferences' not in self.request.session:
            self.request.session['user_preferences'] = {}
        
        self.request.session['user_preferences'][key] = value
        self.request.session.modified = True
    
    def update_profile_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        Update user profile preferences (for authenticated users).
        
        Args:
            preferences: Dictionary of preferences to update
            
        Returns:
            bool: True if update was successful
        """
        if not (self.user.is_authenticated and hasattr(self.user, 'profile')):
            return False
        
        profile = self.user.profile
        
        # Update available fields
        if 'font_family' in preferences:
            profile.preferred_font = preferences['font_family']
        
        if 'font_size' in preferences:
            profile.font_size = preferences['font_size']
        
        if 'high_contrast_mode' in preferences:
            profile.high_contrast_mode = preferences['high_contrast_mode']
        
        if 'color_theme' in preferences:
            profile.color_theme = preferences['color_theme']
        
        try:
            profile.save()
            return True
        except Exception:
            return False


def get_user_preferences_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Get complete user preferences context for templates.
    
    This function serves as the main interface for template context processors.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Complete preferences context for templates
    """
    prefs = UserPreferences(request)
    preferences = prefs.get_preferences()
    
    return {
        'user_preferences': preferences,
        'font_family': preferences['font_family'],
        'font_size_css': prefs.get_font_size(),
        'google_fonts_url': prefs.get_google_fonts_url(),
        'css_variables': prefs.get_css_variables(),
        'accessibility_classes': prefs.get_accessibility_classes(),
        'available_fonts': list(prefs.GOOGLE_FONTS.keys()),
        'available_font_sizes': prefs.FONT_SIZES,
        'high_contrast_mode': preferences['high_contrast_mode'],
        'color_theme': preferences['color_theme'],
    }
