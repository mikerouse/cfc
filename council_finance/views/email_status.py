"""
API endpoint for checking email change rate limiting status
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from council_finance.services.email_security import email_security_service


@login_required
def email_change_status(request):
    """Get current email change rate limiting status for the user."""
    
    # Check current rate limits
    ip_status = email_security_service.check_ip_rate_limit(request)
    user_status = email_security_service.check_user_rate_limit(request.user)
    
    # Get profile status
    profile = getattr(request.user, 'profile', None)
    profile_can_send = profile.can_send_confirmation() if profile else True
    
    # Calculate next available time
    next_available = None
    if not ip_status['allowed']:
        next_available = ip_status['reset_in_seconds']
    elif not user_status['allowed']:
        next_available = user_status['reset_in_seconds']
    elif not profile_can_send and profile:
        # Calculate time until profile rate limit resets
        import datetime
        if profile.last_confirmation_sent:
            time_since_last = datetime.datetime.now() - profile.last_confirmation_sent
            if time_since_last.total_seconds() < 300:  # 5 minutes
                next_available = 300 - int(time_since_last.total_seconds())
    
    return JsonResponse({
        'can_send': ip_status['allowed'] and user_status['allowed'] and profile_can_send,
        'rate_limits': {
            'ip': {
                'allowed': ip_status['allowed'],
                'attempts': ip_status['attempts'],
                'max_attempts': ip_status['max_attempts'],
                'remaining': ip_status.get('remaining', 0),
                'reset_in_seconds': ip_status.get('reset_in_seconds', 0)
            },
            'user': {
                'allowed': user_status['allowed'],
                'attempts': user_status['attempts'],
                'max_attempts': user_status['max_attempts'],
                'remaining': user_status.get('remaining', 0),
                'reset_in_seconds': user_status.get('reset_in_seconds', 0)
            },
            'profile': {
                'allowed': profile_can_send,
                'last_sent': profile.last_confirmation_sent.isoformat() if profile and profile.last_confirmation_sent else None,
                'attempts_today': profile.confirmation_attempts if profile else 0
            }
        },
        'next_available_in_seconds': next_available,
        'pending_email': profile.pending_email if profile else None,
        'current_email': request.user.email
    })
