"""
Following system services and utilities.

Provides high-level functions for managing follows, generating feeds,
and calculating trending content.
"""

from django.db.models import Q, F, Count, Avg, Sum, Case, When, FloatField
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Optional, Union, Any
import logging

from ..models import (
    FollowableItem, FeedUpdate, FeedInteraction, UserFeedPreferences,
    TrendingContent, Council, CouncilList, 
)
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class FollowService:
    """Service for managing user follows and followable content."""
    
    @staticmethod
    def follow_item(user, item, priority='normal', email_notifications=True, push_notifications=True):
        """
        Follow any followable item (Council, List, User, Field).
        
        Args:
            user: User who wants to follow
            item: Object to follow (Council, CouncilList, User, Field, etc.)
            priority: Priority level for this follow
            email_notifications: Whether to enable email notifications
            push_notifications: Whether to enable push notifications
            
        Returns:
            FollowableItem instance or None if already following
        """
        content_type = ContentType.objects.get_for_model(item)
        
        follow, created = FollowableItem.objects.get_or_create(
            user=user,
            content_type=content_type,
            object_id=item.id,
            defaults={
                'priority': priority,
                'email_notifications': email_notifications,
                'push_notifications': push_notifications,
            }
        )
        
        if created:
            logger.info(f"User {user.id} started following {content_type.model} {item.id}")
            
            # Create a feed update about this new follow
            FeedService.create_system_update(
                source_object=item,
                title=f"New Follower",
                message=f"{user.get_full_name() or user.username} started following {item}",
                author=user,
                update_type='system'
            )
        
        return follow if created else None
    
    @staticmethod
    def unfollow_item(user, item):
        """
        Unfollow an item.
        
        Args:
            user: User who wants to unfollow
            item: Object to unfollow
            
        Returns:
            bool: True if unfollowed, False if wasn't following
        """
        content_type = ContentType.objects.get_for_model(item)
        
        deleted_count, _ = FollowableItem.objects.filter(
            user=user,
            content_type=content_type,
            object_id=item.id
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"User {user.id} unfollowed {content_type.model} {item.id}")
        
        return deleted_count > 0
    
    @staticmethod
    def is_following(user, item):
        """Check if user is following an item."""
        if not user.is_authenticated:
            return False
            
        content_type = ContentType.objects.get_for_model(item)
        return FollowableItem.objects.filter(
            user=user,
            content_type=content_type,
            object_id=item.id
        ).exists()
    
    @staticmethod
    def get_user_follows(user, content_type=None, priority=None):
        """
        Get all items a user is following.
        
        Args:
            user: User to get follows for
            content_type: Optional filter by content type
            priority: Optional filter by priority
            
        Returns:
            QuerySet of FollowableItem
        """
        follows = FollowableItem.objects.filter(user=user).select_related('content_type')
        
        if content_type:
            if isinstance(content_type, str):
                follows = follows.filter(content_type__model=content_type)
            else:
                follows = follows.filter(content_type=content_type)
        
        if priority:
            follows = follows.filter(priority=priority)
        
        return follows.order_by('-created_at')
    
    @staticmethod
    def get_follower_count(item):
        """Get the number of followers for an item."""
        content_type = ContentType.objects.get_for_model(item)
        return FollowableItem.objects.filter(
            content_type=content_type,
            object_id=item.id
        ).count()
    
    @staticmethod
    def get_followers(item, limit=None):
        """Get users following an item."""
        content_type = ContentType.objects.get_for_model(item)
        follows = FollowableItem.objects.filter(
            content_type=content_type,
            object_id=item.id
        ).select_related('user').order_by('-created_at')
        
        if limit:
            follows = follows[:limit]
        
        return [follow.user for follow in follows]


class FeedService:
    """Service for managing feed updates and content."""
    
    @staticmethod
    def create_update(source_object, update_type, title, message, author=None, 
                     rich_content=None, is_public=True, targeted_followers_only=False):
        """
        Create a new feed update.
        
        Args:
            source_object: Object that this update relates to
            update_type: Type of update (financial, contribution, etc.)
            title: Update title
            message: Update message
            author: User who created this update
            rich_content: Optional JSON data for rich content
            is_public: Whether update is publicly visible
            targeted_followers_only: Whether to only show to followers
            
        Returns:
            FeedUpdate instance
        """
        content_type = ContentType.objects.get_for_model(source_object)
        
        update = FeedUpdate.objects.create(
            content_type=content_type,
            object_id=source_object.id,
            update_type=update_type,
            title=title,
            message=message,
            author=author,
            rich_content=rich_content or {},
            is_public=is_public,
            targeted_followers_only=targeted_followers_only
        )
        
        logger.info(f"Created feed update {update.id} for {content_type.model} {source_object.id}")
        return update
    
    @staticmethod
    def create_contribution_update(contribution, author):
        """Create a feed update for a new contribution."""
        return FeedService.create_update(
            source_object=contribution,
            update_type='contribution',
            title=f"New data contributed for {contribution.council.name}",
            message=f"{author.get_full_name() or author.username} contributed new financial data",
            author=author,
            rich_content={
                'contribution_id': contribution.id,
                'council_name': contribution.council.name,
                'fields_updated': getattr(contribution, 'fields_updated', [])
            }
        )
    
    @staticmethod
    def create_financial_update(council, field_name, old_value, new_value, author=None):
        """Create a feed update for financial data changes."""
        return FeedService.create_update(
            source_object=council,
            update_type='financial',
            title=f"{council.name}: {field_name} updated",
            message=f"{field_name} changed from {old_value} to {new_value}",
            author=author,
            rich_content={
                'field_name': field_name,
                'old_value': str(old_value) if old_value else None,
                'new_value': str(new_value) if new_value else None,
                'change_type': 'increase' if (new_value or 0) > (old_value or 0) else 'decrease'
            }
        )
    
    @staticmethod
    def create_list_update(council_list, action, councils_affected=None, author=None):
        """Create a feed update for list changes."""
        if action == 'created':
            message = f"Created new list '{council_list.name}'"
        elif action == 'councils_added':
            message = f"Added {len(councils_affected) if councils_affected else 0} councils to '{council_list.name}'"
        elif action == 'councils_removed':
            message = f"Removed {len(councils_affected) if councils_affected else 0} councils from '{council_list.name}'"
        else:
            message = f"Updated list '{council_list.name}'"
        
        return FeedService.create_update(
            source_object=council_list,
            update_type='list_change',
            title=f"List Update: {council_list.name}",
            message=message,
            author=author,
            rich_content={
                'action': action,
                'councils_affected': [c.id for c in councils_affected] if councils_affected else [],
                'list_size': council_list.councils.count()
            }
        )
    
    @staticmethod
    def create_system_update(source_object, title, message, author=None, update_type='system'):
        """Create a system-generated update."""
        return FeedService.create_update(
            source_object=source_object,
            update_type=update_type,
            title=title,
            message=message,
            author=author
        )
    
    @staticmethod
    def get_personalized_feed(user, limit=50, algorithm='mixed', content_filters=None, feed_filter='all'):
        """
        Get personalized feed for user based on their follows and preferences.
        
        Args:
            user: User to get feed for
            limit: Maximum number of items to return
            algorithm: Algorithm to use (chronological, engagement, priority, mixed)
            content_filters: Q object with content filtering logic
            feed_filter: Specific filter type (financial, contributions, etc.)
            
        Returns:
            QuerySet of FeedUpdate
        """
        if not user.is_authenticated:
            # Return public updates for anonymous users
            updates = FeedUpdate.objects.filter(
                is_public=True,
                targeted_followers_only=False
            ).select_related('content_type', 'author')
            
            # Apply filters for anonymous users too
            if content_filters and content_filters.children:
                updates = updates.filter(content_filters)
                
            if feed_filter == 'financial':
                updates = updates.filter(update_type='financial')
            elif feed_filter == 'contributions':
                updates = updates.filter(update_type='contribution')
            elif feed_filter == 'councils':
                from ..models import Council
                updates = updates.filter(content_type=ContentType.objects.get_for_model(Council))
            elif feed_filter == 'lists':
                from ..models import CouncilList
                updates = updates.filter(content_type=ContentType.objects.get_for_model(CouncilList))
                
            return updates.order_by('-created_at')[:limit]
        
        # Get user's follows
        follows = FollowableItem.objects.filter(user=user).values(
            'content_type', 'object_id', 'priority'
        )
        
        if not follows.exists():
            # User doesn't follow anything, show trending/public content
            updates = FeedUpdate.objects.filter(
                is_public=True,
                targeted_followers_only=False
            ).select_related('content_type', 'author')
            
            # Apply filters for users with no follows too
            if content_filters and content_filters.children:
                updates = updates.filter(content_filters)
                
            if feed_filter == 'financial':
                updates = updates.filter(update_type='financial')
            elif feed_filter == 'contributions':
                updates = updates.filter(update_type='contribution')
            elif feed_filter == 'councils':
                from ..models import Council
                updates = updates.filter(content_type=ContentType.objects.get_for_model(Council))
            elif feed_filter == 'lists':
                from ..models import CouncilList
                updates = updates.filter(content_type=ContentType.objects.get_for_model(CouncilList))
                
            return updates.order_by('-created_at')[:limit]
        
        # Build filter for followed content
        follow_filters = Q()
        for follow in follows:
            follow_filters |= Q(
                content_type_id=follow['content_type'],
                object_id=follow['object_id']
            )
        
        # Base queryset
        updates = FeedUpdate.objects.filter(
            Q(is_public=True) & (follow_filters | Q(targeted_followers_only=False))
        ).select_related('content_type', 'author')
        
        # Apply content filters if provided
        if content_filters and content_filters.children:
            updates = updates.filter(content_filters)
            
        # Apply feed-specific filters
        if feed_filter == 'financial':
            updates = updates.filter(update_type='financial')
        elif feed_filter == 'contributions':
            updates = updates.filter(update_type='contribution')
        elif feed_filter == 'councils':
            from ..models import Council
            updates = updates.filter(content_type=ContentType.objects.get_for_model(Council))
        elif feed_filter == 'lists':
            from ..models import CouncilList
            updates = updates.filter(content_type=ContentType.objects.get_for_model(CouncilList))
        
        # Apply algorithm
        if algorithm == 'chronological':
            updates = updates.order_by('-created_at')
        elif algorithm == 'engagement':
            updates = updates.annotate(
                engagement_score=F('like_count') + F('comment_count') + F('share_count')
            ).order_by('-engagement_score', '-created_at')
        elif algorithm == 'priority':
            # Create priority score based on user's follow priorities
            priority_cases = []
            for follow in follows:
                priority_value = {'critical': 4, 'high': 3, 'normal': 2, 'low': 1}.get(follow['priority'], 2)
                priority_cases.append(
                    When(
                        content_type_id=follow['content_type'],
                        object_id=follow['object_id'],
                        then=priority_value
                    )
                )
            
            updates = updates.annotate(
                priority_score=Case(*priority_cases, default=1, output_field=FloatField())
            ).order_by('-priority_score', '-created_at')
        else:  # mixed algorithm
            updates = updates.annotate(
                engagement_score=F('like_count') + F('comment_count') + F('share_count'),
                recency_score=Case(
                    When(created_at__gte=timezone.now() - timedelta(hours=1), then=5),
                    When(created_at__gte=timezone.now() - timedelta(hours=6), then=4),
                    When(created_at__gte=timezone.now() - timedelta(days=1), then=3),
                    When(created_at__gte=timezone.now() - timedelta(days=7), then=2),
                    default=1,
                    output_field=FloatField()
                ),
                mixed_score=F('engagement_score') + F('recency_score')
            ).order_by('-mixed_score', '-created_at')
        
        return updates[:limit]
    
    @staticmethod
    def get_recent_updates_count(user, days=7, content_filters=None, feed_filter='all'):
        """
        Get count of recent updates for the user's feed.
        
        Args:
            user: User to get count for
            days: Number of days to look back
            content_filters: Q object with content filtering logic
            feed_filter: Specific filter type (financial, contributions, etc.)
            
        Returns:
            Integer count of recent updates
        """
        from django.utils import timezone
        from datetime import timedelta
        
        recent_cutoff = timezone.now() - timedelta(days=days)
        
        if not user.is_authenticated:
            # Return count of public updates for anonymous users
            updates = FeedUpdate.objects.filter(
                is_public=True,
                targeted_followers_only=False,
                created_at__gte=recent_cutoff
            )
            
            # Apply filters for anonymous users
            if content_filters and content_filters.children:
                updates = updates.filter(content_filters)
                
            if feed_filter == 'financial':
                updates = updates.filter(update_type='financial')
            elif feed_filter == 'contributions':
                updates = updates.filter(update_type='contribution')
            elif feed_filter == 'councils':
                from ..models import Council
                updates = updates.filter(content_type=ContentType.objects.get_for_model(Council))
            elif feed_filter == 'lists':
                from ..models import CouncilList
                updates = updates.filter(content_type=ContentType.objects.get_for_model(CouncilList))
                
            return updates.count()
        
        # Get user's follows
        follows = FollowableItem.objects.filter(user=user).values(
            'content_type', 'object_id'
        )
        
        if not follows.exists():
            # User doesn't follow anything, show trending/public content count
            updates = FeedUpdate.objects.filter(
                is_public=True,
                targeted_followers_only=False,
                created_at__gte=recent_cutoff
            )
            
            # Apply filters for users with no follows
            if content_filters and content_filters.children:
                updates = updates.filter(content_filters)
                
            if feed_filter == 'financial':
                updates = updates.filter(update_type='financial')
            elif feed_filter == 'contributions':
                updates = updates.filter(update_type='contribution')
            elif feed_filter == 'councils':
                from ..models import Council
                updates = updates.filter(content_type=ContentType.objects.get_for_model(Council))
            elif feed_filter == 'lists':
                from ..models import CouncilList
                updates = updates.filter(content_type=ContentType.objects.get_for_model(CouncilList))
                
            return updates.count()
        
        # Build filter for followed content
        follow_filters = Q()
        for follow in follows:
            follow_filters |= Q(
                content_type_id=follow['content_type'],
                object_id=follow['object_id']
            )
        
        # Base queryset for count
        updates = FeedUpdate.objects.filter(
            Q(is_public=True) & (follow_filters | Q(targeted_followers_only=False)),
            created_at__gte=recent_cutoff
        )
        
        # Apply content filters if provided
        if content_filters and content_filters.children:
            updates = updates.filter(content_filters)
            
        # Apply feed-specific filters
        if feed_filter == 'financial':
            updates = updates.filter(update_type='financial')
        elif feed_filter == 'contributions':
            updates = updates.filter(update_type='contribution')
        elif feed_filter == 'councils':
            from ..models import Council
            updates = updates.filter(content_type=ContentType.objects.get_for_model(Council))
        elif feed_filter == 'lists':
            from ..models import CouncilList
            updates = updates.filter(content_type=ContentType.objects.get_for_model(CouncilList))
        
        return updates.count()
    
    @staticmethod
    def get_trending_updates(days=7, limit=20):
        """Get trending updates based on engagement."""
        since = timezone.now() - timedelta(days=days)
        
        return FeedUpdate.objects.filter(
            created_at__gte=since,
            is_public=True
        ).annotate(
            trend_score=F('view_count') + (F('like_count') * 2) + (F('comment_count') * 3) + (F('share_count') * 4)
        ).order_by('-trend_score')[:limit]


class TrendingService:
    """Service for calculating and managing trending content."""
    
    @staticmethod
    def calculate_trending_councils(period_hours=24):
        """Calculate trending councils based on recent activity."""
        since = timezone.now() - timedelta(hours=period_hours)
        
        # Get councils with recent activity
        council_stats = {}
        
        # Follow velocity
        recent_follows = FollowableItem.objects.filter(
            created_at__gte=since,
            content_type=ContentType.objects.get_for_model(Council)
        ).values('object_id').annotate(follow_count=Count('id'))
        
        for stat in recent_follows:
            council_id = stat['object_id']
            if council_id not in council_stats:
                council_stats[council_id] = {'follow_velocity': 0, 'engagement_velocity': 0, 'view_velocity': 0}
            council_stats[council_id]['follow_velocity'] = stat['follow_count']
        
        # Engagement velocity from feed updates
        council_updates = FeedUpdate.objects.filter(
            created_at__gte=since,
            content_type=ContentType.objects.get_for_model(Council)
        ).values('object_id').annotate(
            total_likes=Sum('like_count'),
            total_comments=Sum('comment_count'),
            total_shares=Sum('share_count'),
            total_views=Sum('view_count')
        )
        
        for stat in council_updates:
            council_id = stat['object_id']
            if council_id not in council_stats:
                council_stats[council_id] = {'follow_velocity': 0, 'engagement_velocity': 0, 'view_velocity': 0}
            
            engagement = (stat['total_likes'] or 0) + (stat['total_comments'] or 0) * 2 + (stat['total_shares'] or 0) * 3
            council_stats[council_id]['engagement_velocity'] = engagement
            council_stats[council_id]['view_velocity'] = stat['total_views'] or 0
        
        # Calculate trend scores and update TrendingContent
        content_type = ContentType.objects.get_for_model(Council)
        period_start = since
        period_end = timezone.now()
        
        for council_id, stats in council_stats.items():
            # Weighted trend score
            trend_score = (
                stats['follow_velocity'] * 3 +
                stats['engagement_velocity'] * 2 +
                stats['view_velocity'] * 1
            )
            
            if trend_score > 0:
                TrendingContent.objects.update_or_create(
                    content_type=content_type,
                    object_id=council_id,
                    period_start=period_start,
                    period_end=period_end,
                    defaults={
                        'trend_score': trend_score,
                        'follow_velocity': stats['follow_velocity'],
                        'engagement_velocity': stats['engagement_velocity'],
                        'view_velocity': stats['view_velocity'],
                        'reason': f"High activity in last {period_hours}h"
                    }
                )
        
        logger.info(f"Updated trending calculations for {len(council_stats)} councils")
    
    @staticmethod
    def get_trending_content(content_type=None, limit=10, promote_threshold=50):
        """
        Get trending content, optionally filtered by type.
        
        Args:
            content_type: Optional content type filter
            limit: Maximum items to return
            promote_threshold: Minimum trend score for promotion
            
        Returns:
            QuerySet of TrendingContent
        """
        trending = TrendingContent.objects.filter(
            trend_score__gte=promote_threshold
        ).select_related('content_type').order_by('-trend_score')
        
        if content_type:
            if isinstance(content_type, str):
                trending = trending.filter(content_type__model=content_type)
            else:
                trending = trending.filter(content_type=content_type)
        
        return trending[:limit]
    
    @staticmethod
    def mark_for_promotion(trending_item):
        """Mark a trending item for home page promotion."""
        trending_item.is_promoted = True
        trending_item.save(update_fields=['is_promoted'])
        
        logger.info(f"Marked {trending_item.content_object} for promotion (score: {trending_item.trend_score})")


class EngagementService:
    """Service for tracking and managing user engagement."""
    
    @staticmethod
    def record_interaction(user, update, interaction_type, notes=''):
        """Record a user interaction with a feed update."""
        interaction, created = FeedInteraction.objects.get_or_create(
            user=user,
            update=update,
            interaction_type=interaction_type,
            defaults={'notes': notes}
        )
        
        if created:
            # Update counters on the feed update
            if interaction_type == 'like':
                FeedUpdate.objects.filter(id=update.id).update(like_count=F('like_count') + 1)
            elif interaction_type == 'share':
                FeedUpdate.objects.filter(id=update.id).update(share_count=F('share_count') + 1)
            
            logger.debug(f"User {user.id} {interaction_type}d update {update.id}")
        
        return interaction
    
    @staticmethod
    def remove_interaction(user, update, interaction_type):
        """Remove a user interaction."""
        deleted_count, _ = FeedInteraction.objects.filter(
            user=user,
            update=update,
            interaction_type=interaction_type
        ).delete()
        
        if deleted_count > 0:
            # Update counters
            if interaction_type == 'like':
                FeedUpdate.objects.filter(id=update.id).update(like_count=F('like_count') - 1)
            elif interaction_type == 'share':
                FeedUpdate.objects.filter(id=update.id).update(share_count=F('share_count') - 1)
        
        return deleted_count > 0
    
    @staticmethod
    def get_user_interactions(user, interaction_type=None, limit=None):
        """Get user's interactions, optionally filtered by type."""
        interactions = FeedInteraction.objects.filter(user=user).select_related('update')
        
        if interaction_type:
            interactions = interactions.filter(interaction_type=interaction_type)
        
        interactions = interactions.order_by('-created_at')
        
        if limit:
            interactions = interactions[:limit]
        
        return interactions
