"""
Integration tests for the new Council Edit React interface.

Tests the complete pipeline from URL routing to API responses.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from council_finance.models import Council, FinancialYear, DataField
import json


class CouncilEditIntegrationTests(TestCase):
    """Test the complete council edit React interface integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test council
        self.council = Council.objects.create(
            name='Test Council',
            slug='test-council',
            website='https://example.com'
        )
        
        # Create test financial year
        self.year = FinancialYear.objects.create(
            label='2024/25',
            start_date='2024-04-01',
            end_date='2025-03-31'
        )
    
    def test_council_edit_url_resolves(self):
        """Test that the React edit URL resolves correctly."""
        url = reverse('council_edit', args=[self.council.slug])
        self.assertEqual(url, f'/councils/{self.council.slug}/edit/')
    
    def test_characteristics_api_url_resolves(self):
        """Test that characteristics API URL resolves correctly."""
        url = reverse('council_characteristics_api', args=[self.council.slug])
        self.assertEqual(url, f'/api/council/{self.council.slug}/characteristics/')
    
    def test_characteristics_api_returns_valid_json(self):
        """Test that characteristics API returns valid JSON."""
        url = reverse('council_characteristics_api', args=[self.council.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('characteristics', data)
        self.assertIn('available_fields', data)
    
    def test_years_api_returns_valid_data(self):
        """Test that years API returns valid financial year data."""
        url = reverse('council_available_years_api', args=[self.council.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data.get('success'))
        self.assertIn('years', data)
        self.assertIsInstance(data['years'], list)
        
        if data['years']:
            year_data = data['years'][0]
            required_fields = ['id', 'label', 'display']
            for field in required_fields:
                self.assertIn(field, year_data)
    
    def test_temporal_data_api_requires_year_id(self):
        """Test that temporal data API requires a year ID."""
        url = reverse('council_temporal_data_api', args=[self.council.slug, self.year.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data.get('success'))
        self.assertIn('year', data)
        self.assertIn('general', data)
        self.assertIn('financial', data)
    
    def test_context_api_provides_complete_data(self):
        """Test that context API provides all necessary data for React."""
        url = reverse('council_edit_context_api', args=[self.council.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data.get('success'))
        self.assertIn('council', data)
        self.assertIn('years', data)
        self.assertIn('fields', data)
        
        # Check council data structure
        council_data = data['council']
        self.assertEqual(council_data['slug'], self.council.slug)
        self.assertEqual(council_data['name'], self.council.name)
    
    def test_council_edit_page_loads(self):
        """Test that the React edit page loads without errors."""
        url = reverse('council_edit', args=[self.council.slug])
        response = self.client.get(url)
        
        # Should return the template (200) or redirect for auth (302)
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            content = response.content.decode()
            self.assertIn('council-edit-react-root', content)
            self.assertIn('CouncilEditApp', content)
    
    def test_api_endpoints_require_authentication(self):
        """Test that API endpoints require user authentication."""
        # Log out the user
        self.client.logout()
        
        endpoints = [
            reverse('council_characteristics_api', args=[self.council.slug]),
            reverse('council_available_years_api', args=[self.council.slug]),
            reverse('council_edit_context_api', args=[self.council.slug]),
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should redirect to login or return 403/401
            self.assertIn(response.status_code, [302, 401, 403])
    
    def test_nonexistent_council_returns_404(self):
        """Test that nonexistent council returns 404."""
        url = reverse('council_characteristics_api', args=['nonexistent-council'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class SyntaxValidationTests(TestCase):
    """Test that all new files have valid syntax."""
    
    def test_council_edit_api_imports(self):
        """Test that council edit API can be imported."""
        try:
            from council_finance.views.council_edit_api import (
                council_characteristics_api,
                save_council_characteristic_api,
                council_temporal_data_api,
                save_temporal_data_api,
                council_available_years_api,
                council_edit_context_api,
            )
        except ImportError as e:
            self.fail(f"Council edit API import failed: {e}")
        except SyntaxError as e:
            self.fail(f"Council edit API syntax error: {e}")
    
    def test_councils_view_imports(self):
        """Test that updated councils view can be imported."""
        try:
            from council_finance.views.councils import council_edit
        except ImportError as e:
            self.fail(f"Council edit view import failed: {e}")
        except SyntaxError as e:
            self.fail(f"Council edit view syntax error: {e}")
    
    def test_url_configuration_loads(self):
        """Test that URL configuration loads without errors."""
        try:
            from council_finance import urls
            from django.urls import reverse
            
            # Test that key URLs can be reversed
            reverse('council_edit', args=['test'])
            reverse('council_characteristics_api', args=['test'])
            
        except Exception as e:
            self.fail(f"URL configuration error: {e}")