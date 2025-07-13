"""
Tutorial Display Engine for Council Finance Counters

This module provides a centralized system for managing tutorials across the application.
It supports:
- Debug mode override (always show tutorials when DEBUG=True)
- A/B testing capabilities (future)
- Text size preferences (future)
- Tutorial versioning and analytics
"""

import os
from typing import Dict, List, Optional, Any
from django.conf import settings


class TutorialEngine:
    """
    Central engine for managing tutorial display logic across the application.
    
    This class encapsulates all the business logic for determining when and how
    tutorials should be displayed to users.
    """
    
    def __init__(self):
        self.debug_mode = getattr(settings, 'DEBUG', False)
        # Future: Load from environment or settings
        self.force_debug_tutorials = os.getenv('DEBUG', 'False').lower() == 'true'
    
    def should_show_tutorial(self, tutorial_id: str, user_data: Optional[Dict] = None) -> bool:
        """
        Determine whether a specific tutorial should be shown to the user.
        
        Args:
            tutorial_id: Unique identifier for the tutorial
            user_data: Optional user context (localStorage data, user preferences, etc.)
            
        Returns:
            bool: True if the tutorial should be displayed
        """
        # Always show tutorials in debug mode
        if self.debug_mode or self.force_debug_tutorials:
            return True
            
        # Check if user has already seen this tutorial
        if user_data and user_data.get(f'seen_{tutorial_id}'):
            return False
            
        # Future: Add A/B testing logic here
        # Future: Add user preference checks
        # Future: Add tutorial scheduling logic
        
        return True
    
    def get_tutorial_config(self, tutorial_id: str) -> Dict[str, Any]:
        """
        Get configuration for a specific tutorial.
        
        Args:
            tutorial_id: Unique identifier for the tutorial
            
        Returns:
            dict: Tutorial configuration including slides, styling, behavior
        """
        # Base configuration that applies to all tutorials
        base_config = {
            'debug_mode': self.debug_mode or self.force_debug_tutorials,
            'storage_key': f'seen_{tutorial_id}',
            'animation_duration': 300,
            'backdrop_dismissible': True,
            'escape_dismissible': True,
        }
        
        # Tutorial-specific configurations
        tutorial_configs = {
            'contribute': {
                'title': 'Welcome to Contribute Data',
                'slides': [
                    {
                        'title': 'Welcome to Contribute Data',
                        'content': 'Use this table to add or review council data. Moderators see extra actions like approve, reject, and delete contributions.'
                    }
                    # Future slides can be added here
                ],
                'theme': 'default',
                'size': 'medium'
            },
            # Future tutorials can be added here
            'counter_preview': {
                'title': 'Counter Preview Tool',
                'slides': [
                    {
                        'title': 'Live Preview',
                        'content': 'This tool lets you preview how counters will look before saving them.'
                    }
                ],
                'theme': 'default',
                'size': 'medium'
            }
        }
        
        config = base_config.copy()
        if tutorial_id in tutorial_configs:
            config.update(tutorial_configs[tutorial_id])
        
        return config
    
    def get_tutorial_javascript(self, tutorial_id: str) -> str:
        """
        Generate JavaScript configuration for a tutorial.
        
        Args:
            tutorial_id: Unique identifier for the tutorial
            
        Returns:
            str: JavaScript object configuration
        """
        config = self.get_tutorial_config(tutorial_id)
        
        # Convert Python config to JavaScript-safe format
        js_config = {
            'tutorialId': tutorial_id,
            'debugMode': config['debug_mode'],
            'storageKey': config['storage_key'],
            'slides': config.get('slides', []),
            'title': config.get('title', 'Tutorial'),
            'animationDuration': config['animation_duration'],
            'backdropDismissible': config['backdrop_dismissible'],
            'escapeDismissible': config['escape_dismissible'],
        }
        
        return js_config
    
    def mark_tutorial_seen(self, tutorial_id: str, user_identifier: Optional[str] = None):
        """
        Mark a tutorial as seen for analytics purposes.
        
        Args:
            tutorial_id: Unique identifier for the tutorial
            user_identifier: Optional user identifier for analytics
        """
        # Future: Log to analytics system
        # Future: Update user preferences in database
        pass
    
    def get_all_tutorial_ids(self) -> List[str]:
        """
        Get list of all available tutorial IDs.
        
        Returns:
            list: All registered tutorial IDs
        """
        return ['contribute', 'counter_preview']
    
    def reset_all_tutorials(self):
        """
        Reset all tutorial seen flags (useful for testing).
        This generates JavaScript that can be run in the browser console.
        
        Returns:
            str: JavaScript code to reset tutorials
        """
        tutorial_ids = self.get_all_tutorial_ids()
        js_commands = []
        
        for tutorial_id in tutorial_ids:
            config = self.get_tutorial_config(tutorial_id)
            storage_key = config['storage_key']
            js_commands.append(f"localStorage.removeItem('{storage_key}');")
        
        js_commands.append("console.log('All tutorials reset. Refresh the page to see them again.');")
        
        return '\n'.join(js_commands)


# Global instance
tutorial_engine = TutorialEngine()
