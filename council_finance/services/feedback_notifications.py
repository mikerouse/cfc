"""
Feedback Email Notification System
Sends email alerts when new feedback is submitted.
"""

import logging
import os
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_feedback_notification(feedback):
    """
    Send email notification for new feedback submission.
    
    Args:
        feedback: SiteFeedback instance
    """
    
    try:
        # Get email address from environment
        recipient_email = os.getenv('ERROR_ALERTS_EMAIL_ADDRESS')
        
        if not recipient_email:
            logger.warning("ERROR_ALERTS_EMAIL_ADDRESS not configured, skipping feedback email notification")
            return False
        
        # Determine email urgency based on feedback type and severity
        is_urgent = feedback.severity in ['critical', 'high'] or feedback.feedback_type == 'bug'
        
        # Create subject line
        urgency_prefix = "[URGENT]" if is_urgent else "[FEEDBACK]"
        subject = f"{urgency_prefix} New {feedback.get_feedback_type_display()}: {feedback.title}"
        
        # Email content
        context = {
            'feedback': feedback,
            'is_urgent': is_urgent,
            'priority_score': round(feedback.get_priority_score(), 2),
            'dashboard_url': f"{get_site_url()}/system-events/events/?source=site_feedback",
            'feedback_detail_url': f"{get_site_url()}/admin/council_finance/sitefeedback/{feedback.id}/change/",
            'site_name': 'Council Finance Counters'
        }
        
        # Create both HTML and plain text versions
        html_message = render_to_string('council_finance/emails/feedback_notification.html', context)
        plain_message = render_to_string('council_finance/emails/feedback_notification.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Feedback notification email sent for feedback #{feedback.id} to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send feedback notification email for feedback #{feedback.id}: {e}")
        return False


def send_feedback_digest():
    """
    Send daily digest of unresolved feedback.
    Can be called from a cron job or management command.
    """
    
    try:
        from council_finance.models import SiteFeedback
        
        recipient_email = os.getenv('ERROR_ALERTS_EMAIL_ADDRESS')
        if not recipient_email:
            return False
        
        # Get unresolved feedback from last 24 hours and older unresolved items
        from datetime import timedelta
        
        last_24h = timezone.now() - timedelta(hours=24)
        
        new_feedback = SiteFeedback.objects.filter(
            submitted_at__gte=last_24h,
            status__in=['new', 'acknowledged']
        ).order_by('-submitted_at')
        
        older_unresolved = SiteFeedback.objects.filter(
            submitted_at__lt=last_24h,
            status__in=['new', 'acknowledged', 'in_progress']
        ).order_by('-submitted_at')[:10]  # Limit to most recent 10
        
        # Only send digest if there's something to report
        if not new_feedback.exists() and not older_unresolved.exists():
            logger.info("No unresolved feedback to report in daily digest")
            return True
        
        context = {
            'new_feedback': new_feedback,
            'older_unresolved': older_unresolved,
            'total_new': new_feedback.count(),
            'total_older': older_unresolved.count(),
            'dashboard_url': f"{get_site_url()}/system-events/events/?source=site_feedback",
            'site_name': 'Council Finance Counters',
            'date': timezone.now().date()
        }
        
        subject = f"[DIGEST] Daily Feedback Summary - {context['total_new']} new, {context['total_older']} pending"
        
        html_message = render_to_string('council_finance/emails/feedback_digest.html', context)
        plain_message = render_to_string('council_finance/emails/feedback_digest.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Feedback digest email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send feedback digest email: {e}")
        return False


def get_site_url():
    """Get the site base URL for email links."""
    # In production, this should be set from settings
    if hasattr(settings, 'SITE_URL'):
        return settings.SITE_URL
    
    # Development fallback
    return "http://127.0.0.1:8000"