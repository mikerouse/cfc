#!/usr/bin/env python
"""
Test script to verify the financial year dropdown fix
"""
import os
import sys
import django

# Add the current directory to Python path and set up Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from council_finance.models import Council, FinancialYear
from council_finance.views.general import current_financial_year_label

def test_financial_year_dropdown():
    """Test that financial years have proper display text in dropdown"""
    print("Testing financial year dropdown display...")
    
    # Create test data
    council = Council.objects.create(name="Test Council", slug="test-council")
    
    # Create some financial years
    current_year = current_financial_year_label()
    fy1 = FinancialYear.objects.create(label=current_year)
    fy2 = FinancialYear.objects.create(label="2023/24")
    
    print(f"Current year: {current_year}")
    print(f"Created financial years: {[fy.label for fy in FinancialYear.objects.all()]}")
    
    # Test the council detail view
    client = Client()
    response = client.get(reverse('council_detail', args=[council.slug]))
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        # Check the context
        years = response.context.get('years', [])
        print(f"Years in context: {len(years)}")
        
        for year in years:
            display_text = getattr(year, 'display', 'NO DISPLAY ATTRIBUTE')
            print(f"Year {year.label}: display='{display_text}'")
            
            # Verify that current year shows "Current Year to Date"
            if year.label == current_year:
                expected = "Current Year to Date"
                if display_text == expected:
                    print(f"✓ Current year shows correct display: '{display_text}'")
                else:
                    print(f"✗ Current year shows wrong display: '{display_text}' (expected '{expected}')")
            else:
                if display_text == year.label:
                    print(f"✓ Non-current year shows correct display: '{display_text}'")
                else:
                    print(f"✗ Non-current year shows wrong display: '{display_text}' (expected '{year.label}')")
    else:
        print(f"Error: View returned status {response.status_code}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content.decode()[:500]}...")

if __name__ == '__main__':
    test_financial_year_dropdown()
    print("\nTest completed!")
