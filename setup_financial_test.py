#!/usr/bin/env python3
"""
Quick test to create financial fields and fix API issues
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import DataField, FinancialYear, Council

def create_sample_fields():
    """Create sample financial fields for testing."""
    
    print("Creating sample financial fields...")
    
    # Financial field data
    fields_data = [
        # Balance Sheet
        {'name': 'Total Assets', 'slug': 'total_assets', 'category': 'balance_sheet', 'content_type': 'monetary'},
        {'name': 'Current Assets', 'slug': 'current_assets', 'category': 'balance_sheet', 'content_type': 'monetary'},
        {'name': 'Fixed Assets', 'slug': 'fixed_assets', 'category': 'balance_sheet', 'content_type': 'monetary'},
        {'name': 'Total Liabilities', 'slug': 'total_liabilities', 'category': 'balance_sheet', 'content_type': 'monetary'},
        
        # Cash Flow
        {'name': 'Operating Cash Flow', 'slug': 'operating_cash_flow', 'category': 'cash_flow', 'content_type': 'monetary'},
        {'name': 'Investment Cash Flow', 'slug': 'investment_cash_flow', 'category': 'cash_flow', 'content_type': 'monetary'},
        {'name': 'Financing Cash Flow', 'slug': 'financing_cash_flow', 'category': 'cash_flow', 'content_type': 'monetary'},
        
        # Income
        {'name': 'Council Tax Revenue', 'slug': 'council_tax_revenue', 'category': 'income', 'content_type': 'monetary'},
        {'name': 'Government Grants', 'slug': 'government_grants', 'category': 'income', 'content_type': 'monetary'},
        {'name': 'Business Rates', 'slug': 'business_rates', 'category': 'income', 'content_type': 'monetary'},
        
        # Spending
        {'name': 'Staff Costs', 'slug': 'staff_costs', 'category': 'spending', 'content_type': 'monetary'},
        {'name': 'Service Delivery Costs', 'slug': 'service_delivery_costs', 'category': 'spending', 'content_type': 'monetary'},
        {'name': 'Infrastructure Investment', 'slug': 'infrastructure_investment', 'category': 'spending', 'content_type': 'monetary'},
    ]
    
    created_count = 0
    for field_data in fields_data:
        field, created = DataField.objects.get_or_create(
            slug=field_data['slug'],
            defaults=field_data
        )
        if created:
            created_count += 1
            print(f"✓ Created: {field.name} ({field.category})")
        else:
            print(f"  Exists: {field.name} ({field.category})")
    
    print(f"\nCreated {created_count} new fields")
    
    # Ensure we have a financial year
    year, created = FinancialYear.objects.get_or_create(
        label='2025/26',
        defaults={'display': '2025/26'}
    )
    if created:
        print(f"✓ Created financial year: {year.label}")
    else:
        print(f"  Financial year exists: {year.label}")
    
    # Check councils
    council_count = Council.objects.count()
    print(f"Councils in database: {council_count}")
    
    if council_count > 0:
        sample_council = Council.objects.first()
        print(f"Sample council: {sample_council.slug}")
    
    return True

def test_api_function():
    """Test the financial_data_api function directly."""
    
    from django.test import RequestFactory
    from django.contrib.auth.models import User
    from council_finance.views.councils import financial_data_api
    import json
    
    print("\nTesting financial_data_api function...")
    
    try:
        # Get or create a test council
        council = Council.objects.first()
        if not council:
            council = Council.objects.create(
                name="Test Council",
                slug="test-council"
            )
        
        # Create a superuser for testing
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'is_superuser': True}
        )
        
        # Test the API
        factory = RequestFactory()
        request = factory.get(f'/councils/{council.slug}/financial-data/?year=2025%2F26')
        request.user = user
        
        response = financial_data_api(request, council.slug)
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print("✓ API call successful")
            print(f"Categories: {data.get('categories', [])}")
            print(f"Fields by category: {list(data.get('fields_by_category', {}).keys())}")
        else:
            print(f"❌ API call failed")
            print(f"Response: {response.content}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Financial Data Setup and Test")
    print("=" * 40)
    
    try:
        create_sample_fields()
        test_api_function()
        print("\n✅ Setup completed successfully")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
