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
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import json
import logging

from council_finance.models import (
    Flag, FlaggedContent, UserProfile, Council, Contribution
)
from council_finance.services.flagging_services import FlaggingService

# Import utility functions we'll need
from .general import log_activity

logger = logging.getLogger(__name__)


@login_required
@require_POST
def flag_content(request):
    """Handle content flagging requests."""
    try:
        # Handle both JSON and form data submissions
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
            content_type = data.get('content_type')
            content_id = data.get('content_id')
            flag_type = data.get('flag_type', '')
            description = data.get('description', '').strip()
            priority = data.get('priority', 'medium')
            field_name = data.get('field_name', '')
        else:
            # Handle form data (multipart/form-data or application/x-www-form-urlencoded)
            content_type = request.POST.get('content_type')
            content_id = request.POST.get('object_id')  # Form sends 'object_id', not 'content_id'
            flag_type = request.POST.get('flag_type', '')
            description = request.POST.get('description', '').strip()
            priority = request.POST.get('priority', 'medium')
            field_name = request.POST.get('data_field', '')  # Form sends 'data_field', not 'field_name'
        
        if not all([content_type, content_id, flag_type, description]):
            return JsonResponse({
                'error': 'Content type, content ID, flag type, and description are required'
            }, status=400)
        
        # Map content types to actual objects/data for flagging
        # For all financial data flagging, we'll use the Council as the content object
        # and store specific field/counter information in the flag context
        try:
            council = Council.objects.get(slug=content_id)
            content_object = council
        except Council.DoesNotExist:
            return JsonResponse({'error': 'Council not found'}, status=404)
        
        flag_context = {
            'council_slug': content_id
        }
        
        if content_type == 'financial_counter':
            # For financial counters, store counter information
            flag_context.update({
                'flagged_content_type': 'financial_counter',
                'counter_slug': content_id,
                'field_name': field_name,
                'content_description': f'Financial counter: {content_id}'
            })
            
        elif content_type == 'council_financial_data':
            # For general council financial data
            flag_context.update({
                'flagged_content_type': 'council_financial_data',
                'data_type': 'financial_overview'
            })
            # Add field information if provided
            if field_name:
                flag_context['field_name'] = field_name
                
        elif content_type == 'council_characteristic':
            # For council characteristics/meta data
            flag_context.update({
                'flagged_content_type': 'council_characteristic',
                'data_type': 'characteristic',
                'field_name': field_name
            })
                
        else:
            return JsonResponse({'error': 'Unsupported content type'}, status=400)
        
        # Create the flag
        try:
            # Check if user has already flagged this specific content
            # For duplicate prevention, we need to consider both the council and the specific field/counter
            content_key = f"{flag_context.get('flagged_content_type', 'general')}:{flag_context.get('field_name', 'general')}"
            
            existing_flag = Flag.objects.filter(
                flagged_by=request.user,
                content_type=ContentType.objects.get_for_model(content_object),
                object_id=content_object.id,
                description__contains=content_key  # Check if we've already flagged this specific field/counter
            ).first()
            
            if existing_flag:
                return JsonResponse({
                    'error': 'You have already flagged this content'
                }, status=400)
            
            # Create new flag
            flag_data = {
                'flagged_by': request.user,
                'flag_type': flag_type,
                'priority': priority,
                'description': description,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'content_type': ContentType.objects.get_for_model(content_object),
                'object_id': content_object.id
            }
            
            flag = Flag.objects.create(**flag_data)
            
            # Store additional context in the flag description
            if flag_context:
                context_str = "; ".join([f"{k}: {v}" for k, v in flag_context.items()])
                flag.description = f"{description}\n\nContext: {context_str}\nContent Key: {content_key}"
                flag.save()
            
            # Log the activity
            log_activity(
                request,
                activity=f"Content flagged: {content_type}",
                details=f"Flag ID: {flag.id}, Content: {content_id}, Reason: {flag_type}"
            )
            
            # Send email notification to admins
            send_flag_notification_email(flag, flag_context)
            
            return JsonResponse({
                'success': True,
                'message': 'Content flagged successfully. Thank you for helping improve data quality.',
                'flag_id': flag.id
            })
            
        except Exception as e:
            logger.error(f"Error creating flag: {str(e)}")
            return JsonResponse({
                'error': 'Failed to create flag. Please try again.'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in flag_content: {str(e)}")
        return JsonResponse({'error': 'An error occurred while processing your request'}, status=500)

def send_flag_notification_email(flag, context=None):
    """Send email notification to admins when content is flagged."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from django.contrib.auth.models import User
        
        # Get admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        admin_emails = [user.email for user in admin_users if user.email]
        
        if not admin_emails:
            return
        
        # Prepare email content
        subject = f"[CFC] New Content Flag: {flag.get_flag_type_display()}"
        
        context_info = ""
        if context:
            context_info = "\n\nAdditional Context:\n" + "\n".join([f"- {k}: {v}" for k, v in context.items()])
        
        message = f"""
A user has flagged content for review on Council Finance Counters.

Flag Details:
- Flag Type: {flag.get_flag_type_display()}
- Priority: {flag.get_priority_display()}
- Flagged by: {flag.flagged_by.username} ({flag.flagged_by.email})
- Date: {flag.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Description:
{flag.description}
{context_info}

Please review this flag in the admin interface:
{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/moderation/flagged-content/

---
This is an automated notification from Council Finance Counters.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@councilfinancecounters.com'),
            recipient_list=admin_emails,
            fail_silently=True  # Don't break the flagging process if email fails
        )
        
    except Exception as e:
        logger.error(f"Failed to send flag notification email: {str(e)}")


@login_required
def flagged_content_list(request):
    """Display list of flagged content for moderators."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.tier.level < 4:  # MANAGEMENT_TIER
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    content_type_filter = request.GET.get('content_type', '')
    search_query = request.GET.get('search', '')
    
    # Build base queryset for flags
    flags_qs = Flag.objects.all().select_related('flagged_by', 'content_type').order_by('-created_at')
    
    # Apply filters
    if status_filter:
        flags_qs = flags_qs.filter(status=status_filter)
    
    if priority_filter:
        flags_qs = flags_qs.filter(priority=priority_filter)
    
    if content_type_filter:
        if content_type_filter == 'financial_counter':
            # For virtual financial counter flags
            flags_qs = flags_qs.filter(content_type=None)
        else:
            # For actual model-based flags
            try:
                ct = ContentType.objects.get(model=content_type_filter)
                flags_qs = flags_qs.filter(content_type=ct)
            except ContentType.DoesNotExist:
                pass
    
    if search_query:
        flags_qs = flags_qs.filter(description__icontains=search_query)
    
    # Get statistics
    all_flags = Flag.objects.all()
    stats = {
        'total_count': all_flags.count(),
        'open_count': all_flags.filter(status='open').count(),
        'resolved_count': all_flags.filter(status='resolved').count(),
        'critical_count': all_flags.filter(priority='critical').count(),
    }
    
    # Paginate results
    page_number = request.GET.get('page', 1)
    per_page = 25  # You can make this configurable if desired
    paginator = Paginator(flags_qs, per_page)
    page_obj = paginator.get_page(page_number)

    # Convert flags to flagged content format for template compatibility
    flagged_content = []
    for flag in page_obj.object_list:
        # Create a pseudo-flagged content object
        flagged_item = type('FlaggedContent', (), {
            'id': flag.id,
            'status': flag.status,
            'priority': flag.priority,
            'first_flagged': flag.created_at,
            'last_flagged': flag.resolved_at or flag.created_at,
            'flag_count': 1,  # Individual flags, not aggregated
            'is_under_review': flag.status == 'under_review',
            'content_type': flag.content_type or type('VirtualContentType', (), {
                'model': 'financial_counter' if flag.content_type is None else flag.content_type.model
            })(),
            'content_object': flag.flagged_object if flag.flagged_object else f"Financial Counter (ID: {flag.object_id})",
            'flags': type('FlagQuerySet', (), {
                'first': lambda: flag,
                'count': lambda: 1,
                'all': lambda: [flag]
            })()
        })()
        
        flagged_content.append(flagged_item)
    
    # Paginate results
    paginator = Paginator(flagged_content, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'flagged_content': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'content_type_filter': content_type_filter,
        'search_query': search_query,
        **stats
    }
    
    return render(request, 'council_finance/flagged_content.html', context)


@login_required
@require_POST
def resolve_flag(request, flag_id):
    """Resolve a content flag."""
    # Check if user has moderation permissions
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.tier.level < 4:  # MANAGEMENT_TIER
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
    if profile.tier.level < 4:  # MANAGEMENT_TIER
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
    if profile.tier.level < 4:  # MANAGEMENT_TIER
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
    # Check if user has moderation permissions    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.tier.level < 4:  # MANAGEMENT_TIER
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    flagging_service = FlaggingService()
    
    # Get moderation statistics
    stats = {
        'pending_flags': flagging_service.get_pending_count(),
        'total_flags': Flag.objects.count(),        'resolved_today': flagging_service.get_resolved_today_count(),
        'active_moderators': UserProfile.objects.filter(
            tier__level__gte=4,
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
