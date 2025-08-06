"""
Custom Auth0 pipeline functions to integrate with existing UserProfile system.
"""
import logging
from django.utils import timezone
from .models import UserProfile

logger = logging.getLogger(__name__)


def save_profile(backend, user, response, *args, **kwargs):
    """
    Save Auth0 user data to our UserProfile model.
    This runs after user creation in the social auth pipeline.
    """
    if not user:
        return
    
    # Get or create the user profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Store Auth0 user ID for future reference
    auth0_user_id = kwargs.get('uid', '')
    if auth0_user_id:
        profile.auth0_user_id = auth0_user_id
    
    # Store Auth0 metadata
    profile.auth0_metadata = {
        'provider': backend.name,
        'picture': response.get('picture', ''),
        'locale': response.get('locale', ''),
        'updated_at': response.get('updated_at', ''),
        'last_login': timezone.now().isoformat(),
    }
    
    # Check if email is verified from Auth0
    email_verified = response.get('email_verified', False)
    if email_verified and not profile.email_confirmed:
        profile.confirm_email()
        logger.info(f"Email confirmed via Auth0 for user {user.username}")
    
    # Set login method for tracking
    profile.last_login_method = f'auth0:{backend.name}'
    
    # Save the profile
    profile.save()
    
    if created:
        logger.info(f"Created UserProfile for Auth0 user {user.username}")
    else:
        logger.info(f"Updated UserProfile for Auth0 user {user.username}")
    
    return {'profile': profile}


def redirect_to_onboarding(strategy, details, user=None, *args, **kwargs):
    """
    Redirect new users to onboarding if they need it.
    This runs at the end of the pipeline.
    """
    if user and hasattr(user, 'profile'):
        profile = user.profile
        if profile.needs_onboarding():
            # Store the fact that this user needs onboarding
            strategy.session_set('needs_onboarding', True)
            # The redirect will be handled by middleware or view logic
    
    return {}