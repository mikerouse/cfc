#!/usr/bin/env python
"""Test the financial year dropdown fix"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from council_finance.models import Council
from council_finance.views.general import current_financial_year_label

def test_dropdown_fix():
    """Test that the financial year dropdown now works correctly"""
    print("Testing financial year dropdown fix...")
    
    # Get a test council
    council = Council.objects.first()
    if not council:
        print("❌ No councils found in database")
        return False
        
    print(f"📋 Testing with council: {council.name} ({council.slug})")
    
    # Get current financial year
    current_year = current_financial_year_label()
    print(f"📅 Current financial year: {current_year}")
    
    # Test the council detail view
    client = Client()
    response = client.get(reverse('council_detail', args=[council.slug]))
    
    print(f"🌐 HTTP Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Failed to load page (status {response.status_code})")
        return False
    
    # Check context data
    years = response.context.get('years', [])
    print(f"📊 Financial years in context: {len(years)}")
    
    if not years:
        print("❌ No financial years found in context")
        return False
    
    # Test each year's display property
    success = True
    for year in years:
        if not hasattr(year, 'display'):
            print(f"❌ Year {year.label} missing display property")
            success = False
            continue
            
        display = year.display
        expected = "Current Year to Date" if year.label == current_year else year.label
        
        if display == expected:
            status = "✅"
        else:
            status = "❌"
            success = False
            
        print(f"{status} {year.label}: '{display}' (expected: '{expected}')")
    
    return success

if __name__ == '__main__':
    try:
        success = test_dropdown_fix()
        if success:
            print("\n🎉 All tests passed! Financial year dropdown fix is working correctly.")
        else:
            print("\n❌ Some tests failed. Check output above.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)
