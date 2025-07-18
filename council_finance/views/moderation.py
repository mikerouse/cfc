"""
Moderation and flagging views for Council Finance Counters.
This module handles content flagging, moderation panels, and content management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
import json

from council_finance.models import (
    Flag, FlaggedContent, UserProfile, Council, Contribution
)
from council_finance.services.flagging_services import FlaggingService

# Import utility functions we'll need
from .general import log_activity


@login_required
@require_POST
def flag_content(request):
    """Handle content flagging requests."""
    try:
        data = json.loads(request.body)
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        reason = data.get('reason', '').strip()
        
        if not all([content_type, content_id, reason]):
            return JsonResponse({
                'error': 'Content type, content ID, and reason are required'
            }, status=400)
        
        # Use the flagging service
        flagging_service = FlaggingService()
        
        try:
            flag = flagging_service.flag_content(
                user=request.user,
                content_type=content_type,
                content_id=content_id,
                reason=reason
            )
            
            log_activity(
                request,
                activity=f"Content flagged: {content_type} #{content_id}",
                details=f"Reason: {reason}"
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Content flagged successfully. Thank you for helping keep our community safe.',
                'flag_id': flag.id
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to flag content: {str(e)}'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def flagged_content_list(request):
    """Display list of flagged content for moderators."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.trust_tier < 4:  # MANAGEMENT_TIER
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    flagging_service = FlaggingService()
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')
    content_type_filter = request.GET.get('content_type', '')
    
    # Get flagged content
    flagged_items = flagging_service.get_flagged_content(
        status=status_filter,
        content_type=content_type_filter
    )
    
    # Paginate results
    paginator = Paginator(flagged_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'content_type_filter': content_type_filter,
        'total_pending': flagging_service.get_pending_count(),
    }
    
    return render(request, 'moderation/flagged_content_list.html', context)


@login_required
@require_POST
def resolve_flag(request, flag_id):
    """Resolve a content flag."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.trust_tier < 4:  # MANAGEMENT_TIER
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        flag = get_object_or_404(Flag, id=flag_id)
        action = request.POST.get('action')
        moderator_notes = request.POST.get('notes', '').strip()
        
        if action not in ['approve', 'reject']:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        flagging_service = FlaggingService()
        
        if action == 'approve':
            flagging_service.approve_flag(flag, request.user, moderator_notes)
            message = 'Flag approved and appropriate action taken.'
        else:
            flagging_service.reject_flag(flag, request.user, moderator_notes)
            message = 'Flag rejected.'
        
        log_activity(
            request,
            activity=f"Flag {action}d: {flag.content_type} #{flag.content_id}",
            details=f"Moderator notes: {moderator_notes}"
        )
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def take_content_action(request, flagged_content_id):
    """Take action on flagged content."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.trust_tier < 4:  # MANAGEMENT_TIER
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        flagged_content = get_object_or_404(FlaggedContent, id=flagged_content_id)
        action = request.POST.get('action')
        notes = request.POST.get('notes', '').strip()
        
        valid_actions = ['hide', 'delete', 'edit', 'no_action']
        if action not in valid_actions:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        flagging_service = FlaggingService()
        
        result = flagging_service.take_content_action(
            flagged_content=flagged_content,
            action=action,
            moderator=request.user,
            notes=notes
        )
        
        log_activity(
            request,
            activity=f"Content action taken: {action}",
            details=f"Content: {flagged_content.content_type} #{flagged_content.content_id}, Notes: {notes}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Action "{action}" applied successfully.',
            'action_taken': action
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def take_user_action(request, user_id):
    """Take moderation action on a user."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.trust_tier < 4:  # MANAGEMENT_TIER
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        target_user = get_object_or_404(UserProfile, user_id=user_id)
        action = request.POST.get('action')
        notes = request.POST.get('notes', '').strip()
        duration = request.POST.get('duration', '')
        
        valid_actions = ['warn', 'suspend', 'ban', 'reduce_trust']
        if action not in valid_actions:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        flagging_service = FlaggingService()
        
        result = flagging_service.take_user_action(
            user=target_user.user,
            action=action,
            moderator=request.user,
            notes=notes,
            duration=duration
        )
        
        log_activity(
            request,
            activity=f"User action taken: {action}",
            details=f"User: {target_user.user.username}, Notes: {notes}, Duration: {duration}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Action "{action}" applied to user successfully.',
            'action_taken': action
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def my_flags(request):
    """Display flags created by the current user."""
    flags = Flag.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(flags, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_flags': flags.count(),
    }
    
    return render(request, 'moderation/my_flags.html', context)


@login_required
def moderator_panel(request):
    """Main moderator dashboard."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.trust_tier < 4:  # MANAGEMENT_TIER
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    flagging_service = FlaggingService()
    
    # Get moderation statistics
    stats = {
        'pending_flags': flagging_service.get_pending_count(),
        'total_flags': Flag.objects.count(),
        'resolved_today': flagging_service.get_resolved_today_count(),
        'active_moderators': UserProfile.objects.filter(
            trust_tier__gte=4,
            user__is_active=True
        ).count(),
    }
    
    # Get recent flagged content
    recent_flags = Flag.objects.filter(
        status='pending'
    ).order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_flags': recent_flags,
    }
    
    return render(request, 'moderation/moderator_panel.html', context)
