#!/usr/bin/env python3
"""
Direct test of council detail view with edit tab
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import RequestFactory
from council_finance.views import council_detail

def test_council_view():
    factory = RequestFactory()
    request = factory.get('/councils/aberdeen-city-council/?tab=edit')
    
    try:
        response = council_detail(request, 'aberdeen-city-council')
        print(f"✅ View executed successfully - Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ View error: {e}")
        return False

if __name__ == '__main__':
    print("Testing council detail view with edit tab...")
    test_council_view()
