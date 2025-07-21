#!/usr/bin/env python3
"""
Test the financial data API directly
"""

import os
import sys
import django
import json

# Setup Django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_financial_data_api():
    # Create a test client
    client = Client()
    
    # Get test user
    try:
        user = User.objects.get(username='testuser')
        print(f"Found user: {user.username}")
    except User.DoesNotExist:
        print("Test user not found. Run create_test_user.py first.")
        return
    
    # Login
    login_success = client.login(username='testuser', password='testpass123')
    if not login_success:
        print("Login failed!")
        return
    
    print("Login successful!")
    
    # Test the financial data API
    url = '/councils/aberdeenshire-council/financial-data/?year=2025%2F26'
    print(f"Testing URL: {url}")
    
    response = client.get(url)
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.items())}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("JSON Response:")
            print(json.dumps(data, indent=2))
        except:
            print("Response content (not JSON):")
            print(response.content.decode('utf-8')[:500])
    else:
        print("Error response:")
        print(response.content.decode('utf-8')[:500])

if __name__ == '__main__':
    test_financial_data_api()
