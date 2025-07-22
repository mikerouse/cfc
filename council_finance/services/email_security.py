"""
Security service for enhanced protection of email change operations.
"""

import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from django.contrib.auth.models import User
from council_finance.models import UserProfile
import hashlib
import datetime

logger = logging.getLogger(__name__)


class EmailChangeSecurityService:
    """Enhanced security service for email change operations."""
    
    def __init__(self):
        self.ip_rate_limit_window = 3600  # 1 hour in seconds
        self.ip_max_attempts = 10  # Max attempts per IP per hour
        self.user_rate_limit_window = 1800  # 30 minutes in seconds
        self.user_max_attempts = 3  # Max attempts per user per 30 minutes
        
    def get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_rate_limit_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key for rate limiting."""
        hashed_id = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"email_change_{prefix}_{hashed_id}"
    
    def check_ip_rate_limit(self, request: HttpRequest) -> Dict[str, Any]:
        """Check if IP has exceeded rate limit."""
        ip = self.get_client_ip(request)
        cache_key = self.get_rate_limit_key("ip", ip)
        
        attempts = cache.get(cache_key, 0)
        
        if attempts >= self.ip_max_attempts:
            # Calculate time remaining
            remaining_time = cache.ttl(cache_key)
            return {
                'allowed': False,
                'reason': 'IP rate limit exceeded',
                'attempts': attempts,
                'max_attempts': self.ip_max_attempts,
                'reset_in_seconds': remaining_time,
                'reset_in_minutes': max(1, remaining_time // 60)
            }
        
        return {
            'allowed': True,
            'attempts': attempts,
            'max_attempts': self.ip_max_attempts,
            'remaining': self.ip_max_attempts - attempts
        }
    
    def check_user_rate_limit(self, user: User) -> Dict[str, Any]:
        """Check if user has exceeded rate limit."""
        cache_key = self.get_rate_limit_key("user", str(user.id))
        
        attempts = cache.get(cache_key, 0)
        
        if attempts >= self.user_max_attempts:
            remaining_time = cache.ttl(cache_key)
            return {
                'allowed': False,
                'reason': 'User rate limit exceeded',
                'attempts': attempts,
                'max_attempts': self.user_max_attempts,
                'reset_in_seconds': remaining_time,
                'reset_in_minutes': max(1, remaining_time // 60)
            }
        
        return {
            'allowed': True,
            'attempts': attempts,
            'max_attempts': self.user_max_attempts,
            'remaining': self.user_max_attempts - attempts
        }
    
    def record_attempt(self, request: HttpRequest, user: User, success: bool = False):
        """Record an email change attempt for rate limiting."""
        ip = self.get_client_ip(request)
        
        # Record IP attempt
        ip_cache_key = self.get_rate_limit_key("ip", ip)
        ip_attempts = cache.get(ip_cache_key, 0) + 1
        cache.set(ip_cache_key, ip_attempts, self.ip_rate_limit_window)
        
        # Record user attempt (only if failed, to prevent abuse)
        if not success:
            user_cache_key = self.get_rate_limit_key("user", str(user.id))
            user_attempts = cache.get(user_cache_key, 0) + 1
            cache.set(user_cache_key, user_attempts, self.user_rate_limit_window)
    
    def validate_security_constraints(self, request: HttpRequest, user: User, new_email: str) -> Dict[str, Any]:
        """Comprehensive security validation for email change requests."""
        
        # Check IP rate limiting
        ip_check = self.check_ip_rate_limit(request)
        if not ip_check['allowed']:
            return {
                'valid': False,
                'error': f"Too many email change attempts from your IP address. Please try again in {ip_check['reset_in_minutes']} minutes.",
                'error_code': 'IP_RATE_LIMIT',
                'details': ip_check
            }
        
        # Check user rate limiting
        user_check = self.check_user_rate_limit(user)
        if not user_check['allowed']:
            return {
                'valid': False,
                'error': f"You've made too many email change requests. Please try again in {user_check['reset_in_minutes']} minutes.",
                'error_code': 'USER_RATE_LIMIT',
                'details': user_check
            }
        
        # Check user profile rate limiting (existing logic)
        profile, created = UserProfile.objects.get_or_create(user=user)
        if not profile.can_send_confirmation():
            return {
                'valid': False,
                'error': 'Please wait before requesting another email change. You can try again in a few minutes.',
                'error_code': 'PROFILE_RATE_LIMIT',
                'details': {'profile_limited': True}
            }
        
        # Additional security checks
        if user.email.lower() == new_email.lower():
            return {
                'valid': False,
                'error': 'This is already your current email address',
                'error_code': 'SAME_EMAIL',
                'details': {}
            }
        
        # Check for suspicious patterns (rapid email changes to same domain)
        if self._check_suspicious_patterns(user, new_email):
            return {
                'valid': False,
                'error': 'Email change request flagged for security review. Please contact support.',
                'error_code': 'SUSPICIOUS_PATTERN',
                'details': {}
            }
        
        return {
            'valid': True,
            'ip_info': ip_check,
            'user_info': user_check
        }
    
    def _check_suspicious_patterns(self, user: User, new_email: str) -> bool:
        """Check for suspicious email change patterns."""
        # Get domain from new email
        new_domain = new_email.split('@')[1].lower() if '@' in new_email else ''
        
        # Check recent email change attempts to same domain
        domain_key = self.get_rate_limit_key("domain", f"{user.id}_{new_domain}")
        domain_attempts = cache.get(domain_key, 0)
        
        if domain_attempts >= 3:  # More than 3 attempts to same domain in 24 hours
            return True
        
        # Record this domain attempt
        cache.set(domain_key, domain_attempts + 1, 86400)  # 24 hours
        
        return False
    
    def log_security_event(self, request: HttpRequest, user: User, event_type: str, details: Dict[str, Any]):
        """Log security events for monitoring."""
        try:
            from council_finance.views.general import log_activity
            
            log_activity(
                request,
                activity=f"Email change security event: {event_type}",
                extra=f"User: {user.username}, IP: {self.get_client_ip(request)}, Details: {details}"
            )
        except ImportError:
            logger.warning(f"Email change security event - {event_type}: User {user.username}, Details: {details}")


# Global instance
email_security_service = EmailChangeSecurityService()
