"""
Test the financial_data_api endpoint directly to debug the 500 error
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from council_finance.models import Council, DataField, FinancialYear, UserProfile, Tier
from council_finance.views.councils import financial_data_api
import json

def test_financial_api():
    """Test the financial_data_api endpoint."""
    
    print("Testing financial_data_api endpoint...")
    
    # Create test data
    try:
        # Create a test council if it doesn't exist
        council, created = Council.objects.get_or_create(
            slug='test-council',
            defaults={
                'name': 'Test Council',
                'council_type': 'District Council'
            }
        )
        print(f"✓ Test council: {council.name} ({'created' if created else 'exists'})")
        
        # Create a test user and profile
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_superuser': True
            }
        )
        print(f"✓ Test user: {user.username} ({'created' if created else 'exists'})")
        
        # Create a test financial year
        year, created = FinancialYear.objects.get_or_create(
            label='2025/26',
            defaults={'display': '2025/26'}
        )
        print(f"✓ Test year: {year.label} ({'created' if created else 'exists'})")
        
        # Create test financial fields
        categories = ['balance_sheet', 'cash_flow', 'income', 'spending']
        for category in categories:
            field, created = DataField.objects.get_or_create(
                slug=f'test_{category}_field',
                defaults={
                    'name': f'Test {category.replace("_", " ").title()} Field',
                    'category': category,
                    'content_type': 'monetary',
                    'explanation': f'Test field for {category}'
                }
            )
            if created:
                print(f"✓ Created field: {field.name}")
        
        # Test the API endpoint
        factory = RequestFactory()
        request = factory.get('/councils/test-council/financial-data/?year=2025%2F26')
        request.user = user
        
        print("\nTesting API call...")
        response = financial_data_api(request, 'test-council')
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print("✓ API call successful")
            print(f"Categories returned: {len(data.get('categories', []))}")
            print(f"Fields by category: {list(data.get('fields_by_category', {}).keys())}")
            
            for category, fields in data.get('fields_by_category', {}).items():
                print(f"  {category}: {len(fields)} fields")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            try:
                error_data = json.loads(response.content)
                print(f"Error: {error_data}")
            except:
                print(f"Response content: {response.content}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_financial_api()
    if success:
        print("\n✅ Financial API test passed")
    else:
        print("\n❌ Financial API test failed")
