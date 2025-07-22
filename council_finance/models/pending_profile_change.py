from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import datetime


class PendingProfileChange(models.Model):
    """Store pending updates that require email confirmation."""

    # Change type constants
    CHANGE_TYPES = [
        ('email', 'Email Address'),
        ('password', 'Password'),
        ('profile', 'Profile Information'),
        ('security', 'Security Settings'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES, default='profile')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Enhanced field tracking
    field = models.CharField(max_length=50, help_text="Field being changed")
    old_value = models.TextField(blank=True, help_text="Previous value (for audit)")
    new_value = models.TextField(help_text="New value to be applied")
    
    # Legacy fields for backward compatibility
    new_first_name = models.CharField(max_length=150, blank=True)
    new_last_name = models.CharField(max_length=150, blank=True) 
    new_email = models.EmailField(blank=True)
    new_password = models.CharField(max_length=128, blank=True)
    
    # Enhanced security and tracking
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(default=timezone.now)  # Will be set properly in save()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Security metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(64)
        if not self.expires_at:
            self.expires_at = timezone.now() + datetime.timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Pending {self.change_type} change for {self.user.username} ({self.status})"
    
    @property
    def is_expired(self) -> bool:
        """Check if this change request has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if this change request is valid and can be confirmed."""
        return self.status == 'pending' and not self.is_expired
    
    def confirm(self, applying_user=None) -> bool:
        """Confirm and apply the pending change."""
        if not self.is_valid:
            return False
        
        try:
            if self.change_type == 'email' and self.field == 'email':
                # Apply email change
                old_email = self.user.email
                self.user.email = self.new_value
                self.user.save()
                
                # Update profile
                profile = self.user.profile
                profile.confirm_email()
                profile.clear_pending_email()
                profile.save()
                
            elif self.change_type == 'profile':
                # Apply profile changes based on field
                if self.field == 'first_name':
                    self.user.first_name = self.new_value
                elif self.field == 'last_name':
                    self.user.last_name = self.new_value
                self.user.save()
            
            # Mark as confirmed
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            # Log error but don't raise to prevent email confirmation failures
            print(f"Error applying pending change {self.id}: {e}")
            return False
    
    def cancel(self) -> bool:
        """Cancel this pending change."""
        if self.status == 'pending':
            self.status = 'cancelled'
            self.save()
            return True
        return False
    
    def get_display_info(self) -> dict:
        """Get information suitable for display in templates."""
        return {
            'type': self.get_change_type_display(),
            'field': self.field.replace('_', ' ').title(),
            'new_value': self.new_value if self.field != 'password' else '••••••••',
            'created': self.created_at,
            'expires': self.expires_at,
            'time_remaining': self.expires_at - timezone.now() if not self.is_expired else None,
            'status': self.get_status_display(),
            'is_expired': self.is_expired,
            'is_valid': self.is_valid,
        }

    @classmethod 
    def cleanup_expired(cls):
        """Clean up expired pending changes."""
        expired_changes = cls.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        )
        count = expired_changes.count()
        expired_changes.update(status='expired')
        return count
    
    @classmethod
    def get_pending_for_user(cls, user):
        """Get all valid pending changes for a user."""
        return cls.objects.filter(
            user=user,
            status='pending',
            expires_at__gt=timezone.now()
        ).order_by('-created_at')
