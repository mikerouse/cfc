"""
User onboarding views for Auth0 integration and OSA compliance.
Handles the multi-step onboarding process for new users.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from council_finance.models import UserProfile
from council_finance.forms import BasicDetailsForm, AgeVerificationForm
from .general import log_activity

logger = logging.getLogger(__name__)


def detect_user_country(user, request):
    """
    Detect if user is likely UK-based from various sources.
    Priority: Auth0 data > IP geolocation > email domain
    """
    profile = getattr(user, 'profile', None)
    
    # Check Auth0 metadata first
    if profile and profile.auth0_metadata:
        country = profile.auth0_metadata.get('country', '')
        locale = profile.auth0_metadata.get('locale', '')
        
        if country == 'GB' or locale.endswith('_GB'):
            return True
            
    # Check email domain patterns
    if user.email and user.email.endswith(('.uk', '.gov.uk', '.ac.uk')):
        return True
        
    # TODO: Add IP geolocation as fallback if needed
    # For now, default to UK (can be changed in location step)
    return True


@login_required
def welcome(request):
    """
    Step 1: Welcome page and data extraction from Auth0.
    Extracts available data and determines onboarding path.
    """
    profile = getattr(request.user, 'profile', None)
    
    if not profile:
        # Create profile if it doesn't exist (shouldn't happen with pipeline)
        profile = UserProfile.objects.create(user=request.user)
        log_activity(request, activity="Created missing UserProfile during onboarding")
    
    # Check if user needs onboarding
    if not profile.needs_onboarding():
        messages.info(request, "Your account is already set up!")
        return redirect('profile')
    
    # Extract data from Auth0 if available
    auth0_data = profile.auth0_metadata
    user_data = {
        'first_name': request.user.first_name or auth0_data.get('given_name', ''),
        'last_name': request.user.last_name or auth0_data.get('family_name', ''),
        'email': request.user.email,
        'email_verified': profile.email_confirmed,
        'has_auth0_data': bool(auth0_data),
    }
    
    # Detect user's likely country
    is_uk_user = detect_user_country(request.user, request)
    profile.is_uk_user = is_uk_user
    profile.save()
    
    # Determine next step based on available data
    if user_data['first_name'] and user_data['last_name']:
        next_step = 'age'  # Skip basic details if we have name
    else:
        next_step = 'details'  # Need to collect name
    
    # Calculate progress
    total_steps = 5 if is_uk_user else 4
    current_step = 1
    progress_percent = int(round((current_step / total_steps) * 100))
    
    context = {
        'user_data': user_data,
        'is_uk_user': is_uk_user,
        'next_step': next_step,
        'progress': {
            'current': current_step, 
            'total': total_steps,
            'percent': progress_percent
        }
    }
    
    log_activity(
        request,
        activity=f"User started onboarding - UK: {is_uk_user}, has name: {bool(user_data['first_name'])}"
    )
    
    return render(request, 'onboarding/welcome.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def basic_details(request):
    """
    Step 2: Collect basic details (name) if not available from Auth0.
    """
    profile = getattr(request.user, 'profile', None)
    
    if not profile or not profile.needs_onboarding():
        return redirect('welcome')
    
    # Check if we already have name data
    if request.user.first_name and request.user.last_name:
        messages.info(request, "We already have your name from your Auth0 profile.")
        return redirect('onboarding_age')
    
    if request.method == 'POST':
        form = BasicDetailsForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            
            log_activity(
                request,
                activity=f"User completed basic details: {user.first_name} {user.last_name}"
            )
            
            messages.success(request, "Thanks! Your basic details have been saved.")
            return redirect('onboarding_age')
    else:
        # Pre-populate from Auth0 data if available
        initial_data = {}
        if profile.auth0_metadata:
            initial_data = {
                'first_name': profile.auth0_metadata.get('given_name', request.user.first_name),
                'last_name': profile.auth0_metadata.get('family_name', request.user.last_name),
            }
        
        form = BasicDetailsForm(instance=request.user, initial=initial_data)
    
    # Calculate progress
    total_steps = 5 if profile.is_uk_user else 4
    current_step = 2
    progress_percent = int(round((current_step / total_steps) * 100))
    
    context = {
        'form': form,
        'progress': {
            'current': current_step, 
            'total': total_steps,
            'percent': progress_percent
        },
        'is_uk_user': profile.is_uk_user,
    }
    
    return render(request, 'onboarding/basic_details.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def age_verification(request):
    """
    Step 3: Age verification (date of birth collection).
    Required for OSA compliance.
    """
    profile = getattr(request.user, 'profile', None)
    
    if not profile or not profile.needs_onboarding():
        return redirect('welcome')
    
    # Check if we already have age verification
    if profile.date_of_birth and profile.age_verified:
        messages.info(request, "Your age has already been verified.")
        return redirect('onboarding_location' if profile.is_uk_user else 'onboarding_guidelines')
    
    if request.method == 'POST':
        form = AgeVerificationForm(request.POST)
        if form.is_valid():
            dob = form.cleaned_data['date_of_birth']
            
            # Update profile with age information
            profile.date_of_birth = dob
            profile.age_verified = True
            
            # Update content access based on age (OSA compliance)
            profile.update_content_access()
            
            profile.save()
            
            # Calculate age for logging
            from datetime import date
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            log_activity(
                request,
                activity=f"User completed age verification: {age} years old, adult: {profile.is_adult()}"
            )
            
            # Show appropriate success message based on age
            if profile.is_adult():
                messages.success(request, "Age verified! You have full access to all features.")
            else:
                messages.success(request, "Age verified! Some features may be restricted for your safety.")
            
            # Navigate to next step
            if profile.is_uk_user:
                return redirect('onboarding_location')
            else:
                return redirect('onboarding_guidelines')
    else:
        form = AgeVerificationForm()
    
    # Calculate progress
    total_steps = 5 if profile.is_uk_user else 4
    current_step = 3
    progress_percent = int(round((current_step / total_steps) * 100))
    
    context = {
        'form': form,
        'progress': {
            'current': current_step, 
            'total': total_steps,
            'percent': progress_percent
        },
        'is_uk_user': profile.is_uk_user,
    }
    
    return render(request, 'onboarding/age_verification.html', context)


@login_required
def location_info(request):
    """
    Step 4: Location information (conditional on UK status).
    """
    # Placeholder - will implement in next phase
    return render(request, 'onboarding/location_info.html', {
        'progress': {'current': 4, 'total': 5}
    })


@login_required
def community_guidelines(request):
    """
    Step 5: Community guidelines acceptance.
    """
    # Placeholder - will implement in next phase
    return render(request, 'onboarding/community_guidelines.html', {
        'progress': {'current': 5, 'total': 5}
    })


@login_required
def onboarding_complete(request):
    """
    Final step: Onboarding completion and redirect.
    """
    profile = getattr(request.user, 'profile', None)
    
    if profile and not profile.needs_onboarding():
        return render(request, 'onboarding/complete.html', {
            'user': request.user,
            'profile': profile,
        })
    else:
        # Still needs onboarding
        return redirect('welcome')