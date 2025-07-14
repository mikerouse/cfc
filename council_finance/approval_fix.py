"""
Quick fix for the contribution approval issue.
This creates a direct approval endpoint that uses the new V2 system.
"""

from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
import logging

from council_finance.models import Contribution
from council_finance.views import _apply_contribution_v2, log_activity, create_notification

logger = logging.getLogger(__name__)


@require_POST
@login_required
def approve_contribution_direct(request, contribution_id):
    """
    Direct approval of contributions using the new V2 system.
    This bypasses the problematic review_contribution function.
    """
    
    # Check permissions
    if not request.user.is_superuser and request.user.profile.tier.level < 3:
        return JsonResponse({
            'success': False,
            'error': 'Permission denied. You need moderator privileges.'
        })
    
    try:
        contrib = get_object_or_404(Contribution, pk=contribution_id, status='pending')
        
        # Apply the contribution using the new system
        _apply_contribution_v2(contrib, request.user, request)
        
        # Mark as approved
        contrib.status = "approved"
        contrib.save()
        
        # Log activity
        log_activity(
            request,
            council=contrib.council,
            activity="review_contribution",
            log_type="user",
            action=f"id={contribution_id}",
            response="approved",
            extra={"value": contrib.value},
        )
        
        # Award points
        points = 3 if contrib.field.category == "characteristic" else 2
        profile = contrib.user.profile
        profile.points += points
        profile.save()
        
        # Create notification
        link = reverse("council_detail", args=[contrib.council.slug])
        message = (
            f"Your contribution to <a href='{link}'>{contrib.council.name}</a> "
            f"(Field: {contrib.field.name}) was accepted. You also earned {points} "
            f"points for this. Thank you!"
        )
        create_notification(contrib.user, message)
        
        messages.success(request, f"Contribution approved successfully!")
        
        return JsonResponse({
            'success': True,
            'message': f'Contribution for {contrib.field.name} approved successfully!',
            'contribution_id': contribution_id
        })
        
    except Exception as e:
        logger.error(f"Error approving contribution {contribution_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error approving contribution: {str(e)}'
        })


@require_POST
@login_required  
def reject_contribution_direct(request, contribution_id):
    """Direct rejection of contributions."""
    
    # Check permissions
    if not request.user.is_superuser and request.user.profile.tier.level < 3:
        return JsonResponse({
            'success': False,
            'error': 'Permission denied. You need moderator privileges.'
        })
    
    try:
        contrib = get_object_or_404(Contribution, pk=contribution_id, status='pending')
        
        reason = request.POST.get("reason", "No reason provided")
        contrib.status = "rejected" 
        contrib.save()
        
        # Log activity
        log_activity(
            request,
            council=contrib.council,
            activity="review_contribution",
            log_type="user",
            action=f"id={contribution_id}",
            response="rejected",
            extra={"value": contrib.value, "reason": reason},
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Contribution for {contrib.field.name} rejected.',
            'contribution_id': contribution_id
        })
        
    except Exception as e:
        logger.error(f"Error rejecting contribution {contribution_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error rejecting contribution: {str(e)}'
        })
