"""
Signal handlers for the Council Finance system.

Automatically imports all signal modules to ensure they are registered.
"""

from .feed_signals import (
    FeedUpdateHooks,
    trigger_list_councils_changed,
    trigger_custom_feed_update
)

__all__ = [
    'FeedUpdateHooks',
    'trigger_list_councils_changed', 
    'trigger_custom_feed_update'
]