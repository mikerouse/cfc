#!/usr/bin/env python3
"""
Test script to create sample financial data and validate the complete editing workflow.
"""

import os
import sys
import django

# Setup Django
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cfc.settings')

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    # Try alternative setup
    sys.path.insert(0, os.path.join(current_dir, '..'))
    django.setup()

from django.contrib.auth.models import User
from council_finance.models import Council, FinancialYear, DataField, FinancialFigure
from council_finance.utils.year_utils import current_financial_year_label

def create_test_data():
    """Create comprehensive test data for the financial editing workflow."""
    
    print("🔧 Creating test data for complete workflow validation...")
    
    # Get or create the test council
    council, created = Council.objects.get_or_create(
        slug='test-council',
        defaults={
            'name': 'Test Borough Council',
            'short_name': 'TBC',
            'active': True
        }
    )
    
    if created:
        print(f"✅ Created test council: {council.name}")
    else:
        print(f"📋 Using existing council: {council.name}")
    
    # Get current financial year
    current_year_label = current_financial_year_label()
    financial_year, created = FinancialYear.objects.get_or_create(
        label=current_year_label,
        defaults={'label': current_year_label}
    )
    
    if created:
        print(f"✅ Created financial year: {financial_year.label}")
    else:
        print(f"📋 Using existing financial year: {financial_year.label}")
    
    # Get financial data fields
    financial_fields = DataField.objects.filter(category='financial')
    
    if not financial_fields.exists():
        print("❌ No financial fields found. Creating sample fields...")
        
        # Create sample financial fields
        sample_fields = [
            {
                'slug': 'total_revenue', 
                'name': 'Total Revenue',
                'category': 'financial',
                'explanation': 'Total revenue for the financial year',
                'field_type': 'currency'
            },
            {
                'slug': 'total_expenditure',
                'name': 'Total Expenditure', 
                'category': 'financial',
                'explanation': 'Total expenditure for the financial year',
                'field_type': 'currency'
            },
            {
                'slug': 'council_tax_income',
                'name': 'Council Tax Income',
                'category': 'financial',
                'explanation': 'Income from council tax',
                'field_type': 'currency'
            }
        ]
        
        for field_data in sample_fields:
            field, created = DataField.objects.get_or_create(
                slug=field_data['slug'],
                defaults=field_data
            )
            if created:
                print(f"✅ Created field: {field.name}")
        
        financial_fields = DataField.objects.filter(category='financial')
    
    # Create some sample financial figures
    figures_created = 0
    for field in financial_fields[:3]:  # Limit to first 3 fields
        figure, created = FinancialFigure.objects.get_or_create(
            council=council,
            field=field,
            year=financial_year,
            defaults={
                'value': f'{1000000 + field.id * 100000}',  # Sample values
                'source_document': 'Annual Statement of Accounts 2023/24'
            }
        )
        
        if created:
            figures_created += 1
            print(f"✅ Created figure: {field.name} = £{figure.value}")
    
    print(f"📊 Created {figures_created} new financial figures")
    
    # Test the API endpoint
    print("\n🔍 Testing financial data API...")
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        
        # Create test client
        client = Client()
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"✅ Created test user: {user.username}")
        
        # Login
        client.force_login(user)
        
        # Test API endpoint
        response = client.get(f'/council/{council.slug}/financial-data-api/')
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API test successful - {len(data.get('categories', {}))} categories returned")
            
            # Print sample data structure
            for category, fields in data.get('categories', {}).items():
                print(f"   📁 {category}: {len(fields)} fields")
                for field in fields[:2]:  # Show first 2 fields per category
                    print(f"      💰 {field['name']}: £{field.get('value', 'No data')}")
        else:
            print(f"❌ API test failed - Status: {response.status_code}")
            print(f"   Response: {response.content.decode()[:200]}...")
            
    except Exception as e:
        print(f"❌ Error testing API: {str(e)}")
    
    print("\n🎯 Test data creation complete!")
    print(f"   📍 Council: {council.name} (slug: {council.slug})")
    print(f"   📅 Financial Year: {financial_year.label}")
    print(f"   📊 Financial Fields: {financial_fields.count()}")
    print(f"   💰 Financial Figures: {FinancialFigure.objects.filter(council=council, year=financial_year).count()}")
    
    print(f"\n🌐 Test URLs:")
    print(f"   📝 Edit page: http://localhost:8000/council/{council.slug}/?tab=edit")
    print(f"   📊 API endpoint: http://localhost:8000/council/{council.slug}/financial-data-api/")

if __name__ == '__main__':
    create_test_data()
