"""
Site Feedback Views
Handles the feedback form for pre-alpha testing and ongoing user feedback.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db import models

from council_finance.models import SiteFeedback

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_client_info(request):
    """Extract client browser and device information."""
    return {
        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
        'page_url': request.META.get('HTTP_REFERER', request.build_absolute_uri())[:500],
        'ip_address': get_client_ip(request)
    }


@require_http_methods(["GET", "POST"])
@csrf_protect
def feedback_form(request):
    """
    Display and handle the site feedback form.
    
    Supports both HTML form submission and AJAX requests.
    """
    
    if request.method == 'POST':
        return handle_feedback_submission(request)
    
    # GET request - show the form
    context = {
        'feedback_types': SiteFeedback.FEEDBACK_TYPES,
        'severity_levels': SiteFeedback.SEVERITY_LEVELS,
        'current_page': request.GET.get('page', ''),
        'show_debug_info': settings.DEBUG,
    }
    
    return render(request, 'council_finance/feedback_form.html', context)


def handle_feedback_submission(request):
    """Process feedback form submission."""
    
    try:
        # Extract form data
        feedback_data = {
            'feedback_type': request.POST.get('feedback_type', 'general'),
            'title': request.POST.get('title', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'severity': request.POST.get('severity', 'medium'),
            'steps_to_reproduce': request.POST.get('steps_to_reproduce', '').strip(),
            'expected_behaviour': request.POST.get('expected_behaviour', '').strip(),
            'actual_behaviour': request.POST.get('actual_behaviour', '').strip(),
            'contact_name': request.POST.get('contact_name', '').strip(),
            'contact_email': request.POST.get('contact_email', '').strip(),
            'screen_resolution': request.POST.get('screen_resolution', '').strip()[:50],  # Truncate to field length
        }
        
        # Log field lengths for debugging if needed
        logger.debug(f"Screen resolution: '{feedback_data['screen_resolution']}' (length: {len(feedback_data['screen_resolution'])})")
        
        # Add client information
        client_info = get_client_info(request)
        feedback_data.update(client_info)
        
        # Set user if authenticated
        if request.user.is_authenticated:
            feedback_data['user'] = request.user
        
        # Validate required fields
        if not feedback_data['title']:
            raise ValidationError("Title is required")
        
        if not feedback_data['description']:
            raise ValidationError("Description is required")
        
        if len(feedback_data['description']) < 10:
            raise ValidationError("Please provide more details in the description")
        
        # Create feedback record
        feedback = SiteFeedback.objects.create(**feedback_data)
        
        # Log success
        logger.info(f"Feedback submitted: {feedback.id} - {feedback.feedback_type} - {feedback.title}")
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Thank you for your feedback! We\'ll review it shortly.',
                'feedback_id': feedback.id
            })
        
        # Handle regular form submission
        messages.success(
            request,
            f'Thank you for your feedback! We\'ll review your {feedback.get_feedback_type_display().lower()} shortly. '
            f'Reference ID: {feedback.id}'
        )
        
        return redirect('feedback_form')
        
    except ValidationError as e:
        error_message = str(e)
        logger.warning(f"Feedback validation error: {error_message}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=400)
        
        messages.error(request, error_message)
        return redirect('feedback_form')
        
    except Exception as e:
        error_message = "Sorry, there was an error submitting your feedback. Please try again."
        logger.error(f"Feedback submission error: {e}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=500)
        
        messages.error(request, error_message)
        return redirect('feedback_form')


@require_http_methods(["GET"])
def feedback_thank_you(request):
    """Thank you page after feedback submission."""
    
    feedback_id = request.GET.get('id')
    feedback = None
    
    if feedback_id:
        try:
            feedback = SiteFeedback.objects.get(id=feedback_id)
            # Only show feedback details to the submitter or staff
            if not (request.user.is_authenticated and 
                   (request.user == feedback.user or request.user.is_staff)):
                feedback = None
        except SiteFeedback.DoesNotExist:
            pass
    
    context = {
        'feedback': feedback,
        'show_back_link': True,
    }
    
    return render(request, 'council_finance/feedback_thank_you.html', context)


def get_active_announcements(request):
    """Get currently active site announcements for display."""
    
    try:
        from council_finance.models import SiteAnnouncement
        
        now = timezone.now()
        announcements = SiteAnnouncement.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        )
        
        # Filter by page context if needed
        if not request.path == '/':
            announcements = announcements.filter(show_on_all_pages=True)
        
        # Increment view counts
        for announcement in announcements:
            announcement.increment_views()
        
        return announcements
        
    except Exception as e:
        logger.error(f"Error loading announcements: {e}")
        return []


# Context processor to make announcements available in all templates
def announcements_context_processor(request):
    """Add active announcements to template context."""
    return {
        'active_announcements': get_active_announcements(request),
        'show_feedback_link': True,  # Always show feedback link during pre-alpha
    }