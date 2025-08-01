"""
Feed Update Signal Handlers

Automatically triggers feed updates when data changes occur.
Designed to be hookable and extensible for different types of content updates.
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import (
    FinancialFigure, Council, CouncilList, Contribution,
    FeedUpdate, FollowableItem
)
from ..services.following_services import FeedService

User = get_user_model()
logger = logging.getLogger(__name__)


class FeedUpdateHooks:
    """
    Hookable system for extending feed update triggers.
    
    This allows other parts of the system to register custom hooks
    for generating feed updates when specific events occur.
    """
    
    _hooks = {
        'financial_data_changed': [],
        'contribution_created': [],
        'council_updated': [],
        'list_updated': [],
        'user_achievement': [],
        'custom_event': []
    }
    
    @classmethod
    def register_hook(cls, event_type, hook_function):
        """
        Register a hook function for a specific event type.
        
        Args:
            event_type (str): Type of event ('financial_data_changed', etc.)
            hook_function (callable): Function to call when event occurs
                Signature: hook_function(instance, event_data, **kwargs)
        """
        if event_type not in cls._hooks:
            cls._hooks[event_type] = []
        
        cls._hooks[event_type].append(hook_function)
        logger.info(f"Registered feed update hook for {event_type}: {hook_function.__name__}")
    
    @classmethod
    def trigger_hooks(cls, event_type, instance, event_data=None, **kwargs):
        """
        Trigger all registered hooks for an event type.
        
        Args:
            event_type (str): Type of event that occurred
            instance: Model instance that triggered the event
            event_data (dict): Additional data about the event
            **kwargs: Additional keyword arguments
        """
        hooks = cls._hooks.get(event_type, [])
        
        for hook_function in hooks:
            try:
                hook_function(instance, event_data or {}, **kwargs)
            except Exception as e:
                logger.error(f"Feed update hook {hook_function.__name__} failed for {event_type}: {e}")
    
    @classmethod
    def list_hooks(cls):
        """List all registered hooks for debugging."""
        return {event_type: [f.__name__ for f in hooks] for event_type, hooks in cls._hooks.items()}


def create_financial_data_feed_update(instance, event_data, **kwargs):
    """
    Default hook for financial data changes.
    Creates feed updates when financial figures are added/updated.
    """
    try:
        council = instance.council
        field_name = instance.field.name if instance.field else 'Financial Data'
        
        # Get the user who made the change (if available)
        author = event_data.get('author')
        
        # Determine the type of change
        old_value = event_data.get('old_value')
        new_value = instance.value
        
        if old_value is None:
            # New data added
            title = f"New {field_name} data for {council.name}"
            message = f"Added {field_name}: {new_value}"
            change_type = 'new'
        else:
            # Data updated
            title = f"{council.name}: {field_name} updated"
            message = f"{field_name} changed from {old_value} to {new_value}"
            change_type = 'updated'
        
        # Create rich content with more context
        rich_content = {
            'field_name': field_name,
            'field_slug': instance.field.slug if instance.field else None,
            'old_value': str(old_value) if old_value is not None else None,
            'new_value': str(new_value),
            'change_type': change_type,
            'council_slug': council.slug,
            'council_name': council.name,
            'year': instance.year.label if instance.year else None,
            'percentage_change': None
        }
        
        # Calculate percentage change if both values are numeric
        if old_value is not None:
            try:
                old_val = float(old_value)
                new_val = float(new_value)
                if old_val != 0:
                    percentage_change = ((new_val - old_val) / old_val) * 100
                    rich_content['percentage_change'] = round(percentage_change, 2)
            except (ValueError, TypeError):
                pass
        
        # Create the feed update
        feed_update = FeedService.create_update(
            source_object=council,
            update_type='financial',
            title=title,
            message=message,
            author=author,
            rich_content=rich_content
        )
        
        logger.info(f"Created financial feed update {feed_update.id} for {council.name} - {field_name}")
        return feed_update
        
    except Exception as e:
        logger.error(f"Failed to create financial data feed update: {e}")
        return None


def create_contribution_feed_update(instance, event_data, **kwargs):
    """
    Default hook for contribution events.
    Creates feed updates when users contribute data.
    """
    try:
        author = instance.user if hasattr(instance, 'user') else event_data.get('author')
        council = instance.council if hasattr(instance, 'council') else event_data.get('council')
        
        if not council:
            logger.warning("Cannot create contribution feed update without council")
            return None
        
        # Create feed update
        title = f"New contribution for {council.name}"
        message = f"{author.get_full_name() or author.username if author else 'Someone'} contributed new data"
        
        rich_content = {
            'contribution_id': instance.id,
            'council_slug': council.slug,
            'council_name': council.name,
            'contributor_name': author.get_full_name() or author.username if author else 'Anonymous',
            'fields_contributed': event_data.get('fields_contributed', [])
        }
        
        feed_update = FeedService.create_update(
            source_object=council,
            update_type='contribution',
            title=title,
            message=message,
            author=author,
            rich_content=rich_content
        )
        
        logger.info(f"Created contribution feed update {feed_update.id} for {council.name}")
        return feed_update
        
    except Exception as e:
        logger.error(f"Failed to create contribution feed update: {e}")
        return None


def create_list_change_feed_update(instance, event_data, **kwargs):
    """
    Default hook for council list changes.
    Creates feed updates when lists are modified.
    """
    try:
        action = event_data.get('action', 'updated')
        author = event_data.get('author')
        councils_affected = event_data.get('councils_affected', [])
        
        if action == 'created':
            title = f"New list created: {instance.name}"
            message = f"Created a new council list with {instance.councils.count()} councils"
        elif action == 'councils_added':
            title = f"Councils added to {instance.name}"
            message = f"Added {len(councils_affected)} councils to the list"
        elif action == 'councils_removed':
            title = f"Councils removed from {instance.name}"
            message = f"Removed {len(councils_affected)} councils from the list"
        else:
            title = f"List updated: {instance.name}"
            message = f"Made changes to the council list"
        
        rich_content = {
            'list_id': instance.id,
            'list_name': instance.name,
            'list_slug': instance.slug,
            'action': action,
            'councils_affected': [{'id': c.id, 'name': c.name, 'slug': c.slug} for c in councils_affected],
            'total_councils': instance.councils.count()
        }
        
        feed_update = FeedService.create_update(
            source_object=instance,
            update_type='list_change',
            title=title,
            message=message,
            author=author,
            rich_content=rich_content
        )
        
        logger.info(f"Created list change feed update {feed_update.id} for {instance.name}")
        return feed_update
        
    except Exception as e:
        logger.error(f"Failed to create list change feed update: {e}")
        return None


# Register default hooks
FeedUpdateHooks.register_hook('financial_data_changed', create_financial_data_feed_update)
FeedUpdateHooks.register_hook('contribution_created', create_contribution_feed_update)
FeedUpdateHooks.register_hook('list_updated', create_list_change_feed_update)


@receiver(pre_save, sender=FinancialFigure)
def capture_financial_figure_old_value(sender, instance, **kwargs):
    """Capture the old value before saving to track changes."""
    if instance.pk:
        try:
            old_instance = FinancialFigure.objects.get(pk=instance.pk)
            instance._old_value = old_instance.value
        except FinancialFigure.DoesNotExist:
            instance._old_value = None
    else:
        instance._old_value = None


@receiver(post_save, sender=FinancialFigure)
def financial_figure_updated(sender, instance, created, **kwargs):
    """
    Signal handler for FinancialFigure changes.
    Triggers feed updates when financial data is added or updated.
    """
    try:
        # Skip if this is a bulk operation or migration
        if kwargs.get('raw', False):
            return
        
        # Get the old value that was captured in pre_save
        old_value = getattr(instance, '_old_value', None)
        
        # Only create feed update if the value actually changed or is new
        if created or (old_value is not None and str(old_value) != str(instance.value)):
            event_data = {
                'old_value': old_value,
                'new_value': instance.value,
                'created': created,
                'author': getattr(instance, '_author', None)  # Can be set by the view
            }
            
            FeedUpdateHooks.trigger_hooks(
                'financial_data_changed',
                instance,
                event_data
            )
    
    except Exception as e:
        logger.error(f"Error in financial_figure_updated signal: {e}")


@receiver(post_save, sender=Contribution)
def contribution_created(sender, instance, created, **kwargs):
    """
    Signal handler for new contributions.
    Triggers feed updates when users contribute data.
    """
    if created and not kwargs.get('raw', False):
        try:
            event_data = {
                'fields_contributed': getattr(instance, '_fields_contributed', []),
                'author': instance.user if hasattr(instance, 'user') else None,
                'council': instance.council if hasattr(instance, 'council') else None
            }
            
            FeedUpdateHooks.trigger_hooks(
                'contribution_created',
                instance,
                event_data
            )
        
        except Exception as e:
            logger.error(f"Error in contribution_created signal: {e}")


@receiver(post_save, sender=CouncilList)
def council_list_updated(sender, instance, created, **kwargs):
    """
    Signal handler for council list changes.
    Note: This handles list creation, but not council additions/removals
    which need to be triggered manually by views.
    """
    if created and not kwargs.get('raw', False):
        try:
            event_data = {
                'action': 'created',
                'author': getattr(instance, '_author', None),
                'councils_affected': []
            }
            
            FeedUpdateHooks.trigger_hooks(
                'list_updated',
                instance,
                event_data
            )
        
        except Exception as e:
            logger.error(f"Error in council_list_updated signal: {e}")


# Utility functions for manual trigger of feed updates
def trigger_list_councils_changed(council_list, action, councils_affected, author=None):
    """
    Manually trigger feed update for council list changes.
    Use this in views when councils are added/removed from lists.
    
    Args:
        council_list: CouncilList instance
        action: 'councils_added' or 'councils_removed'
        councils_affected: List of Council instances
        author: User who made the change
    """
    event_data = {
        'action': action,
        'author': author,
        'councils_affected': councils_affected
    }
    
    FeedUpdateHooks.trigger_hooks(
        'list_updated',
        council_list,
        event_data
    )


def trigger_custom_feed_update(source_object, title, message, update_type='system', 
                              author=None, rich_content=None):
    """
    Manually trigger a custom feed update.
    
    Args:
        source_object: Object the update relates to
        title: Update title
        message: Update message  
        update_type: Type of update
        author: User who triggered the update
        rich_content: Additional JSON data
    
    Returns:
        FeedUpdate instance
    """
    return FeedService.create_update(
        source_object=source_object,
        update_type=update_type,
        title=title,
        message=message,
        author=author,
        rich_content=rich_content or {}
    )


# Register additional hook for site-wide factoid updates
def create_factoid_regeneration_update(instance, event_data, **kwargs):
    """
    Hook for site-wide factoid regeneration events.
    """
    try:
        title = "AI Insights Updated"
        message = f"New cross-council financial insights have been generated based on updated data"
        
        rich_content = {
            'trigger_council': instance.name if hasattr(instance, 'name') else str(instance),
            'factoid_count': event_data.get('factoid_count', 0),
            'insights_updated': True
        }
        
        # Create a system-wide update (not tied to specific council)
        feed_update = FeedService.create_update(
            source_object=instance,
            update_type='system',
            title=title,
            message=message,
            author=event_data.get('author'),
            rich_content=rich_content
        )
        
        logger.info(f"Created factoid regeneration feed update {feed_update.id}")
        return feed_update
        
    except Exception as e:
        logger.error(f"Failed to create factoid regeneration feed update: {e}")
        return None


FeedUpdateHooks.register_hook('factoid_regenerated', create_factoid_regeneration_update)