"""
Email Confirmation Service

Comprehensive email confirmation system with support for various confirmation types,
rate limiting, and preparation for SSO integration.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.http import HttpRequest

from council_finance.models import UserProfile, PendingProfileChange
from council_finance.emails import send_email_enhanced as send_email

logger = logging.getLogger(__name__)


class EmailConfirmationService:
    """Service for handling all email confirmation operations."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@councilfinance.com')
    
    def _safe_log_activity(self, request, activity, details=None, extra=None):
        """Safely log activity, avoiding circular imports."""
        try:
            from council_finance.views.general import log_activity
            log_activity(request, activity=activity, details=details, extra=extra)
        except ImportError:
            logger.info(f"Activity: {activity}" + (f" - {details}" if details else ""))
    
    def send_initial_confirmation(self, user: User, request: HttpRequest = None) -> bool:
        """Send initial email confirmation for new users."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Check rate limiting
            if not profile.can_send_confirmation():
                logger.warning(f"Rate limit exceeded for user {user.username}")
                return False
            
            # Generate token
            token = profile.generate_confirmation_token()
            profile.last_confirmation_sent = timezone.now()
            profile.confirmation_attempts += 1
            profile.save()
            
            # Build confirmation URL
            confirm_url = self._build_confirmation_url('confirm_email', token, request)
            
            # Send email
            success = send_email(
                to_email=user.email,
                subject='Welcome! Please confirm your email address',
                template='emails/initial_confirmation.html',
                context={
                    'user': user,
                    'confirm_url': confirm_url,
                    'site_name': 'Council Finance Counters',
                }
            )
            
            if success and request:
                self._safe_log_activity(
                    request,
                    activity=f"Initial confirmation email sent to {user.username}",
                    details=f"Email: {user.email}, Token: {token[:10]}..."
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send initial confirmation to {user.username}: {e}")
            return False
    
    def send_reconfirmation(self, user: User, reason: str = "security_change", request: HttpRequest = None) -> bool:
        """Send re-confirmation email after security changes."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Check rate limiting
            if not profile.can_send_confirmation():
                logger.warning(f"Rate limit exceeded for reconfirmation {user.username}")
                return False
            
            # Mark as requiring reconfirmation
            profile.require_reconfirmation(reason)
            
            # Generate token
            token = profile.generate_confirmation_token()
            profile.last_confirmation_sent = timezone.now()
            profile.confirmation_attempts += 1
            profile.save()
            
            # Build confirmation URL
            confirm_url = self._build_confirmation_url('confirm_email', token, request)
            
            # Determine email content based on reason
            template, subject = self._get_reconfirmation_template(reason)
            
            # Send email
            success = send_email(
                to_email=user.email,
                subject=subject,
                template=template,
                context={
                    'user': user,
                    'confirm_url': confirm_url,
                    'reason': reason,
                    'reason_display': self._get_reason_display(reason),
                }
            )
            
            if success and request:
                self._safe_log_activity(
                    request,
                    activity=f"Re-confirmation email sent to {user.username}",
                    details=f"Reason: {reason}, Email: {user.email}"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send reconfirmation to {user.username}: {e}")
            return False
    
    def send_email_change_confirmation(self, user: User, new_email: str, request: HttpRequest = None) -> bool:
        """Send confirmation email for email address changes."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Check rate limiting
            if not profile.can_send_confirmation():
                logger.warning(f"Rate limit exceeded for email change {user.username}")
                return False
            
            # Set up pending email change
            token = profile.generate_pending_email_token()
            profile.pending_email = new_email
            profile.last_confirmation_sent = timezone.now()
            profile.confirmation_attempts += 1
            profile.save()
            
            # Create pending change record
            pending_change = PendingProfileChange.objects.create(
                user=user,
                change_type='email',
                field='email',
                old_value=user.email,
                new_value=new_email,
                token=token,
                ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            )
            
            # Build confirmation URL
            confirm_url = self._build_confirmation_url('confirm_profile_change', token, request)
            
            # Send confirmation to NEW email address
            success = send_email(
                to_email=new_email,
                subject='Confirm your new email address',
                template='emails/email_change_confirmation.html',
                context={
                    'user': user,
                    'old_email': user.email,
                    'new_email': new_email,
                    'confirm_url': confirm_url,
                }
            )
            
            # Send security notification to OLD email address
            if success:
                send_email(
                    to_email=user.email,
                    subject='Security Alert: Email address change requested',
                    template='emails/email_change_notification.html',
                    context={
                        'user': user,
                        'old_email': user.email,
                        'new_email': new_email,
                        'requested_at': timezone.now(),
                        'ip_address': self._get_client_ip(request) if request else 'Unknown',
                    }
                )
            
            if success and request:
                self._safe_log_activity(
                    request,
                    activity=f"Email change confirmation sent to {user.username}",
                    extra=f"From: {user.email} To: {new_email}"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send email change confirmation to {user.username}: {e}")
            return False
    
    def confirm_email_by_token(self, token: str, request: HttpRequest = None) -> Dict[str, Any]:
        """Confirm email using token from email link."""
        try:
            # Try profile confirmation first
            try:
                profile = UserProfile.objects.get(confirmation_token=token)
                if profile.confirmation_token == token and token:
                    profile.confirm_email()
                    profile.save()
                    
                    if request:
                        self._safe_log_activity(
                            request,
                            activity=f"Email confirmed for {profile.user.username}",
                            details=f"Email: {profile.user.email}"
                        )
                    
                    return {
                        'success': True,
                        'message': 'Email confirmed successfully!',
                        'user': profile.user,
                        'confirmation_type': 'initial'
                    }
            except UserProfile.DoesNotExist:
                pass
            
            # Try pending email change confirmation
            try:
                pending_change = PendingProfileChange.objects.get(
                    token=token,
                    status='pending'
                )
                
                if pending_change.is_valid:
                    success = pending_change.confirm()
                    if success:
                        if request:
                            self._safe_log_activity(
                                request,
                                activity=f"Email change confirmed for {pending_change.user.username}",
                                details=f"New email: {pending_change.new_value}"
                            )
                        
                        return {
                            'success': True,
                            'message': 'Email address changed successfully!',
                            'user': pending_change.user,
                            'confirmation_type': 'email_change'
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Failed to apply email change. Please try again.',
                            'confirmation_type': 'email_change'
                        }
                else:
                    return {
                        'success': False,
                        'message': 'Confirmation link has expired. Please request a new one.',
                        'confirmation_type': 'email_change'
                    }
                    
            except PendingProfileChange.DoesNotExist:
                pass
            
            # Token not found
            return {
                'success': False,
                'message': 'Invalid or expired confirmation link.',
                'confirmation_type': 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Error confirming email with token {token[:10]}...: {e}")
            return {
                'success': False,
                'message': 'An error occurred during confirmation. Please try again.',
                'confirmation_type': 'error'
            }
    
    def get_confirmation_status(self, user: User) -> Dict[str, Any]:
        """Get comprehensive confirmation status for a user."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            status = profile.get_confirmation_status()
            
            # Add pending changes
            pending_changes = PendingProfileChange.get_pending_for_user(user)
            status['pending_changes'] = [change.get_display_info() for change in pending_changes]
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting confirmation status for {user.username}: {e}")
            return {
                'email_confirmed': False,
                'requires_reconfirmation': True,
                'confirmation_status': 'Error retrieving status',
                'pending_changes': []
            }
    
    def cancel_pending_email_change(self, user: User) -> bool:
        """Cancel any pending email changes for a user."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.clear_pending_email()
            profile.save()
            
            # Cancel any pending change records
            PendingProfileChange.objects.filter(
                user=user,
                change_type='email',
                status='pending'
            ).update(status='cancelled')
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling pending email change for {user.username}: {e}")
            return False
    
    def cleanup_expired_confirmations(self) -> Dict[str, int]:
        """Clean up expired confirmation tokens and pending changes."""
        try:
            # Clean up expired pending changes
            expired_changes = PendingProfileChange.cleanup_expired()
            
            # Clean up expired profile tokens
            expired_profiles = UserProfile.objects.filter(
                pending_email_expires__lt=timezone.now(),
                pending_email__isnull=False
            ).exclude(pending_email='')
            
            expired_profile_count = expired_profiles.count()
            for profile in expired_profiles:
                profile.clear_pending_email()
                profile.save()
            
            return {
                'expired_changes': expired_changes,
                'expired_profile_tokens': expired_profile_count
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {'expired_changes': 0, 'expired_profile_tokens': 0}
    
    def _build_confirmation_url(self, url_name: str, token: str, request: HttpRequest = None) -> str:
        """Build confirmation URL."""
        if request:
            return request.build_absolute_uri(
                reverse(url_name, kwargs={'token': token})
            )
        else:
            # Fallback for background tasks
            base_url = getattr(settings, 'SITE_URL', 'https://councilfinance.com')
            relative_url = reverse(url_name, kwargs={'token': token})
            return f"{base_url}{relative_url}"
    
    def _get_reconfirmation_template(self, reason: str) -> tuple:
        """Get template and subject for reconfirmation based on reason."""
        templates = {
            'password_change': ('emails/reconfirm_password_change.html', 'Please re-confirm your email after password change'),
            'security_change': ('emails/reconfirm_security.html', 'Please re-confirm your email for security'),
            'suspicious_activity': ('emails/reconfirm_suspicious.html', 'Security alert: Please confirm your email'),
        }
        
        return templates.get(reason, ('emails/reconfirm_general.html', 'Please re-confirm your email address'))
    
    def _get_reason_display(self, reason: str) -> str:
        """Get human-readable reason display."""
        reasons = {
            'password_change': 'password was changed',
            'security_change': 'security settings were modified', 
            'suspicious_activity': 'suspicious activity was detected',
        }
        return reasons.get(reason, 'security-related changes were made')
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip


# Global service instance
email_confirmation_service = EmailConfirmationService()

# Convenience functions
def send_confirmation_email(user: User, request: HttpRequest = None) -> bool:
    """Send confirmation email - convenience function."""
    return email_confirmation_service.send_initial_confirmation(user, request)

def send_reconfirmation_email(user: User, reason: str = "security_change", request: HttpRequest = None) -> bool:
    """Send re-confirmation email - convenience function."""
    return email_confirmation_service.send_reconfirmation(user, reason, request)

def send_email_change_confirmation(user: User, new_email: str, request: HttpRequest = None) -> bool:
    """Send email change confirmation - convenience function."""
    return email_confirmation_service.send_email_change_confirmation(user, new_email, request)

def confirm_email_token(token: str, request: HttpRequest = None) -> Dict[str, Any]:
    """Confirm email by token - convenience function."""
    return email_confirmation_service.confirm_email_by_token(token, request)