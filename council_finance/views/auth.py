"""
Authentication and user management views for Council Finance Counters.
This module handles user registration, login, profile management, and notifications.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core import signing
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from council_finance.models import UserProfile, PendingProfileChange
from council_finance.forms import SignUpForm, ProfileExtraForm
from council_finance.emails import send_confirmation_email, send_email
from council_finance.notifications import create_notification

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
    """Confirm user email address."""
    try:
        # Verify the token
        data = signing.loads(token, max_age=86400)  # 24 hours
        user_id = data.get('user_id')
        
        if not user_id:
            messages.error(request, 'Invalid confirmation token.')
            return redirect('login')
        
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            if profile.email_confirmed:
                messages.info(request, 'Your email is already confirmed.')
            else:
                profile.email_confirmed = True
                profile.save()
                
                # Log the user in automatically
                login(request, profile.user)
                
                messages.success(request, 'Email confirmed successfully! Welcome to Council Finance Counters.')
                log_activity(
                    request,
                    activity=f"Email confirmed for user: {profile.user.username}"
                )
                
        except UserProfile.DoesNotExist:
            messages.error(request, 'User profile not found.')
            return redirect('login')
            
    except signing.BadSignature:
        messages.error(request, 'Invalid or expired confirmation token.')
        return redirect('login')
    
    return redirect('home')


@login_required
def resend_confirmation(request):
    """Resend email confirmation."""
    try:
        profile = request.user.userprofile_set.first()
        if profile and profile.email_confirmed:
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


@login_required
def profile_view(request):
    """Display user profile."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
        'user': request.user,
    }
    
    return render(request, 'accounts/profile.html', context)


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
