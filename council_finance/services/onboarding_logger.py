"""
Onboarding Event Logger Service
Provides centralized logging for all onboarding events to the Event Viewer system.
"""
from datetime import date
from django.utils import timezone
from typing import Optional, Dict, Any


class OnboardingLogger:
    """
    Service for logging onboarding events to the Event Viewer system.
    Ensures consistent event tracking across the entire onboarding flow.
    """
    
    @staticmethod
    def log_registration_started(user, request, profile):
        """Log when a new user starts the onboarding process via Auth0."""
        from event_viewer.models import SystemEvent
        
        # Extract detection data
        auth0_metadata = profile.auth0_metadata if profile else {}
        email_domain = user.email.split('@')[1] if user.email and '@' in user.email else ''
        
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='user_activity', 
            title='New User Registration Started',
            message=f'User {user.email} began onboarding via Auth0',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'auth0_user_id': profile.auth0_user_id if profile else None,
                'country_detected': 'UK' if profile and profile.is_uk_user else 'International',
                'email_verified': profile.email_confirmed if profile else False,
                'registration_method': 'auth0',
                'detection_data': {
                    'locale': auth0_metadata.get('locale', ''),
                    'email_domain': email_domain,
                    'auth0_provider': profile.last_login_method if profile else '',
                }
            },
            tags=['onboarding', 'auth0', 'registration'],
            fingerprint=f'user_registration_started_{user.id}_{date.today()}'
        )
    
    @staticmethod
    def log_step_completion(user, request, step_name: str, step_number: int, total_steps: int, details: Optional[Dict[str, Any]] = None):
        """Log completion of an onboarding step."""
        from event_viewer.models import SystemEvent
        
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='user_activity',
            title=f'Onboarding Step Completed: {step_name}',
            message=f'User {user.username or user.email} completed {step_name} step ({step_number}/{total_steps})',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'step_name': step_name,
                'step_number': step_number,
                'total_steps': total_steps,
                'progress_percent': round((step_number / total_steps) * 100),
                **(details or {})
            },
            tags=['onboarding', 'step_completion', step_name.lower().replace(' ', '_')],
            fingerprint=f'onboarding_step_{step_name.lower().replace(" ", "_")}_{user.id}'
        )
    
    @staticmethod
    def log_age_verification(user, request, profile, age: int):
        """Log age verification completion for OSA compliance."""
        from event_viewer.models import SystemEvent
        
        is_adult = age >= 18
        
        SystemEvent.objects.create(
            source='osa_compliance',
            level='info',
            category='compliance',
            title='Age Verification Completed',
            message=f'User verified age: {age} years old',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'age': age,
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                'is_adult': is_adult,
                'verification_method': 'self_declared',
                'osa_compliant': age >= 13,
            },
            tags=['osa', 'age_verification', 'compliance'],
            fingerprint=f'age_verification_{user.id}'
        )
        
        # If under 18, log content restrictions
        if not is_adult:
            SystemEvent.objects.create(
                source='osa_compliance',
                level='warning',
                category='compliance',
                title='OSA Content Restrictions Applied',
                message=f'User under 18 - Feed/comments blocked per OSA requirements',
                user=user,
                request_path=request.path,
                details={
                    'age': age,
                    'restrictions_applied': ['feed_blocked', 'comments_blocked'],
                    'compliance_reason': 'online_safety_act',
                    'can_access_comments': False,
                },
                tags=['osa', 'content_restriction', 'minor_protection'],
                fingerprint=f'content_restrictions_{user.id}'
            )
    
    @staticmethod
    def log_location_collection(user, request, profile, outcome: str):
        """Log location information collection outcome."""
        from event_viewer.models import SystemEvent
        
        # Determine what happened
        if outcome == 'provided':
            masked_postcode = f"{profile.postcode[:3]}***" if profile.postcode and len(profile.postcode) >= 3 else "***"
            message = f'User provided postcode: {masked_postcode}'
            details = {
                'outcome': 'postcode_provided',
                'postcode_prefix': profile.postcode[:3] if profile.postcode and len(profile.postcode) >= 3 else None,
                'is_uk_user': True,
            }
        elif outcome == 'refused':
            message = 'User declined to provide postcode'
            details = {
                'outcome': 'postcode_refused',
                'is_uk_user': True,
            }
        elif outcome == 'skipped':
            message = 'User skipped postcode collection'
            details = {
                'outcome': 'postcode_skipped',
                'is_uk_user': True,
            }
        else:  # non-uk
            message = 'Location step skipped - non-UK user'
            details = {
                'outcome': 'not_applicable',
                'is_uk_user': False,
            }
        
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='user_activity',
            title='Location Information Collection',
            message=message,
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details=details,
            tags=['onboarding', 'location', 'geographic_data'],
            fingerprint=f'location_collection_{user.id}'
        )
    
    @staticmethod
    def log_guidelines_acceptance(user, request, profile):
        """Log community guidelines acceptance."""
        from event_viewer.models import SystemEvent
        
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='compliance',
            title='Community Guidelines Accepted',
            message=f'User {user.username or user.email} accepted community guidelines',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'guidelines_version': '1.0',  # Could be dynamic in future
                'accepted_at': timezone.now().isoformat(),
                'is_adult': profile.is_adult() if profile else None,
                'completion_time': None,  # Could track time spent reading
            },
            tags=['onboarding', 'community_guidelines', 'compliance'],
            fingerprint=f'guidelines_acceptance_{user.id}'
        )
    
    @staticmethod
    def log_onboarding_completed(user, request, profile):
        """Log successful completion of entire onboarding flow."""
        from event_viewer.models import SystemEvent
        
        # Calculate summary stats
        age = profile.age() if profile and profile.date_of_birth else None
        is_adult = profile.is_adult() if profile else None
        
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='user_activity',
            title='Onboarding Completed Successfully',
            message=f'User {user.get_full_name() or user.email} completed onboarding',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'user_type': 'UK' if profile and profile.is_uk_user else 'International',
                'age_group': 'adult' if is_adult else 'minor' if age else 'unknown',
                'has_postcode': bool(profile and profile.postcode),
                'email_verified': profile.email_confirmed if profile else False,
                'can_access_comments': profile.can_access_comments if profile else False,
                'profile_data': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'age': age,
                    'is_uk_user': profile.is_uk_user if profile else None,
                    'auth0_provider': profile.last_login_method if profile else None,
                }
            },
            tags=['onboarding', 'registration_complete', 'user_activated'],
            fingerprint=f'onboarding_complete_{user.id}'
        )
    
    @staticmethod
    def log_onboarding_error(user, request, step_name: str, error_type: str, error_details: Dict[str, Any]):
        """Log errors or issues during onboarding."""
        from event_viewer.models import SystemEvent
        
        SystemEvent.objects.create(
            source='user_onboarding',
            level='error',
            category='exception',
            title=f'Onboarding Error: {step_name}',
            message=f'Error during {step_name}: {error_type}',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'step_name': step_name,
                'error_type': error_type,
                'error_details': error_details,
                'user_email': user.email,
            },
            tags=['onboarding', 'error', step_name.lower().replace(' ', '_')],
            fingerprint=f'onboarding_error_{error_type}_{step_name.lower()}'
        )
    
    @staticmethod
    def log_suspicious_activity(request, activity_type: str, details: Dict[str, Any]):
        """Log suspicious registration patterns for security monitoring."""
        from event_viewer.models import SystemEvent
        
        SystemEvent.objects.create(
            source='security',
            level='warning',
            category='security',
            title=f'Suspicious Registration Activity: {activity_type}',
            message=f'Potential {activity_type} detected during registration',
            user=None,  # May not have user object yet
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'activity_type': activity_type,
                'detection_details': details,
                'timestamp': timezone.now().isoformat(),
            },
            tags=['security', 'fraud_detection', 'registration', 'suspicious_activity'],
            fingerprint=f'suspicious_registration_{activity_type}_{date.today()}'
        )