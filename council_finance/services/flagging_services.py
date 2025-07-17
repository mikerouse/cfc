"""
Flagging system services.

Provides functionality for flagging content, managing flags, and community moderation.
"""

from django.db.models import Count, Q, F
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from typing import Optional, List, Dict, Any
import logging

from ..models import (
    Flag, FlaggedContent, UserModerationRecord, FlagComment,
    Contribution, Council, DataField
)
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class FlaggingService:
    """Service for managing the flagging system."""
    
    @staticmethod
    def flag_content(user, content_object, flag_type: str, description: str, 
                    priority: str = 'medium', ip_address: str = None) -> Dict[str, Any]:
        """
        Flag a piece of content for review.
        
        Args:
            user: User raising the flag
            content_object: Object being flagged
            flag_type: Type of flag (see Flag.FLAG_TYPES)
            description: Description of the issue
            priority: Priority level
            ip_address: IP address of the user
            
        Returns:
            Dict with success status and flag information
        """
        try:
            # Check if user has already flagged this content
            content_type = ContentType.objects.get_for_model(content_object)
            existing_flag = Flag.objects.filter(
                flagged_by=user,
                content_type=content_type,
                object_id=content_object.id
            ).first()
            
            if existing_flag:
                return {
                    'success': False,
                    'error': 'You have already flagged this content',
                    'flag': existing_flag
                }
            
            # Check if user is not rate-limited
            if FlaggingService.is_user_rate_limited(user):
                return {
                    'success': False,
                    'error': 'You have reached your flag submission limit. Please try again later.',
                    'flag': None
                }
            
            # Create the flag
            flag = Flag.objects.create(
                flagged_by=user,
                content_type=content_type,
                object_id=content_object.id,
                flag_type=flag_type,
                priority=priority,
                description=description,
                ip_address=ip_address
            )
            
            # Update or create flagged content record
            flagged_content, created = FlaggedContent.objects.get_or_create(
                content_type=content_type,
                object_id=content_object.id,
                defaults={
                    'total_flags': 0,
                    'unique_flaggers': 0
                }
            )
            
            flagged_content.add_flag(flag)
            
            logger.info(f"Content flagged: {content_object} by {user.username} ({flag_type})")
            
            return {
                'success': True,
                'flag': flag,
                'flagged_content': flagged_content,
                'auto_escalated': flagged_content.auto_escalated
            }
            
        except Exception as e:
            logger.error(f"Error flagging content: {str(e)}")
            return {
                'success': False,
                'error': f'Error submitting flag: {str(e)}',
                'flag': None
            }
    
    @staticmethod
    def is_user_rate_limited(user) -> bool:
        """Check if user has hit rate limits for flagging."""
        # Check for active moderation records that limit flagging
        active_limits = UserModerationRecord.objects.filter(
            user=user,
            action__in=['flag_limit', 'temp_ban', 'perm_ban']
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        if active_limits.exists():
            return True
        
        # Check flag rate (max 10 flags per day for regular users)
        yesterday = timezone.now() - timedelta(days=1)
        recent_flags = Flag.objects.filter(
            flagged_by=user,
            created_at__gte=yesterday
        ).count()
        
        # Higher limits for trusted users
        if hasattr(user, 'profile') and user.profile.tier and user.profile.tier.level >= 3:
            limit = 25  # Higher limit for moderators
        else:
            limit = 10  # Regular user limit
        
        return recent_flags >= limit
    
    @staticmethod
    def get_flagged_content(status: str = None, priority: str = None, 
                          content_type: str = None, limit: int = 50) -> List[FlaggedContent]:
        """Get flagged content for review."""
        queryset = FlaggedContent.objects.select_related('content_type').prefetch_related(
            'content_object'
        )
        
        if status == 'under_review':
            queryset = queryset.filter(is_under_review=True, is_resolved=False)
        elif status == 'resolved':
            queryset = queryset.filter(is_resolved=True)
        elif status == 'open':
            queryset = queryset.filter(is_under_review=False, is_resolved=False)
        
        if content_type:
            queryset = queryset.filter(content_type__model=content_type)
        
        return queryset.order_by('-last_flagged')[:limit]
    
    @staticmethod
    def get_flags_for_content(content_object) -> List[Flag]:
        """Get all flags for a specific piece of content."""
        content_type = ContentType.objects.get_for_model(content_object)
        return Flag.objects.filter(
            content_type=content_type,
            object_id=content_object.id
        ).select_related('flagged_by').order_by('-created_at')
    
    @staticmethod
    def resolve_flag(flag: Flag, resolved_by, notes: str = "", action_taken: str = None):
        """Resolve a flag with optional action."""
        flag.mark_resolved(resolved_by, notes)
        
        # Update flagged content if all flags are resolved
        content_type = ContentType.objects.get_for_model(flag.flagged_object)
        flagged_content = FlaggedContent.objects.get(
            content_type=content_type,
            object_id=flag.object_id
        )
        
        # Check if all flags for this content are resolved/dismissed
        remaining_flags = Flag.objects.filter(
            content_type=content_type,
            object_id=flag.object_id,
            status='open'
        ).count()
        
        if remaining_flags == 0:
            flagged_content.is_resolved = True
            flagged_content.is_under_review = False
            flagged_content.save()
        
        logger.info(f"Flag resolved by {resolved_by.username}: {flag}")
    
    @staticmethod
    def dismiss_flag(flag: Flag, dismissed_by, notes: str = ""):
        """Dismiss a flag as invalid."""
        flag.mark_dismissed(dismissed_by, notes)
        logger.info(f"Flag dismissed by {dismissed_by.username}: {flag}")
    
    @staticmethod
    def get_user_flags(user, status: str = None) -> List[Flag]:
        """Get flags raised by a specific user."""
        queryset = Flag.objects.filter(flagged_by=user).select_related(
            'content_type'
        ).prefetch_related('flagged_object')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_moderation_stats() -> Dict[str, Any]:
        """Get statistics for the moderation dashboard."""
        total_flags = Flag.objects.count()
        open_flags = Flag.objects.filter(status='open').count()
        under_review = Flag.objects.filter(status='under_review').count()
        resolved_flags = Flag.objects.filter(status='resolved').count()
        
        # Get top flagged content types
        content_types = Flag.objects.values(
            'content_type__model'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Get recent flag activity
        recent_flags = Flag.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Get users with most flags raised
        top_flaggers = Flag.objects.values(
            'flagged_by__username'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return {
            'total_flags': total_flags,
            'open_flags': open_flags,
            'under_review': under_review,
            'resolved_flags': resolved_flags,
            'content_types': content_types,
            'recent_flags': recent_flags,
            'top_flaggers': top_flaggers,
            'resolution_rate': (resolved_flags / total_flags * 100) if total_flags > 0 else 0
        }
    
    @staticmethod
    def is_content_flagged(content_object) -> Dict[str, Any]:
        """Check if content is flagged and return flag information."""
        content_type = ContentType.objects.get_for_model(content_object)
        
        try:
            flagged_content = FlaggedContent.objects.get(
                content_type=content_type,
                object_id=content_object.id
            )
            
            return {
                'is_flagged': True,
                'total_flags': flagged_content.total_flags,
                'is_under_review': flagged_content.is_under_review,
                'is_hidden': flagged_content.is_hidden,
                'auto_escalated': flagged_content.auto_escalated
            }
        except FlaggedContent.DoesNotExist:
            return {
                'is_flagged': False,
                'total_flags': 0,
                'is_under_review': False,
                'is_hidden': False,
                'auto_escalated': False
            }


class ModerationService:
    """Service for user moderation actions."""
    
    @staticmethod
    def warn_user(user, moderator, reason: str, related_flag: Flag = None):
        """Issue a warning to a user."""
        record = UserModerationRecord.objects.create(
            user=user,
            action='warning',
            reason=reason,
            moderator=moderator,
            related_flag=related_flag
        )
        
        logger.info(f"User {user.username} warned by {moderator.username}: {reason}")
        return record
    
    @staticmethod
    def temp_ban_user(user, moderator, reason: str, duration_days: int = 7, related_flag: Flag = None):
        """Temporarily ban a user."""
        expires_at = timezone.now() + timedelta(days=duration_days)
        
        record = UserModerationRecord.objects.create(
            user=user,
            action='temp_ban',
            reason=reason,
            moderator=moderator,
            expires_at=expires_at,
            related_flag=related_flag
        )
        
        logger.warning(f"User {user.username} temporarily banned by {moderator.username}: {reason}")
        return record
    
    @staticmethod
    def limit_user_flags(user, moderator, reason: str, duration_days: int = 30, related_flag: Flag = None):
        """Limit a user's ability to submit flags."""
        expires_at = timezone.now() + timedelta(days=duration_days)
        
        record = UserModerationRecord.objects.create(
            user=user,
            action='flag_limit',
            reason=reason,
            moderator=moderator,
            expires_at=expires_at,
            related_flag=related_flag
        )
        
        logger.info(f"User {user.username} flag privileges limited by {moderator.username}: {reason}")
        return record
    
    @staticmethod
    def get_user_moderation_status(user) -> Dict[str, Any]:
        """Get current moderation status for a user."""
        active_records = UserModerationRecord.objects.filter(
            user=user
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).order_by('-created_at')
        
        status = {
            'is_banned': False,
            'flag_limited': False,
            'contrib_limited': False,
            'warnings_count': 0,
            'active_records': list(active_records)
        }
        
        for record in active_records:
            if record.action == 'temp_ban' or record.action == 'perm_ban':
                status['is_banned'] = True
            elif record.action == 'flag_limit':
                status['flag_limited'] = True
            elif record.action == 'contrib_limit':
                status['contrib_limited'] = True
        
        # Count total warnings
        status['warnings_count'] = UserModerationRecord.objects.filter(
            user=user,
            action='warning'
        ).count()
        
        return status
    
    @staticmethod
    def take_content_action(flagged_content, action, moderator, **kwargs):
        """
        Take moderation action on flagged content.
        Actions: 'edit', 'remove', 'reinstate'
        """
        from ..models import Contribution, ActivityLog
        from django.contrib.contenttypes.models import ContentType
        
        if action not in ['edit', 'remove', 'reinstate']:
            return {'success': False, 'error': 'Invalid action'}
        
        content_object = flagged_content.content_object
        
        try:
            if action == 'edit':
                # For contributions, update the value
                if isinstance(content_object, Contribution):
                    new_value = kwargs.get('new_value')
                    old_value = content_object.value
                    
                    if not new_value:
                        return {'success': False, 'error': 'New value is required for edit action'}
                    
                    content_object.value = new_value
                    content_object.save()
                    
                    # Log the edit action
                    ActivityLog.objects.create(
                        user=moderator,
                        activity='moderate_content_edit',
                        action=f'Edited flagged content: {old_value} → {new_value}',
                        council=getattr(content_object, 'council', None),
                        extra={
                            'flagged_content_id': flagged_content.id,
                            'content_type': str(flagged_content.content_type),
                            'object_id': flagged_content.object_id,
                            'old_value': old_value,
                            'new_value': new_value
                        }
                    )
                    
                    # Mark flags as resolved
                    flagged_content.status = 'resolved'
                    flagged_content.resolved_at = timezone.now()
                    flagged_content.resolved_by = moderator
                    flagged_content.resolution_notes = f"Content edited by moderator: {old_value} → {new_value}"
                    flagged_content.save()
                    
                    # Resolve all individual flags
                    for flag in flagged_content.flags.filter(status='open'):
                        flag.status = 'resolved'
                        flag.resolved_at = timezone.now()
                        flag.resolved_by = moderator
                        flag.save()
                    
                    return {'success': True, 'message': 'Content edited successfully'}
                
            elif action == 'remove':
                # Remove/nullify the content and add back to contribution queue
                if isinstance(content_object, Contribution):
                    # Mark the contribution as removed
                    content_object.status = 'removed'
                    content_object.save()
                    
                    # Clear the actual data field if it exists
                    if hasattr(content_object, 'council') and hasattr(content_object, 'field'):
                        # This would need to be implemented based on your data model
                        # For now, we'll just mark it for re-contribution
                        pass
                    
                    # Log the removal action
                    ActivityLog.objects.create(
                        user=moderator,
                        activity='moderate_content_remove',
                        action=f'Removed flagged content: {content_object.value}',
                        council=getattr(content_object, 'council', None),
                        extra={
                            'flagged_content_id': flagged_content.id,
                            'content_type': str(flagged_content.content_type),
                            'object_id': flagged_content.object_id,
                            'removed_value': content_object.value
                        }
                    )
                    
                    # Mark flags as resolved
                    flagged_content.status = 'resolved'
                    flagged_content.resolved_at = timezone.now()
                    flagged_content.resolved_by = moderator
                    flagged_content.resolution_notes = f"Content removed by moderator and returned to contribution queue"
                    flagged_content.save()
                    
                    # Resolve all individual flags
                    for flag in flagged_content.flags.filter(status='open'):
                        flag.status = 'resolved'
                        flag.resolved_at = timezone.now()
                        flag.resolved_by = moderator
                        flag.save()
                    
                    return {'success': True, 'message': 'Content removed and returned to contribution queue'}
                
            elif action == 'reinstate':
                # Clear flags and keep content as-is
                # Log the reinstatement action
                ActivityLog.objects.create(
                    user=moderator,
                    activity='moderate_content_reinstate',
                    action=f'Reinstated flagged content as valid',
                    council=getattr(content_object, 'council', None),
                    extra={
                        'flagged_content_id': flagged_content.id,
                        'content_type': str(flagged_content.content_type),
                        'object_id': flagged_content.object_id,
                        'reinstated_value': getattr(content_object, 'value', str(content_object))
                    }
                )
                
                # Mark flags as dismissed (content is valid)
                flagged_content.status = 'dismissed'
                flagged_content.resolved_at = timezone.now()
                flagged_content.resolved_by = moderator
                flagged_content.resolution_notes = f"Content reinstated as valid by moderator"
                flagged_content.save()
                
                # Dismiss all individual flags
                for flag in flagged_content.flags.filter(status='open'):
                    flag.status = 'dismissed'
                    flag.resolved_at = timezone.now()
                    flag.resolved_by = moderator
                    flag.save()
                
                return {'success': True, 'message': 'Content reinstated successfully'}
            
        except Exception as e:
            logger.error(f"Error taking content action {action}: {str(e)}")
            return {'success': False, 'error': f'Error executing {action} action'}
    
    @staticmethod
    def take_user_action(user, action, moderator, **kwargs):
        """
        Take moderation action on a flagged user.
        Actions: 'release', 'restrict', 'suspend', 'ban'
        """
        from ..models import UserModerationRecord, ActivityLog
        from django.contrib.contenttypes.models import ContentType
        
        if action not in ['release', 'restrict', 'suspend', 'ban']:
            return {'success': False, 'error': 'Invalid action'}
        
        try:
            if action == 'release':
                # Clear any existing restrictions and flags against the user
                UserModerationRecord.objects.filter(user=user, is_active=True).update(is_active=False)
                
                # Clear user flags (if they exist)
                user_content_type = ContentType.objects.get_for_model(user)
                flagged_user_content = FlaggedContent.objects.filter(
                    content_type=user_content_type,
                    object_id=user.id,
                    status='open'
                )
                
                for flagged_content in flagged_user_content:
                    flagged_content.status = 'dismissed'
                    flagged_content.resolved_at = timezone.now()
                    flagged_content.resolved_by = moderator
                    flagged_content.resolution_notes = "User released by moderator"
                    flagged_content.save()
                    
                    # Dismiss individual flags
                    for flag in flagged_content.flags.filter(status='open'):
                        flag.status = 'dismissed'
                        flag.resolved_at = timezone.now()
                        flag.resolved_by = moderator
                        flag.save()
                
                # Log the action
                ActivityLog.objects.create(
                    user=moderator,
                    activity='moderate_user_release',
                    action=f'Released user {user.username} from restrictions',
                    extra={
                        'target_user_id': user.id,
                        'target_username': user.username
                    }
                )
                
                return {'success': True, 'message': f'User {user.username} released successfully'}
            
            elif action == 'restrict':
                # Apply restrictions to user activities
                restriction_type = kwargs.get('restriction_type', 'contribution_limit')
                duration_days = kwargs.get('duration_days', 7)
                notes = kwargs.get('notes', '')
                
                # Create moderation record
                UserModerationRecord.objects.create(
                    user=user,
                    moderator=moderator,
                    action='restrict',
                    reason=f"User restricted: {restriction_type}",
                    duration_days=duration_days,
                    notes=notes,
                    extra_data={
                        'restriction_type': restriction_type,
                        'original_flags': FlaggingService._get_user_flag_summary(user)
                    }
                )
                
                # Log the action
                ActivityLog.objects.create(
                    user=moderator,
                    activity='moderate_user_restrict',
                    action=f'Restricted user {user.username} for {duration_days} days',
                    extra={
                        'target_user_id': user.id,
                        'target_username': user.username,
                        'restriction_type': restriction_type,
                        'duration_days': duration_days
                    }
                )
                
                return {'success': True, 'message': f'User {user.username} restricted for {duration_days} days'}
            
            elif action in ['suspend', 'ban']:
                # Suspend or ban user
                duration_days = kwargs.get('duration_days', 30 if action == 'suspend' else None)
                reason = kwargs.get('reason', '')
                notes = kwargs.get('notes', '')
                
                # Create moderation record
                UserModerationRecord.objects.create(
                    user=user,
                    moderator=moderator,
                    action=action,
                    reason=reason,
                    duration_days=duration_days,
                    notes=notes,
                    extra_data={
                        'original_flags': FlaggingService._get_user_flag_summary(user)
                    }
                )
                
                # Deactivate user account if banned permanently
                if action == 'ban' and duration_days is None:
                    user.is_active = False
                    user.save()
                
                # Log the action
                ActivityLog.objects.create(
                    user=moderator,
                    activity=f'moderate_user_{action}',
                    action=f'{action.title()}ed user {user.username}' + (f' for {duration_days} days' if duration_days else ' permanently'),
                    extra={
                        'target_user_id': user.id,
                        'target_username': user.username,
                        'duration_days': duration_days,
                        'reason': reason
                    }
                )
                
                action_text = f"{action}ed" + (f" for {duration_days} days" if duration_days else " permanently")
                return {'success': True, 'message': f'User {user.username} {action_text}'}
            
        except Exception as e:
            logger.error(f"Error taking user action {action}: {str(e)}")
            return {'success': False, 'error': f'Error executing {action} action'}
    
    @staticmethod
    def _get_user_flag_summary(user):
        """Get a summary of flags against a user for logging purposes."""
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Count
        
        user_content_type = ContentType.objects.get_for_model(user)
        user_flags = Flag.objects.filter(
            content_type=user_content_type,
            object_id=user.id
        ).values('flag_type').annotate(count=Count('id'))
        
        return {flag['flag_type']: flag['count'] for flag in user_flags}
