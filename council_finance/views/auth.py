"""
Authentication and user management views for Council Finance Counters.
This module handles user registration, login, profile management, and notifications.
"""

import hashlib
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

from council_finance.models import UserProfile, PendingProfileChange, Council, TrustTier
from council_finance.forms import SignUpForm, ProfileExtraForm
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
    """Display user profile."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Handle different form submissions
    if request.method == 'POST':
        if 'change_details' in request.POST:
            return handle_profile_change(request, profile)
        elif 'visibility' in request.POST:
            return handle_visibility_change(request, profile)
        elif 'update_extra' in request.POST:
            return handle_extra_info_update(request, profile)
        elif 'preferred_font' in request.POST or 'tier' in request.POST:
            return handle_customization_update(request, profile)
    
    # Get tab parameter
    tab = request.GET.get('tab', 'profile')
    
    # Get required data for template
    councils = Council.objects.filter(active=True).order_by('name')
    tiers = TrustTier.objects.all().order_by('level')
    fonts = ['Arial', 'Helvetica', 'Georgia', 'Times New Roman', 'Verdana', 'Tahoma']
    
    # Get followers (check if the relationship exists)
    try:
        followers = profile.followers.all().order_by('-created_at')[:10]
    except:
        followers = []
    
    # Get confirmation status
    confirmation_status = email_confirmation_service.get_confirmation_status(request.user)
    
    # Visibility choices
    visibility_choices = UserProfile.VISIBILITY_CHOICES
    
    context = {
        'profile': profile,
        'user': request.user,
        'tab': tab,
        'councils': councils,
        'tiers': tiers,
        'fonts': fonts,
        'followers': followers,
        'visibility_choices': visibility_choices,
        'gravatar_url': get_gravatar_url(request.user.email),
        'confirmation_status': confirmation_status,
    }
    
    return render(request, 'accounts/profile.html', context)


def handle_profile_change(request, profile):
    """Handle profile detail changes (email, name, password)."""
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    password1 = request.POST.get('password1', '').strip()
    password2 = request.POST.get('password2', '').strip()
    
    changes_made = False
    password_changed = False
    
    # Update name fields
    if first_name != request.user.first_name:
        request.user.first_name = first_name
        changes_made = True
    
    if last_name != request.user.last_name:
        request.user.last_name = last_name
        changes_made = True
    
    # Handle email change (requires confirmation)
    if email != request.user.email:
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        try:
            validate_email(email)
            # Use new email confirmation service
            success = send_email_change_confirmation(request.user, email, request)
            if success:
                messages.success(request, f'Please check {email} to confirm your email change. Your current email remains active until confirmed.')
            else:
                messages.error(request, 'Failed to send confirmation email. Please try again later.')
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
    
    # Handle password change
    if password1 and password2:
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            # Update password
            request.user.set_password(password1)
            profile.last_password_change = timezone.now()
            password_changed = True
            changes_made = True
            
            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Password updated successfully. Please check your email to re-confirm your account for security.')
    
    # Save changes
    if changes_made:
        request.user.save()
        profile.save()
        log_activity(request, activity="Profile details updated")
        
        # If password was changed, require email re-confirmation for security
        if password_changed:
            success = send_reconfirmation_email(request.user, "password_change", request)
            if not success:
                messages.warning(request, 'Password updated but failed to send confirmation email. Please use the resend option.')
        
        if not password_changed:  # Only show general success if no password change
            messages.success(request, 'Profile updated successfully.')
    
    return redirect('profile')


def handle_visibility_change(request, profile):
    """Handle profile visibility change."""
    visibility = request.POST.get('visibility')
    if visibility in dict(UserProfile.VISIBILITY_CHOICES):
        profile.visibility = visibility
        profile.save()
        messages.success(request, 'Profile visibility updated.')
        log_activity(request, activity=f"Profile visibility changed to {visibility}")
    else:
        messages.error(request, 'Invalid visibility setting.')
    
    return redirect('profile')


def handle_extra_info_update(request, profile):
    """Handle extra profile information update."""
    political_affiliation = request.POST.get('political_affiliation', '').strip()
    works_for_council = request.POST.get('works_for_council') == '1'
    employer_council_id = request.POST.get('employer_council')
    official_email = request.POST.get('official_email', '').strip()
    
    profile.political_affiliation = political_affiliation
    profile.works_for_council = works_for_council
    profile.official_email = official_email
    
    if employer_council_id:
        try:
            profile.employer_council = Council.objects.get(id=employer_council_id)
        except Council.DoesNotExist:
            profile.employer_council = None
    else:
        profile.employer_council = None
    
    profile.save()
    messages.success(request, 'Volunteer information updated.')
    log_activity(request, activity="Volunteer information updated")
    
    return redirect('profile')


def handle_customization_update(request, profile):
    """Handle customization settings update."""
    preferred_font = request.POST.get('preferred_font')
    tier_id = request.POST.get('tier')
    
    if preferred_font:
        profile.preferred_font = preferred_font
    
    if tier_id and request.user.is_superuser:
        try:
            profile.tier = TrustTier.objects.get(id=tier_id)
        except TrustTier.DoesNotExist:
            messages.error(request, 'Invalid trust tier.')
            return redirect('profile')
    
    profile.save()
    messages.success(request, 'Customization settings updated.')
    log_activity(request, activity="Customization settings updated")
    
    return redirect('profile')


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
    """Confirm profile changes."""
    try:
        pending_change = get_object_or_404(
            PendingProfileChange,
            token=token,
            expires_at__gt=timezone.now()
        )
        
        # Apply the change
        profile, created = UserProfile.objects.get_or_create(user=pending_change.user)
        
        if pending_change.field == 'postcode':
            profile.postcode = pending_change.new_value
            profile.save()
            
            messages.success(request, 'Postcode updated successfully!')
            log_activity(
                request,
                council=None,
                activity=f"Postcode updated to: {pending_change.new_value}",
                details=f"User: {pending_change.user.username}"
            )
        
        # Delete the pending change
        pending_change.delete()
        
    except PendingProfileChange.DoesNotExist:
        messages.error(request, 'Invalid or expired confirmation token.')
    
    return redirect('profile')


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
