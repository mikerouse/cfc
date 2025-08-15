#!/usr/bin/env python3
"""
Test script for PDF processing API endpoint
"""

import requests
import os
import sys

# Test the PDF processing API
def test_pdf_api():
    print("🧪 Testing PDF Processing API")
    
    # API endpoint
    url = "http://127.0.0.1:8000/api/council/process-pdf/"
    
    # Test data
    data = {
        'council_slug': 'birmingham-city-council',
        'year_id': '1',
        'source_type': 'upload'
    }
    
    # Use README.md as a test file (not a real PDF, but will test the upload mechanism)
    files = {}
    if os.path.exists('README.md'):
        with open('README.md', 'rb') as f:
            files = {'pdf_file': ('test.pdf', f, 'application/pdf')}
            
            print(f"📤 Making request to: {url}")
            print(f"📋 Data: {data}")
            print(f"📎 File: README.md (as test.pdf)")
            
            try:
                response = requests.post(url, data=data, files=files, timeout=30)
                
                print(f"📊 Response Status: {response.status_code}")
                print(f"📄 Response Headers: {dict(response.headers)}")
                print(f"📝 Response Content: {response.text[:1000]}...")
                
                if response.status_code == 200:
                    print("✅ API endpoint is working!")
                    return True
                else:
                    print(f"❌ API returned error {response.status_code}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                print(f"💥 Request failed: {e}")
                return False
    else:
        print("❌ README.md not found for testing")
        return False

if __name__ == "__main__":
    success = test_pdf_api()
    sys.exit(0 if success else 1)
