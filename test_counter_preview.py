#!/usr/bin/env python3
"""
Test script for counter preview functionality
"""
import os
import sys
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.views.admin import preview_counter_value
from django.test import RequestFactory
from django.contrib.auth.models import User

def test_counter_preview():
    """Test the counter preview functionality"""
    
    print("🧪 Testing Counter Preview Functionality")
    print("=" * 50)
    
    # Create mock request
    factory = RequestFactory()
    
    # Test cases
    test_cases = [
        {
            'name': 'Aberdeen - 2024/25 - Calculated Field',
            'params': {
                'council': 'aberdeen-city-council',
                'year': '2024/25',
                'formula': 'non-ring-fenced-government-grant-income-per-capita',
                'precision': '0',
                'show_currency': 'true',
                'friendly_format': 'false'
            }
        },
        {
            'name': 'Worcestershire - 2024/25 - Calculated Field',
            'params': {
                'council': 'worcestershire',
                'year': '2024/25',
                'formula': 'non-ring-fenced-government-grant-income-per-capita',
                'precision': '0',
                'show_currency': 'true',
                'friendly_format': 'false'
            }
        },
        {
            'name': 'Simple Formula Test',
            'params': {
                'council': 'worcestershire',
                'year': '2024/25',
                'formula': '1000 + 500',
                'precision': '0',
                'show_currency': 'true',
                'friendly_format': 'false'
            }
        }
    ]
    
    # Get a superuser for authentication
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("❌ No superuser found. Creating test superuser...")
        user = User.objects.create_superuser('testadmin', 'test@test.com', 'testpass123')
        print("✅ Created test superuser")
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 30)
        
        # Create request
        request = factory.get('/manage/counters/preview/', test_case['params'])
        request.user = user
        
        try:
            response = preview_counter_value(request)
            print(f"Status: {response.status_code}")
            
            import json
            data = json.loads(response.content.decode())
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 200:
                print("✅ SUCCESS")
            else:
                print("❌ FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_counter_preview()
