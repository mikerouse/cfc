#!/usr/bin/env python
"""Test script to verify God Mode view is working correctly."""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from council_finance.models import FinancialYear
from council_finance.views.admin import god_mode

def test_god_mode_view():
    """Test that God Mode view returns financial years in context."""
    print("Testing God Mode view...")
    
    # Create a test request
    factory = RequestFactory()
    request = factory.get('/god-mode/')
    
    # Create a test user
    user = User.objects.create_user(username='testuser', password='testpass')
    request.user = user
    
    # Call the view
    response = god_mode(request)
    
    # Check that the response is successful
    print(f"Response status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Check that financial years are in context
    context = response.context_data
    financial_years = context.get('financial_years', [])
    
    print(f"Financial years in context: {len(financial_years)}")
    for year in financial_years:
        print(f"  - {year.label} (Current: {year.is_current})")
    
    # Verify we have financial years
    assert len(financial_years) > 0, "No financial years found in context"
    
    # Check specific context variables
    expected_vars = [
        'financial_years',
        'user_activity_surveillance',
        'data_quality_surveillance',
        'security_monitoring',
        'all_councils',
    ]
    
    for var in expected_vars:
        assert var in context, f"Missing context variable: {var}"
        print(f"✓ Context variable '{var}' present")
    
    print("✓ God Mode view test passed!")
    return True

if __name__ == '__main__':
    try:
        test_god_mode_view()
        print("\n🎉 All tests passed! God Mode view is working correctly.")
        print("The financial years should now be visible in the God Mode panel.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
