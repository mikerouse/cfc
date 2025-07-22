"""
Authentication and user management views for Council Finance Counters.
This module handles user registration, login, profile management, and notifications.
"""

import hashlib
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core import signing
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.conf import settings

from council_finance.models import UserProfile, PendingProfileChange, Council, TrustTier
from council_finance.forms import (
    SignUpForm, ProfileExtraForm, ProfileBasicForm, 
    ProfileAdditionalForm, ProfileCustomizationForm, ProfileNotificationForm
)
from council_finance.emails import send_email
from council_finance.notifications import create_notification
from council_finance.services.email_confirmation import (
    email_confirmation_service,
    send_confirmation_email,
    send_reconfirmation_email,
    send_email_change_confirmation,
    confirm_email_token,
)

# Import utility functions we'll need
from .general import log_activity

logger = logging.getLogger(__name__)


def signup_view(request):
    """Handle user registration."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # UserProfile is automatically created by signals.py
            # Get the profile to access the confirmation token
            profile = user.profile
            
            # Send confirmation email
            try:
                send_confirmation_email(user, request)
                messages.success(
                    request,
                    'Account created successfully! Please check your email to confirm your account.'
                )
                log_activity(
                    request,
                    activity=f"New user registered: {user.username}",
                    details=f"Email: {user.email}"
                )
            except Exception as e:
                messages.warning(
                    request,
                    'Account created but there was an issue sending the confirmation email. '
                    'Please try to resend it from your profile.'
                )
                log_activity(
                    request,
                    activity=f"Failed to send confirmation email to {user.username}",
                    details=str(e)
                )
            
            return redirect('login')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})


def confirm_email(request, token):
    """Handle email confirmation links using new confirmation service."""
    result = confirm_email_token(token, request)
    
    if result['success']:
        messages.success(request, result['message'])
        
        # Auto-login user if not already logged in (for initial confirmations)
        if not request.user.is_authenticated and result['confirmation_type'] == 'initial':
            login(request, result['user'])
            return redirect('profile')
        elif result['confirmation_type'] == 'email_change':
            return redirect('profile')
        else:
            return redirect('profile' if request.user.is_authenticated else 'home')
    else:
        messages.error(request, result['message'])
        return redirect('profile' if request.user.is_authenticated else 'login')
    
    return redirect('home')


def confirm_profile_change(request, token):
    """Handle profile change confirmation links."""
    result = confirm_email_token(token, request)
    
    if result['success']:
        messages.success(request, result['message'])
    else:
        messages.error(request, result['message'])
    
    return redirect('profile' if request.user.is_authenticated else 'login')


@login_required
def cancel_email_change(request):
    """Cancel pending email change."""
    if request.method == 'POST':
        success = email_confirmation_service.cancel_pending_email_change(request.user)
        if success:
            messages.success(request, 'Email change cancelled successfully.')
        else:
            messages.error(request, 'Failed to cancel email change.')
    
    return redirect('profile')


@login_required
def confirmation_status(request):
    """API endpoint to get confirmation status."""
    status = email_confirmation_service.get_confirmation_status(request.user)
    return JsonResponse(status)


@login_required
def resend_confirmation(request):
    """Resend email confirmation."""
    try:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if profile.email_confirmed:
            messages.info(request, 'Your email is already confirmed.')
        else:
            send_confirmation_email(request.user, request)
            messages.success(request, 'Confirmation email sent successfully!')
            log_activity(
                request,
                activity=f"Resent confirmation email to {request.user.username}"
            )
    except Exception as e:
        messages.error(request, 'Failed to send confirmation email. Please try again later.')
        log_activity(
            request,
            activity=f"Failed to resend confirmation email to {request.user.username}",
            details=str(e)
        )
    
    return redirect('profile')


def get_gravatar_url(email, size=200, default='identicon'):
    """Generate Gravatar URL for email address."""
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d={default}&r=g"


@login_required
def profile_view(request):
    """Display user profile with modern tabbed interface."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get active tab
    tab = request.GET.get('tab', 'basic')
    
    # Handle form submissions based on tab
    if request.method == 'POST':
        if 'basic_form' in request.POST:
            return handle_basic_form(request, profile)
        elif 'additional_form' in request.POST:
            return handle_additional_form(request, profile)
        elif 'customization_form' in request.POST:
            return handle_customization_form(request, profile)
        elif 'notification_form' in request.POST:
            return handle_notification_form(request, profile)
    
    # Initialize forms with current data
    basic_form = ProfileBasicForm(initial={
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'postcode': profile.postcode,
        'postcode_refused': profile.postcode_refused,
        'visibility': profile.visibility,
    })
    
    additional_form = ProfileAdditionalForm(instance=profile)
    customization_form = ProfileCustomizationForm(instance=profile)
    
    # Initialize notification preferences
    notification_form = ProfileNotificationForm(initial={
        'email_notifications': profile.email_notifications,
        'contribution_notifications': profile.contribution_notifications,
        'council_update_notifications': profile.council_update_notifications,
        'weekly_digest': profile.weekly_digest,
    })
    
    # Get required data
    councils = Council.objects.filter(status='active').order_by('name')
    tiers = TrustTier.objects.all().order_by('level')
    
    # Get followers (check if the relationship exists)
    try:
        followers = profile.followers.all().order_by('-created_at')[:10]
    except:
        followers = []
    
    # Get confirmation status
    confirmation_status = email_confirmation_service.get_confirmation_status(request.user)
    
    # Get notifications for notifications tab
    from council_finance.notifications import create_notification
    try:
        notifications = create_notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:20]
    except:
        notifications = []
    
    context = {
        'profile': profile,
        'user': request.user,
        'tab': tab,
        'councils': councils,
        'tiers': tiers,
        'followers': followers,
        'gravatar_url': get_gravatar_url(request.user.email),
        'confirmation_status': confirmation_status,
        'notifications': notifications,
        'basic_form': basic_form,
        'additional_form': additional_form,
        'customization_form': customization_form,
        'notification_form': notification_form,
    }
    
    return render(request, 'accounts/profile.html', context)


def handle_basic_form(request, profile):
    """Handle basic profile information form."""
    form = ProfileBasicForm(request.POST)
    
    if form.is_valid():
        changes_made = False
        password_changed = False
        
        # Update user fields
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        password1 = form.cleaned_data['password1']
        password2 = form.cleaned_data['password2']
        
        if first_name != request.user.first_name:
            request.user.first_name = first_name
            changes_made = True
        
        if last_name != request.user.last_name:
            request.user.last_name = last_name
            changes_made = True
        
        # Email changes are now handled through the modal API endpoint
        # Remove the direct email change handling from here
        
        # Handle password change
        if password1:
            request.user.set_password(password1)
            profile.last_password_change = timezone.now()
            password_changed = True
            changes_made = True
            
            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password updated successfully. Please check your email to re-confirm your account for security.')
        
        # Update profile fields
        postcode = form.cleaned_data['postcode']
        postcode_refused = form.cleaned_data['postcode_refused']
        visibility = form.cleaned_data['visibility']
        
        if postcode_refused:
            profile.postcode_refused = True
            profile.postcode = ""
            changes_made = True
        elif postcode != profile.postcode:
            profile.postcode = postcode
            profile.postcode_refused = False
            changes_made = True
        
        if visibility != profile.visibility:
            profile.visibility = visibility
            changes_made = True
        
        # Save changes
        if changes_made:
            request.user.save()
            profile.save()
            log_activity(request, activity="Basic profile information updated")
            
            # If password was changed, require email re-confirmation for security
            if password_changed:
                success = send_reconfirmation_email(request.user, "password_change", request)
                if not success:
                    messages.warning(request, 'Password updated but failed to send confirmation email. Please use the resend option.')
            
            if not password_changed:
                messages.success(request, 'Basic information updated successfully.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    
    return redirect('profile' + '?tab=basic')


def handle_additional_form(request, profile):
    """Handle additional profile information form."""
    form = ProfileAdditionalForm(request.POST, instance=profile)
    
    if form.is_valid():
        form.save()
        messages.success(request, 'Additional information updated successfully.')
        log_activity(request, activity="Additional profile information updated")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    
    return redirect('profile' + '?tab=additional')


def handle_customization_form(request, profile):
    """Handle customization settings form."""
    form = ProfileCustomizationForm(request.POST, instance=profile)
    
    if form.is_valid():
        form.save()
        messages.success(request, 'Customization settings updated successfully.')
        log_activity(request, activity="Profile customization updated")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    
    return redirect('profile' + '?tab=customization')


def handle_notification_form(request, profile):
    """Handle notification preferences form."""
    form = ProfileNotificationForm(request.POST)
    
    if form.is_valid():
        # Save notification preferences to the profile
        profile.email_notifications = form.cleaned_data['email_notifications']
        profile.contribution_notifications = form.cleaned_data['contribution_notifications']
        profile.council_update_notifications = form.cleaned_data['council_update_notifications']
        profile.weekly_digest = form.cleaned_data['weekly_digest']
        profile.save()
        
        messages.success(request, 'Notification preferences updated successfully.')
        log_activity(request, activity="Notification preferences updated")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    
    return redirect('profile' + '?tab=notifications')


# Old handler functions removed - using new tabbed form handlers above


@login_required
@require_POST
def change_email_modal(request):
    """Handle email change requests through modal interface with comprehensive debugging."""
    import json
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    
    # DEBUG: Add basic error handling
    try:
        logger.info(f"Email change request from user: {request.user.username}")
        
        # Check if request body exists
        if not request.body:
            logger.error("Empty request body")
            return JsonResponse({
                'success': False,
                'error': 'No data provided'
            }, status=400)
    
    except Exception as e:
        logger.error(f"Initial setup error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Request processing error'
        }, status=500)
    
    try:
        # Parse JSON data from the modal
        data = json.loads(request.body)
        new_email = data.get('email', '').strip().lower()
        
        # Comprehensive logging for debugging
        log_activity(
            request,
            activity="Email change request received",
            extra=f"Current email: {request.user.email}, Requested email: {new_email}, User: {request.user.username}"
        )
        
        # Validate email format
        if not new_email:
            return JsonResponse({
                'success': False,
                'error': 'Email address is required'
            }, status=400)
        
        try:
            validate_email(new_email)
        except ValidationError:
            log_activity(
                request,
                activity="Email change failed - invalid format",
                extra=f"Invalid email format: {new_email}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid email address'
            }, status=400)
        
        # Check if email is the same as current
        if new_email == request.user.email.lower():
            return JsonResponse({
                'success': False,
                'error': 'This is already your current email address'
            }, status=400)
        
        # Check if email is already in use by another user
        from django.contrib.auth.models import User
        if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
            log_activity(
                request,
                activity="Email change failed - email already in use",
                extra=f"Email {new_email} already exists for another user"
            )
            return JsonResponse({
                'success': False,
                'error': 'This email address is already registered to another account'
            }, status=400)
        
        # Check rate limiting
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not profile.can_send_confirmation():
            log_activity(
                request,
                activity="Email change failed - rate limited",
                extra=f"User {request.user.username} exceeded rate limit"
            )
            return JsonResponse({
                'success': False,
                'error': 'Please wait before requesting another email change. You can try again in a few minutes.'
            }, status=429)
        
        # Attempt to send confirmation email
        try:
            logger.info(f"Attempting to send confirmation email to {new_email}")
            success = send_email_change_confirmation(request.user, new_email, request)
            logger.info(f"Email send result: {success}")
            
            if success:
                log_activity(
                    request,
                    activity="Email change confirmation sent successfully",
                    extra=f"Confirmation email sent from {request.user.email} to {new_email}"
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Please check {new_email} to confirm your email change. Your current email ({request.user.email}) remains active until confirmed.',
                    'new_email': new_email,
                    'current_email': request.user.email
                })
            else:
                # Log the failure and send alert to admins
                error_details = f"Failed to send email change confirmation to {new_email} for user {request.user.username}"
                log_activity(
                    request,
                    activity="Email change confirmation failed",
                    extra=error_details
                )
                
                # Send alert email to admins
                try:
                    from council_finance.emails import send_email_enhanced
                    send_email_enhanced(
                        to_email=settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'admin@councilfinance.com',
                        subject='Email Service Alert: Email change confirmation failed',
                        template='emails/admin_alert.html',
                        context={
                            'alert_type': 'Email Change Failure',
                            'user': request.user,
                            'details': error_details,
                            'timestamp': timezone.now(),
                            'ip_address': request.META.get('REMOTE_ADDR', 'Unknown')
                        }
                    )
                except Exception as alert_error:
                    logger.error(f"Failed to send admin alert: {alert_error}")
                
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to send confirmation email. Our team has been notified. Please try again later.'
                }, status=500)
                
        except Exception as email_error:
            error_details = f"Exception during email change for {request.user.username}: {str(email_error)}"
            log_activity(
                request,
                activity="Email change exception",
                extra=error_details
            )
            logger.error(error_details)
            
            # Send alert email to admins about the exception
            try:
                from council_finance.emails import send_email_enhanced
                send_email_enhanced(
                    to_email=settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'admin@councilfinance.com',
                    subject='Email Service Alert: Email change exception',
                    template='emails/admin_alert.html',
                    context={
                        'alert_type': 'Email Change Exception',
                        'user': request.user,
                        'details': error_details,
                        'timestamp': timezone.now(),
                        'ip_address': request.META.get('REMOTE_ADDR', 'Unknown'),
                        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                    }
                )
            except Exception as alert_error:
                logger.error(f"Failed to send admin alert for exception: {alert_error}")
            
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred. Our team has been notified. Please try again later.'
            }, status=500)
    
    except json.JSONDecodeError:
        log_activity(
            request,
            activity="Email change failed - invalid JSON",
            extra="Invalid JSON in request body"
        )
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format'
        }, status=400)
    
    except Exception as e:
        error_details = f"Unexpected error in email change modal: {str(e)}"
        log_activity(
            request,
            activity="Email change modal - unexpected error",
            extra=error_details
        )
        logger.error(error_details)
        
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again later.'
        }, status=500)


@login_required
def user_preferences_view(request):
    """Display and handle user preferences."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Handle preference updates
        preferences = {}
        for key, value in request.POST.items():
            if key.startswith('pref_'):
                pref_key = key[5:]  # Remove 'pref_' prefix
                preferences[pref_key] = value
        
        # Update profile preferences
        if not hasattr(profile, 'preferences'):
            profile.preferences = {}
        profile.preferences.update(preferences)
        profile.save()
        
        messages.success(request, 'Preferences updated successfully!')
        log_activity(
            request,
            activity="Updated user preferences",
            details=f"Updated: {', '.join(preferences.keys())}"
        )
        
        return redirect('user_preferences')
    
    context = {
        'profile': profile,
        'preferences': getattr(profile, 'preferences', {}),
    }
    
    return render(request, 'accounts/preferences.html', context)


@login_required
def update_postcode(request):
    """Handle postcode updates."""
    if request.method == 'POST':
        postcode = request.POST.get('postcode', '').strip()
        
        if not postcode:
            messages.error(request, 'Please enter a valid postcode.')
            return redirect('profile')
        
        # Create a pending profile change
        token = get_random_string(32)
        pending_change = PendingProfileChange.objects.create(
            user=request.user,
            field='postcode',
            new_value=postcode,
            token=token,
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        # Send confirmation email
        try:
            confirm_url = request.build_absolute_uri(
                reverse('confirm_profile_change', kwargs={'token': token})
            )
            
            send_email(
                to_email=request.user.email,
                subject='Confirm postcode change',
                template='emails/confirm_postcode_change.html',
                context={
                    'user': request.user,
                    'new_postcode': postcode,
                    'confirm_url': confirm_url,
                }
            )
            
            messages.success(
                request,
                'Please check your email to confirm the postcode change.'
            )
            
            log_activity(
                request,
                activity=f"Postcode change requested: {postcode}",
                details=f"Confirmation token: {token}"
            )
            
        except Exception as e:
            messages.error(request, 'Failed to send confirmation email. Please try again.')
            log_activity(
                request,
                activity=f"Failed to send postcode change confirmation to {request.user.username}",
                details=str(e)
            )
            pending_change.delete()
    
    return redirect('profile')


def confirm_profile_change(request, token):
    """Confirm profile changes with improved error handling."""
    try:
        # First, try to find any record with this token (regardless of expiration)
        try:
            pending_change = PendingProfileChange.objects.get(token=token)
        except PendingProfileChange.DoesNotExist:
            messages.error(request, 'Invalid confirmation token. This link may be incorrect or the request may have been cancelled.')
            log_activity(
                request,
                council=None,
                activity=f"Failed confirmation attempt - token not found: {token[:20]}...",
                extra=f"IP: {request.META.get('REMOTE_ADDR', 'Unknown')}"
            )
            return redirect('profile' if request.user.is_authenticated else 'login')
        
        # Check if the token has expired
        if pending_change.is_expired:
            # For email changes, offer to resend confirmation
            if pending_change.field == 'email':
                messages.error(request, 
                    f'This email change confirmation has expired. '
                    f'You can request a new email change from your profile page to change your email to {pending_change.new_value}.'
                )
                log_activity(
                    request,
                    council=None,
                    activity=f"Expired email change confirmation attempted",
                    extra=f"User: {pending_change.user.username}, Expired: {pending_change.expires_at}, Target: {pending_change.new_value}"
                )
            else:
                messages.error(request, f'This {pending_change.field} change confirmation has expired. Please try making the change again.')
                log_activity(
                    request,
                    council=None,
                    activity=f"Expired {pending_change.field} change confirmation attempted",
                    extra=f"User: {pending_change.user.username}, Expired: {pending_change.expires_at}"
                )
            
            # Clean up expired record
            pending_change.delete()
            return redirect('profile' if request.user.is_authenticated else 'login')
        
        # Check if already confirmed
        if hasattr(pending_change, 'status') and pending_change.status == 'confirmed':
            messages.info(request, 'This change has already been confirmed.')
            return redirect('profile' if request.user.is_authenticated else 'login')
        
        # Apply the change
        profile, created = UserProfile.objects.get_or_create(user=pending_change.user)
        
        if pending_change.field == 'postcode':
            old_postcode = profile.postcode
            profile.postcode = pending_change.new_value
            profile.save()
            
            messages.success(request, f'Postcode updated successfully from "{old_postcode or "none"}" to "{pending_change.new_value}"!')
            log_activity(
                request,
                council=None,
                activity=f"Postcode confirmed and updated to: {pending_change.new_value}",
                extra=f"User: {pending_change.user.username}, Previous: {old_postcode}"
            )
            
        elif pending_change.field == 'email':
            # Handle email change confirmation
            old_email = pending_change.user.email
            new_email = pending_change.new_value
            
            # Update user email
            pending_change.user.email = new_email
            pending_change.user.save()
            
            # Update profile
            profile.email_confirmed = True
            profile.pending_email = None
            profile.pending_email_token = None
            profile.pending_email_expires = None
            profile.save()
            
            messages.success(request, f'Email address successfully changed from {old_email} to {new_email}!')
            log_activity(
                request,
                council=None,
                activity=f"Email confirmed and updated from {old_email} to {new_email}",
                extra=f"User: {pending_change.user.username}, Token: {token[:20]}..."
            )
            
            # Send confirmation notification to new email
            try:
                from council_finance.emails import send_email
                send_email(
                    to_email=new_email,
                    subject='Email address change confirmed',
                    template='emails/email_change_success.html',
                    context={
                        'user': pending_change.user,
                        'old_email': old_email,
                        'new_email': new_email,
                        'changed_at': timezone.now(),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send email change success notification: {e}")
        
        # Mark as confirmed and delete the pending change
        if hasattr(pending_change, 'status'):
            pending_change.status = 'confirmed'
            pending_change.confirmed_at = timezone.now()
            pending_change.save()
        
        pending_change.delete()
        
    except Exception as e:
        logger.error(f"Error in confirm_profile_change: {e}")
        messages.error(request, 'An error occurred while confirming your change. Please try again or contact support.')
        log_activity(
            request,
            council=None,
            activity=f"Error in profile change confirmation: {str(e)}",
            extra=f"Token: {token[:20]}..., IP: {request.META.get('REMOTE_ADDR', 'Unknown')}"
        )
    
    return redirect('profile' if request.user.is_authenticated else 'login')


@login_required
def notifications_page(request):
    """Display user notifications."""
    # Get notifications for the user
    notifications = create_notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]
    
    # Mark notifications as read when viewed
    unread_notifications = notifications.filter(read=False)
    unread_notifications.update(read=True)
    
    context = {
        'notifications': notifications,
        'unread_count': unread_notifications.count(),
    }
    
    return render(request, 'accounts/notifications.html', context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read."""
    try:
        notification = get_object_or_404(
            create_notification,
            id=notification_id,
            user=request.user
        )
        notification.read = True
        notification.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user."""
    try:
        count = create_notification.objects.filter(
            user=request.user,
            read=False
        ).update(read=True)
        
        return JsonResponse({
            'success': True,
            'marked_count': count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def dismiss_notification(request, notification_id):
    """Dismiss a notification."""
    try:
        notification = get_object_or_404(
            create_notification,
            id=notification_id,
            user=request.user
        )
        notification.dismissed = True
        notification.save()
        
        messages.success(request, 'Notification dismissed.')
        
    except Exception as e:
        messages.error(request, 'Failed to dismiss notification.')
    
    return redirect('notifications')


def my_profile(request):
    """Display user's own profile with activity summary."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get recent contributions
    from council_finance.models import Contribution
    recent_contributions = Contribution.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Get activity stats
    from council_finance.models import ActivityLog
    activity_count = ActivityLog.objects.filter(user=request.user).count()
    
    context = {
        'profile': profile,
        'recent_contributions': recent_contributions,
        'activity_count': activity_count,
    }
    
    return render(request, 'accounts/my_profile.html', context)
