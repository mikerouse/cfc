#!/usr/bin/env python3
"""
Test script to verify JavaScript error fixes on the council edit page.

This script tests:
1. API endpoint responses (should return JSON, not 500 errors)
2. Favicon availability (should not return 404)
3. Council edit page loads without JavaScript errors
4. Recent activity data loads correctly
"""

import os
import sys
import requests
import json
from urllib.parse import urljoin

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
import django
django.setup()

from council_finance.models import Council

BASE_URL = 'http://127.0.0.1:8000'

def test_api_endpoints():
    """Test that API endpoints return proper JSON responses."""
    print("Testing API endpoints...")
    
    # Test recent activity API
    url = urljoin(BASE_URL, '/api/council/worcestershire-county-council/recent-activity/')
    try:
        response = requests.get(url, timeout=10)
        print(f"✓ Recent activity API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Recent activity returns valid JSON with {len(data.get('activities', []))} activities")
        else:
            print(f"✗ Recent activity API returned {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"✗ Recent activity API failed: {e}")
        return False
    
    # Test council search API
    url = urljoin(BASE_URL, '/api/councils/search/?q=worcestershire')
    try:
        response = requests.get(url, timeout=10)
        print(f"✓ Search API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Search API returns valid JSON with {len(data)} results")
        else:
            print(f"✗ Search API returned {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"✗ Search API failed: {e}")
        return False
    
    return True

def test_favicon():
    """Test that favicon is available."""
    print("\nTesting favicon...")
    
    url = urljoin(BASE_URL, '/favicon.ico')
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✓ Favicon loads successfully")
            return True
        else:
            print(f"✗ Favicon returned {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Favicon test failed: {e}")
        return False

def test_council_edit_page():
    """Test that the council edit page loads without errors."""
    print("\nTesting council edit page...")
    
    url = urljoin(BASE_URL, '/councils/worcestershire-county-council/?tab=edit')
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✓ Council edit page loads successfully")
            
            # Check for JavaScript elements that should be present
            content = response.text
            if 'recent-activity-list' in content:
                print("✓ Recent activity element found in HTML")
            else:
                print("⚠ Recent activity element not found in HTML")
            
            if 'enhanced_council_edit.html' in content or 'council_edit.js' in content:
                print("✓ Council edit JavaScript components loaded")
            else:
                print("⚠ Council edit JavaScript components not detected")
            
            return True
        else:
            print(f"✗ Council edit page returned {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Council edit page test failed: {e}")
        return False

def test_database_connectivity():
    """Test that database queries work correctly."""
    print("\nTesting database connectivity...")
    
    try:
        # Test council retrieval
        council = Council.objects.get(slug='worcestershire-county-council')
        print(f"✓ Council found: {council.name}")
        
        # Test recent activity query (this was causing the 500 error)
        from council_finance.models import ActivityLog
        activities = ActivityLog.objects.filter(related_council=council).order_by('-created')[:5]
        print(f"✓ Recent activities query works: {len(activities)} activities found")
        
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def main():
    """Run all tests and report results."""
    print("🧪 Testing JavaScript Error Fixes")
    print("=" * 40)
    
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("API Endpoints", test_api_endpoints),
        ("Favicon", test_favicon),
        ("Council Edit Page", test_council_edit_page),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("📊 Test Results Summary")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! JavaScript errors should be resolved.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the server logs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
