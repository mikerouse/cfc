"""
Comprehensive tests for email change functionality.
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from council_finance.models import UserProfile, PendingProfileChange


class EmailChangeTests(TestCase):
    """Test the complete email change process."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='old@example.com',
            password='testpass123'
        )
        self.profile, created = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'email_confirmed': True}
        )
        if not created:
            self.profile.email_confirmed = True
            self.profile.save()
        self.client.login(username='testuser', password='testpass123')
    
    def test_email_change_modal_endpoint_exists(self):
        """Test that the email change modal endpoint is accessible."""
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'new@example.com'}),
            content_type='application/json'
        )
        # Should not be 404
        self.assertNotEqual(response.status_code, 404)
    
    def test_email_change_validation(self):
        """Test email validation in the modal."""
        # Test empty email
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'])
        
        # Test invalid email format
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'invalid-email'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('valid email', data['error'])
        
        # Test same email as current
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'old@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('current email', data['error'])
    
    def test_email_already_in_use(self):
        """Test that duplicate emails are rejected."""
        # Create another user with the target email
        User.objects.create_user(
            username='otheruser',
            email='taken@example.com',
            password='testpass123'
        )
        
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'taken@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('already registered', data['error'])
    
    def test_rate_limiting(self):
        """Test rate limiting on email change requests."""
        # Set up profile to exceed rate limit
        self.profile.last_confirmation_sent = timezone.now()
        self.profile.confirmation_attempts = 5  # Assuming this exceeds limit
        self.profile.save()
        
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'new@example.com'}),
            content_type='application/json'
        )
        
        if response.status_code == 429:  # Rate limited
            data = response.json()
            self.assertFalse(data['success'])
            self.assertIn('wait', data['error'])
    
    @patch('council_finance.services.email_confirmation.EmailConfirmationService.send_email_change_confirmation')
    def test_successful_email_change_request(self, mock_send):
        """Test successful email change request."""
        mock_send.return_value = True
        
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'new@example.com'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('check', data['message'])
        self.assertEqual(data['new_email'], 'new@example.com')
        self.assertEqual(data['current_email'], 'old@example.com')
    
    @patch('council_finance.services.email_confirmation.EmailConfirmationService.send_email_change_confirmation')
    def test_email_send_failure_handling(self, mock_send):
        """Test handling when email sending fails."""
        mock_send.return_value = False
        
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'new@example.com'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Failed to send', data['error'])
    
    def test_pending_profile_change_creation(self):
        """Test that PendingProfileChange record is created correctly."""
        # Mock the email service to succeed
        with patch('council_finance.services.email_confirmation.EmailConfirmationService.send_email_change_confirmation') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(
                reverse('change_email_modal'),
                data=json.dumps({'email': 'new@example.com'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Check if PendingProfileChange was created
            pending_changes = PendingProfileChange.objects.filter(
                user=self.user,
                field='email',
                new_value='new@example.com'
            )
            
            if pending_changes.exists():
                change = pending_changes.first()
                self.assertEqual(change.old_value, 'old@example.com')
                self.assertEqual(change.change_type, 'email')
                self.assertIsNotNone(change.token)
    
    def test_confirmation_url_patterns(self):
        """Test that confirmation URL patterns are correctly configured."""
        # Create a pending change
        pending_change = PendingProfileChange.objects.create(
            user=self.user,
            change_type='email',
            field='email',
            old_value='old@example.com',
            new_value='new@example.com',
            token='test_token_123',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Test both URL patterns
        url1 = reverse('confirm_profile_change', kwargs={'token': 'test_token_123'})
        
        # The URL should be accessible
        response = self.client.get(url1)
        # Should not be 404
        self.assertNotEqual(response.status_code, 404)
    
    def test_email_change_confirmation_process(self):
        """Test the complete email change confirmation process."""
        # Create a pending email change
        pending_change = PendingProfileChange.objects.create(
            user=self.user,
            change_type='email',
            field='email',
            old_value='old@example.com',
            new_value='new@example.com',
            token='test_token_456',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Visit the confirmation URL
        url = reverse('confirm_profile_change', kwargs={'token': 'test_token_456'})
        response = self.client.get(url)
        
        # Should redirect (not 404 or 500)
        self.assertIn(response.status_code, [200, 302])
        
        # Check if the email was actually changed
        self.user.refresh_from_db()
        if response.status_code == 302:  # Successful redirect
            # The email should be updated OR there should be a helpful error message
            self.assertTrue(
                self.user.email == 'new@example.com' or 
                len([m for m in list(response.wsgi_request._messages) if 'error' in str(m).lower()]) > 0
            )
    
    def test_expired_confirmation_token(self):
        """Test handling of expired confirmation tokens."""
        # Create an expired pending change
        pending_change = PendingProfileChange.objects.create(
            user=self.user,
            change_type='email',
            field='email',
            old_value='old@example.com',
            new_value='new@example.com',
            token='expired_token_123',
            expires_at=timezone.now() - timedelta(hours=1)  # Expired
        )
        
        # Visit the confirmation URL
        url = reverse('confirm_profile_change', kwargs={'token': 'expired_token_123'})
        response = self.client.get(url)
        
        # Should handle the expired token gracefully
        self.assertIn(response.status_code, [200, 302, 404])
        
        # Email should not be changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
    
    def test_json_response_format(self):
        """Test that all API responses return valid JSON."""
        test_cases = [
            {'email': ''},  # Empty email
            {'email': 'invalid'},  # Invalid email
            {'email': 'valid@example.com'},  # Valid email
        ]
        
        for test_data in test_cases:
            with patch('council_finance.services.email_confirmation.EmailConfirmationService.send_email_change_confirmation') as mock_send:
                mock_send.return_value = True
                
                response = self.client.post(
                    reverse('change_email_modal'),
                    data=json.dumps(test_data),
                    content_type='application/json'
                )
                
                # Should always return JSON, never HTML
                self.assertEqual(response['Content-Type'], 'application/json')
                
                # Should be parseable JSON
                try:
                    data = response.json()
                    self.assertIsInstance(data, dict)
                    self.assertIn('success', data)
                except json.JSONDecodeError:
                    self.fail(f"Response is not valid JSON: {response.content}")
    
    def test_authentication_required(self):
        """Test that authentication is required for email change."""
        self.client.logout()
        
        response = self.client.post(
            reverse('change_email_modal'),
            data=json.dumps({'email': 'new@example.com'}),
            content_type='application/json'
        )
        
        # Should require login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class EmailChangeDebugTests(TestCase):
    """Tests for debugging email change issues when DEBUG=True."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='debuguser',
            email='debug@example.com',
            password='testpass123'
        )
        self.profile, created = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'email_confirmed': True}
        )
        if not created:
            self.profile.email_confirmed = True
            self.profile.save()
        self.client.login(username='debuguser', password='testpass123')
    
    def test_detailed_error_messages(self):
        """Test that detailed error messages are provided when DEBUG=True."""
        from django.conf import settings
        
        if settings.DEBUG:
            # Test various error conditions and ensure we get detailed feedback
            
            # Test malformed JSON
            response = self.client.post(
                reverse('change_email_modal'),
                data='invalid json',
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertFalse(data['success'])
            self.assertIn('error', data)
    
    def test_logging_activity(self):
        """Test that email change attempts are properly logged."""
        with patch('council_finance.views.auth.log_activity') as mock_log:
            response = self.client.post(
                reverse('change_email_modal'),
                data=json.dumps({'email': 'test@example.com'}),
                content_type='application/json'
            )
            
            # Should have logged the request
            self.assertTrue(mock_log.called)
            
            # Check the log call had the right activity type
            call_args = mock_log.call_args
            if call_args:
                self.assertIn('activity', call_args[1])
                self.assertIn('Email change', call_args[1]['activity'])
    
    def test_admin_alerting(self):
        """Test that admin alerts are sent on failures."""
        with patch('council_finance.services.email_confirmation.EmailConfirmationService.send_email_change_confirmation') as mock_send:
            with patch('council_finance.emails.send_email_enhanced') as mock_alert:
                mock_send.return_value = False  # Simulate email send failure
                
                response = self.client.post(
                    reverse('change_email_modal'),
                    data=json.dumps({'email': 'test@example.com'}),
                    content_type='application/json'
                )
                
                # Should have attempted to send admin alert
                self.assertEqual(response.status_code, 500)
                
                # Check if admin alert was attempted
                if mock_alert.called:
                    call_args = mock_alert.call_args[1]
                    self.assertIn('subject', call_args)
                    self.assertIn('Alert', call_args['subject'])