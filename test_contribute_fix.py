#!/usr/bin/env python3
"""
Test script to verify the contribute page fixes work correctly.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_contribute_page():
    """Test that the contribute page loads without errors."""
    print("Testing contribute page...")
    
    response = requests.get(f"{BASE_URL}/contribute/")
    print(f"Contribute page status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Contribute page loads successfully")
        if "Missing Characteristics" in response.text:
            print("✅ Page contains expected content")
        else:
            print("❌ Page missing expected content")
    else:
        print(f"❌ Contribute page failed to load: {response.status_code}")

def test_contribute_stats():
    """Test the contribute stats API endpoint."""
    print("\nTesting contribute stats API...")
    
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    response = requests.get(f"{BASE_URL}/contribute/stats/", headers=headers)
    
    print(f"Stats API status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("✅ Stats API returns valid JSON:")
            print(f"  Missing total: {data.get('missing', 'N/A')}")
            print(f"  Missing characteristics: {data.get('missing_characteristics', 'N/A')}")
            print(f"  Missing financial: {data.get('missing_financial', 'N/A')}")
            print(f"  Pending: {data.get('pending', 'N/A')}")
            print(f"  Suspicious: {data.get('suspicious', 'N/A')}")
            
            if data.get('missing_characteristics', 0) > 0:
                print("✅ Found missing characteristics data")
            else:
                print("⚠️  No missing characteristics found - this might be expected")
                
        except json.JSONDecodeError:
            print("❌ Stats API returned invalid JSON")
    else:
        print(f"❌ Stats API failed: {response.status_code}")

def test_data_issues_table():
    """Test the data issues table API endpoint."""
    print("\nTesting data issues table API...")
    
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    
    # Test missing characteristics
    params = {
        'type': 'missing',
        'category': 'characteristic',
        'page': 1,
        'page_size': 10
    }
    
    response = requests.get(f"{BASE_URL}/contribute/issues/", headers=headers, params=params)
    print(f"Data issues API status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("✅ Data issues API returns valid JSON:")
            print(f"  HTML length: {len(data.get('html', ''))}")
            print(f"  Total issues: {data.get('total', 'N/A')}")
            print(f"  Current page: {data.get('page', 'N/A')}")
            print(f"  Total pages: {data.get('num_pages', 'N/A')}")
            
            if data.get('total', 0) > 0:
                print("✅ Found data issues to display")
                if 'council' in data.get('html', '').lower():
                    print("✅ HTML contains expected table content")
                else:
                    print("⚠️  HTML might be missing expected content")
            else:
                print("⚠️  No data issues found")
                
        except json.JSONDecodeError:
            print("❌ Data issues API returned invalid JSON")
    else:
        print(f"❌ Data issues API failed: {response.status_code}")

def test_god_mode_activity():
    """Test God Mode activity log enhancement."""
    print("\nTesting God Mode activity log...")
    
    # Note: This requires superuser access, so it may fail
    response = requests.get(f"{BASE_URL}/god-mode/")
    print(f"God Mode page status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ God Mode page accessible")
        if "Activity Log" in response.text:
            print("✅ Page contains activity log section")
        else:
            print("⚠️  Activity log section may be missing")
    elif response.status_code == 403 or response.status_code == 404:
        print("⚠️  God Mode requires authentication (expected)")
    else:
        print(f"❌ God Mode failed: {response.status_code}")

def main():
    print("🔧 Testing Council Finance Counters contribute page fixes...")
    print("=" * 60)
    
    try:
        test_contribute_page()
        test_contribute_stats()
        test_data_issues_table()
        test_god_mode_activity()
        
        print("\n" + "=" * 60)
        print("✅ Testing complete! Check the results above for any issues.")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to development server.")
        print("Make sure Django development server is running on http://127.0.0.1:8000/")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
