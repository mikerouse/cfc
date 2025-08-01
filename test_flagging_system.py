#!/usr/bin/env python3
"""
Test script for the enhanced flagging system
Tests both the contribute system removal and new flagging functionality
"""

import os
import sys
import json
import requests
from urllib.parse import urljoin

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass123"

def test_contribute_system_removed():
    """Test that the contribute system has been properly disabled"""
    print("Testing contribute system removal...")
    
    # Test contribute URL redirects
    response = requests.get(urljoin(BASE_URL, "/contribute/"))
    
    if response.status_code == 200:
        if "Data Contribution Has Changed" in response.text:
            print("✅ Contribute URL properly redirects to info page")
            return True
        else:
            print("❌ Contribute URL accessible but doesn't show redirect page")
            return False
    else:
        print(f"❌ Contribute URL returns status {response.status_code}")
        return False

def test_flagging_system_javascript():
    """Test that flagging system JavaScript is loaded on council pages"""
    print("Testing flagging system JavaScript loading...")
    
    # Test a sample council page
    response = requests.get(urljoin(BASE_URL, "/councils/"))
    
    if response.status_code == 200:
        council_links = []
        # Extract first council link (simple regex)
        import re
        matches = re.findall(r'/councils/([^/]+)/', response.text)
        if matches:
            council_slug = matches[0]
            council_url = urljoin(BASE_URL, f"/councils/{council_slug}/")
            
            council_response = requests.get(council_url)
            if council_response.status_code == 200:
                if "flagging-system.js" in council_response.text:
                    print("✅ Flagging system JavaScript properly loaded")
                    return True
                else:
                    print("❌ Flagging system JavaScript not found in council page")
                    return False
            else:
                print(f"❌ Council page returns status {council_response.status_code}")
                return False
    
    print("❌ Could not find council pages to test")
    return False

def test_flag_modal_presence():
    """Test that flag modal HTML is present"""
    print("Testing flag modal presence...")
    
    # Get any page that should have the flagging system
    response = requests.get(urljoin(BASE_URL, "/councils/"))
    if response.status_code == 200:
        council_links = []
        # Extract first council link
        import re
        matches = re.findall(r'/councils/([^/]+)/', response.text)
        if matches:
            council_slug = matches[0]
            council_url = urljoin(BASE_URL, f"/councils/{council_slug}/")
            
            council_response = requests.get(council_url)
            if council_response.status_code == 200:
                # Check for flag button elements
                if "flag-content-btn" in council_response.text:
                    print("✅ Flag buttons found in page")
                    return True
                else:
                    print("❌ Flag buttons not found in page")
                    return False
    
    print("❌ Could not test flag modal presence")
    return False

def test_admin_navigation():
    """Test that admin navigation properly links to flagged content"""
    print("Testing admin navigation...")
    
    # This would require authentication, so we'll just check the URL pattern exists
    response = requests.get(urljoin(BASE_URL, "/moderation/flagged-content/"))
    
    # We expect either a 200 (if accessible) or redirect to login
    if response.status_code in [200, 302, 403]:
        print("✅ Flagged content admin URL exists")
        return True
    else:
        print(f"❌ Flagged content admin URL returns status {response.status_code}")
        return False

def run_tests():
    """Run all tests"""
    print("=" * 50)
    print("Testing CFC Enhanced Flagging System")
    print("=" * 50)
    
    tests = [
        test_contribute_system_removed,
        test_flagging_system_javascript,
        test_flag_modal_presence,
        test_admin_navigation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! The flagging system is properly implemented.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)