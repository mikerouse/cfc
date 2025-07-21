#!/usr/bin/env python3
"""
Test the financial data API using Django shell
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.http import HttpRequest
from django.contrib.auth.models import User, AnonymousUser
from council_finance.views.councils import financial_data_api

def test_api_directly():
    print("Testing financial_data_api function directly...")
    
    # Get test user
    try:
        user = User.objects.get(username='testuser')
        print(f"Found user: {user.username}")
    except User.DoesNotExist:
        print("Test user not found!")
        return
    
    # Create a mock request
    request = HttpRequest()
    request.method = 'GET'
    request.user = user
    request.GET = {'year': '2025/26'}
    
    try:
        # Call the API function directly
        response = financial_data_api(request, 'aberdeenshire-council')
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            import json
            data = json.loads(response.content.decode('utf-8'))
            print("API Response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error response: {response.content.decode('utf-8')}")
            
    except Exception as e:
        print(f"Error calling API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_api_directly()
