#!/usr/bin/env python3
"""
Test the actual AI factoid API endpoint to see if caching works.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from council_finance.api.ai_factoid_api import ai_council_factoids

def test_api_endpoint():
    """Test the AI factoid API endpoint."""
    council_slug = "worcestershire"
    
    print("TESTING AI FACTOID API ENDPOINT")
    print("=" * 50)
    
    # Clear cache first
    cache_key = f"ai_factoids:{council_slug}"
    cache_key_stale = f"ai_factoids_stale:{council_slug}"
    cache.delete(cache_key)
    cache.delete(cache_key_stale)
    print("Cleared cache before test")
    
    # Create mock request
    factory = RequestFactory()
    request = factory.get(f'/api/factoids/ai/{council_slug}/')
    request.user = AnonymousUser()
    
    print(f"\nCalling API endpoint for {council_slug}...")
    response = ai_council_factoids(request, council_slug)
    
    print(f"Response status: {response.status_code}")
    
    if hasattr(response, 'data'):
        data = response.data
        print(f"Response data keys: {list(data.keys())}")
        
        if data.get('success'):
            factoids = data.get('factoids', [])
            print(f"Factoids returned: {len(factoids)}")
            print(f"AI model used: {data.get('ai_model', 'unknown')}")
            print(f"Cache status: {data.get('cache_status', 'unknown')}")
            
            # Show first factoid
            if factoids:
                print(f"First factoid: {factoids[0].get('text', 'No text')}")
        else:
            print(f"API call failed: {data.get('error', 'Unknown error')}")
    else:
        print("No response data available")
    
    # Check if cache was set
    print(f"\nChecking cache after API call...")
    cached_data = cache.get(cache_key)
    stale_cached_data = cache.get(cache_key_stale)
    
    print(f"Primary cache: {'SET' if cached_data else 'NOT SET'}")
    print(f"Stale cache: {'SET' if stale_cached_data else 'NOT SET'}")
    
    if cached_data:
        print(f"Cached factoid count: {cached_data.get('factoid_count', 'unknown')}")
        print(f"Cached at: {cached_data.get('generated_at', 'unknown')}")

if __name__ == "__main__":
    test_api_endpoint()