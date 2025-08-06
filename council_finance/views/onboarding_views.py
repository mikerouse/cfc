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
from council_finance.forms import BasicDetailsForm, AgeVerificationForm, LocationInfoForm, CommunityGuidelinesForm
from council_finance.services.onboarding_logger import OnboardingLogger
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
    
    # Log to Event Viewer
    OnboardingLogger.log_registration_started(request.user, request, profile)
    
    # Also log to activity log for backwards compatibility
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
            
            # Log to Event Viewer
            OnboardingLogger.log_step_completion(
                user=request.user,
                request=request,
                step_name='Basic Details',
                step_number=2,
                total_steps=5 if profile.is_uk_user else 4,
                details={
                    'first_name_provided': bool(user.first_name),
                    'last_name_provided': bool(user.last_name),
                }
            )
            
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
            
            # Log to Event Viewer
            OnboardingLogger.log_age_verification(request.user, request, profile, age)
            OnboardingLogger.log_step_completion(
                user=request.user,
                request=request,
                step_name='Age Verification',
                step_number=3,
                total_steps=5 if profile.is_uk_user else 4,
                details={
                    'age': age,
                    'is_adult': profile.is_adult(),
                    'osa_compliant': age >= 13,
                }
            )
            
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
@require_http_methods(["GET", "POST"])
def location_info(request):
    """
    Step 4: Location information (conditional on UK status).
    Only shown to UK users - collects optional postcode.
    """
    profile = getattr(request.user, 'profile', None)
    
    if not profile or not profile.needs_onboarding():
        return redirect('welcome')
    
    # Skip this step for non-UK users
    if not profile.is_uk_user:
        OnboardingLogger.log_location_collection(request.user, request, profile, 'non-uk')
        messages.info(request, "Location step skipped as you're not in the UK.")
        return redirect('onboarding_guidelines')
    
    # Check if we already have location info or refusal
    if profile.postcode or profile.postcode_refused:
        messages.info(request, "Your location preferences have already been saved.")
        return redirect('onboarding_guidelines')
    
    if request.method == 'POST':
        form = LocationInfoForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            
            # Log the outcome
            if profile.postcode:
                OnboardingLogger.log_location_collection(request.user, request, profile, 'provided')
                log_activity(
                    request,
                    activity=f"User provided postcode: {profile.postcode[:3]}*** (masked for privacy)"
                )
                messages.success(request, "Thanks! Your postcode will help us show you relevant local information.")
            elif profile.postcode_refused:
                OnboardingLogger.log_location_collection(request.user, request, profile, 'refused')
                log_activity(
                    request,
                    activity="User declined to provide postcode"
                )
                messages.success(request, "No problem! You can always add your postcode later in your profile settings.")
            else:
                OnboardingLogger.log_location_collection(request.user, request, profile, 'skipped')
                log_activity(
                    request,
                    activity="User skipped postcode collection"
                )
                messages.success(request, "Location step completed.")
            
            # Log step completion
            OnboardingLogger.log_step_completion(
                user=request.user,
                request=request,
                step_name='Location Information',
                step_number=4,
                total_steps=5,  # Always 5 for UK users who see this step
                details={
                    'postcode_provided': bool(profile.postcode),
                    'postcode_refused': profile.postcode_refused,
                }
            )
            
            return redirect('onboarding_guidelines')
    else:
        form = LocationInfoForm(instance=profile)
    
    # Calculate progress
    total_steps = 5  # This step is only shown to UK users, so total is always 5
    current_step = 4
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
    
    return render(request, 'onboarding/location_info.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def community_guidelines(request):
    """
    Step 5: Community guidelines acceptance.
    Final step required for all users.
    """
    profile = getattr(request.user, 'profile', None)
    
    if not profile or not profile.needs_onboarding():
        return redirect('welcome')
    
    # Check if guidelines already accepted
    if profile.community_guidelines_accepted:
        messages.info(request, "You have already accepted the community guidelines.")
        return redirect('onboarding_complete')
    
    if request.method == 'POST':
        form = CommunityGuidelinesForm(request.POST)
        if form.is_valid():
            # Mark guidelines as accepted
            profile.community_guidelines_accepted = True
            profile.community_guidelines_accepted_at = timezone.now()
            profile.save()
            
            # Log to Event Viewer
            OnboardingLogger.log_guidelines_acceptance(request.user, request, profile)
            OnboardingLogger.log_step_completion(
                user=request.user,
                request=request,
                step_name='Community Guidelines',
                step_number=5 if profile.is_uk_user else 4,
                total_steps=5 if profile.is_uk_user else 4,
                details={
                    'guidelines_version': '1.0',
                    'is_final_step': True,
                }
            )
            OnboardingLogger.log_onboarding_completed(request.user, request, profile)
            
            log_activity(
                request,
                activity="User accepted community guidelines - onboarding completed"
            )
            
            messages.success(request, "Welcome to Council Finance Counters! Your account is now fully set up.")
            return redirect('onboarding_complete')
    else:
        form = CommunityGuidelinesForm()
    
    # Calculate progress
    total_steps = 5 if profile.is_uk_user else 4
    current_step = total_steps  # This is the final step
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
    
    return render(request, 'onboarding/community_guidelines.html', context)


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