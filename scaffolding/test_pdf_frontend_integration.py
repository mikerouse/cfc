#!/usr/bin/env python3
"""
PDF Frontend Integration Test

Tests the complete PDF.js integration from upload to viewer display.
Creates a test PDF, uploads it via API, and verifies the response includes 
PDF document info for the viewer.
"""

import os
import sys
import requests
import tempfile
import json

# Test PDF content (minimal valid PDF)
PDF_CONTENT = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Financial Statement) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000198 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
292
%%EOF
"""

def test_pdf_upload_integration():
    """Test PDF upload with PDF.js integration"""
    print("🧪 Testing PDF Upload → PDF.js Integration")
    
    # Create temporary PDF file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(PDF_CONTENT)
        temp_file_path = temp_file.name
    
    try:
        # Test data
        base_url = 'http://127.0.0.1:8000'
        
        print(f"📡 Testing against: {base_url}")
        print(f"📄 Created test PDF: {temp_file_path} ({len(PDF_CONTENT)} bytes)")
        
        # First, get CSRF token from the login page
        session = requests.Session()
        login_response = session.get(f"{base_url}/accounts/login/")
        
        if login_response.status_code != 200:
            print(f"❌ Failed to get login page: {login_response.status_code}")
            return False
        
        # Extract CSRF token from response
        csrf_token = None
        for line in login_response.text.split('\n'):
            if 'csrfmiddlewaretoken' in line and 'value=' in line:
                start = line.find('value="') + 8
                end = line.find('"', start)
                csrf_token = line[start:end]
                break
        
        if not csrf_token:
            print("❌ Could not extract CSRF token from login page")
            return False
        
        print(f"🔐 Got CSRF token: {csrf_token[:10]}...")
        
        # Login with admin credentials (from .env)
        import django
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
        django.setup()
        
        from django.conf import settings
        
        admin_user = getattr(settings, 'ADMIN_USER', None)
        admin_password = getattr(settings, 'ADMIN_PASSWORD', None)
        
        if not admin_user or not admin_password:
            print("❌ ADMIN_USER and ADMIN_PASSWORD not configured in .env")
            return False
        
        login_data = {
            'username': admin_user,
            'password': admin_password,
            'csrfmiddlewaretoken': csrf_token
        }
        
        login_response = session.post(f"{base_url}/accounts/login/", data=login_data)
        
        if login_response.status_code not in [200, 302]:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        print(f"✅ Logged in as: {admin_user}")
        
        # Get a fresh CSRF token for the PDF upload
        csrf_response = session.get(f"{base_url}/councils/leeds-city-council/edit/")
        if csrf_response.status_code != 200:
            print(f"❌ Failed to get council edit page: {csrf_response.status_code}")
            return False
        
        # Extract CSRF token from the edit page
        csrf_token = None
        for line in csrf_response.text.split('\n'):
            if 'csrfmiddlewaretoken' in line and 'value=' in line:
                start = line.find('value="') + 8
                end = line.find('"', start)
                csrf_token = line[start:end]
                break
        
        if not csrf_token:
            print("❌ Could not extract CSRF token from edit page")
            return False
        
        # Test PDF upload via API
        print("📤 Testing PDF upload API...")
        
        with open(temp_file_path, 'rb') as pdf_file:
            files = {'pdf_file': ('test_statement.pdf', pdf_file, 'application/pdf')}
            data = {
                'council_slug': 'leeds-city-council',
                'year_id': '1',  # Assume year ID 1 exists
                'source_type': 'upload',
                'csrfmiddlewaretoken': csrf_token
            }
            
            print(f"📋 Upload data: {data}")
            print(f"📄 Upload file: {files['pdf_file'][0]}")
            
            # Make the API request
            response = session.post(
                f"{base_url}/api/council/process-pdf/",
                files=files,
                data=data,
                timeout=120
            )
        
        print(f"📡 API Response: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code}")
            print(f"📄 Response content: {response.text[:500]}")
            return False
        
        # Parse JSON response
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"📄 Response content: {response.text[:500]}")
            return False
        
        print("✅ API request successful!")
        print(f"📊 Response keys: {list(result.keys())}")
        
        # Check for PDF.js integration fields
        success_checks = {
            "success": result.get('success', False),
            "extracted_data": bool(result.get('extracted_data')),
            "confidence_scores": bool(result.get('confidence_scores')),
            "processing_stats": bool(result.get('processing_stats')),
            "pdf_document": bool(result.get('pdf_document'))  # New field for PDF.js
        }
        
        print("\n📋 Integration Test Results:")
        for check_name, passed in success_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}: {passed}")
        
        # Detailed PDF document info check
        if result.get('pdf_document'):
            pdf_doc = result['pdf_document']
            pdf_checks = {
                "id": bool(pdf_doc.get('id')),
                "access_token": bool(pdf_doc.get('access_token')),
                "filename": bool(pdf_doc.get('filename')),
                "secure_url": bool(pdf_doc.get('secure_url')),
                "file_size": bool(pdf_doc.get('file_size'))
            }
            
            print(f"\n📄 PDF Document Info:")
            for field, value in pdf_doc.items():
                if field == 'access_token':
                    print(f"  {field}: {str(value)[:20]}... ({len(str(value))} chars)")
                else:
                    print(f"  {field}: {value}")
            
            print(f"\n📋 PDF Document Checks:")
            for check_name, passed in pdf_checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check_name}: {passed}")
            
            # Test secure URL access
            if pdf_doc.get('secure_url'):
                print(f"\n🔗 Testing PDF access at: {pdf_doc['secure_url']}")
                pdf_response = session.get(f"{base_url}{pdf_doc['secure_url']}")
                print(f"📡 PDF access response: {pdf_response.status_code}")
                
                if pdf_response.status_code == 200:
                    print(f"✅ PDF successfully served ({len(pdf_response.content)} bytes)")
                    print(f"📄 Content-Type: {pdf_response.headers.get('content-type')}")
                else:
                    print(f"❌ PDF access failed: {pdf_response.status_code}")
                    return False
        
        # Overall test result
        all_passed = all(success_checks.values())
        
        if all_passed:
            print(f"\n🎉 PDF.js Integration Test PASSED!")
            print("✅ Backend creates PDFDocument records")
            print("✅ Frontend will receive PDF viewer data")
            print("✅ Secure PDF serving works")
            return True
        else:
            print(f"\n❌ PDF.js Integration Test FAILED!")
            failed_checks = [name for name, passed in success_checks.items() if not passed]
            print(f"Failed checks: {', '.join(failed_checks)}")
            return False
    
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

def main():
    """Run the integration test"""
    print("PDF.js Frontend Integration Test")
    print("=" * 50)
    
    try:
        success = test_pdf_upload_integration()
        
        if success:
            print(f"\n🚀 Integration is working! Try uploading a PDF at:")
            print(f"   http://127.0.0.1:8000/councils/leeds-city-council/edit/")
            print(f"   → Choose PDF Upload")
            print(f"   → Upload your PDF")
            print(f"   → You should now see the PDF viewer!")
        else:
            print(f"\n🔧 Integration has issues. Check the output above.")
        
        return success
    
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)