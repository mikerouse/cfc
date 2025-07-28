#!/usr/bin/env python3
"""
Test with debug enabled
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

def test_with_debug():
    """Test with debug enabled"""
    
    print("🧪 Testing Counter Preview with Debug")
    print("=" * 50)
    
    # Create mock request
    factory = RequestFactory()
    
    # Test Worcestershire with debug
    request = factory.get('/manage/counters/preview/', {
        'council': 'worcestershire',
        'year': '2024/25',
        'formula': 'non-ring-fenced-government-grant-income-per-capita',
        'precision': '0',
        'show_currency': 'true',
        'friendly_format': 'false',
        'debug': 'true'  # Enable debug
    })
    
    # Get a superuser for authentication
    user = User.objects.filter(is_superuser=True).first()
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

if __name__ == '__main__':
    test_with_debug()
