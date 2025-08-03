#!/usr/bin/env python
"""
Quick test script for home page performance and functionality
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test.client import Client

def test_home_page():
    """Test the home page load time and functionality"""
    print("Testing Council Finance Counters Home Page")
    print("=" * 50)
    
    client = Client()
    
    print("Making request to /...")
    start_time = time.time()
    
    try:
        response = client.get('/')
        end_time = time.time()
        
        load_time = end_time - start_time
        
        print(f"SUCCESS: Home page loaded")
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content):,} bytes")
        print(f"Load Time: {load_time:.2f} seconds")
        
        # Performance assessment
        if load_time < 2:
            print("EXCELLENT: Very fast load time")
        elif load_time < 5:
            print("GOOD: Acceptable load time") 
        elif load_time < 10:
            print("MODERATE: Could be improved")
        elif load_time < 20:
            print("SLOW: Needs optimization")
        else:
            print("VERY SLOW: Critical performance issue")
        
        # Check for any obvious errors in content
        content_str = response.content.decode('utf-8', errors='ignore')
        if 'Error' in content_str or 'Exception' in content_str:
            print("WARNING: Response may contain error content")
            # Find the first error/exception mention
            error_start = content_str.find('Error')
            if error_start == -1:
                error_start = content_str.find('Exception')
            if error_start != -1:
                error_snippet = content_str[error_start:error_start+200]
                print(f"Error snippet: {error_snippet}")
        
        return True
        
    except Exception as e:
        end_time = time.time()
        load_time = end_time - start_time
        
        print(f"ERROR: Home page failed to load")
        print(f"Error: {e}")
        print(f"Time before error: {load_time:.2f} seconds")
        
        # Print the full traceback for debugging
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        
        return False

if __name__ == "__main__":
    success = test_home_page()
    sys.exit(0 if success else 1)