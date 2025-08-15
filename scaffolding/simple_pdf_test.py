#!/usr/bin/env python3
"""
Simple PDF Integration Test

Quick test to verify core PDF.js integration components work.
"""

import os
import sys
import django

# Django setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import PDFDocument, Council, FinancialYear
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

def test_pdf_model():
    """Test PDFDocument model basic functionality"""
    print("Testing PDFDocument model...")
    
    # Get or create test data
    user, _ = User.objects.get_or_create(
        username='test_pdf_user',
        defaults={'email': 'test@example.com'}
    )
    
    council, _ = Council.objects.get_or_create(
        slug='test-council-pdf',
        defaults={'name': 'Test Council for PDF'}
    )
    
    year, _ = FinancialYear.objects.get_or_create(
        label='2024/25',
        defaults={'start_date': '2024-04-01', 'end_date': '2025-03-31'}
    )
    
    # Create test PDF content
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nxref\n%%EOF'
    pdf_file = SimpleUploadedFile(
        'test.pdf',
        pdf_content,
        content_type='application/pdf'
    )
    
    # Create PDFDocument
    pdf_doc = PDFDocument(
        original_filename='test_statement.pdf',
        file=pdf_file,
        council=council,
        financial_year=year,
        uploaded_by=user
    )
    pdf_doc.save()
    
    print(f"  - Created PDFDocument: {pdf_doc.id}")
    print(f"  - Original filename: {pdf_doc.original_filename}")
    print(f"  - Council: {pdf_doc.council.name}")
    print(f"  - Year: {pdf_doc.financial_year.label}")
    print(f"  - Access token generated: {len(pdf_doc.access_token) > 0}")
    print(f"  - Access token valid: {pdf_doc.is_access_token_valid()}")
    
    # Test access permissions
    print(f"  - Owner can access: {pdf_doc.can_be_accessed_by(user)}")
    print(f"  - Anonymous cannot access: {not pdf_doc.can_be_accessed_by(None)}")
    
    # Test secure URL
    secure_url = pdf_doc.get_secure_url()
    print(f"  - Secure URL: {secure_url}")
    
    # Test processing workflow
    pdf_doc.start_processing()
    print(f"  - Processing started: {pdf_doc.processing_status}")
    
    pdf_doc.complete_processing({'test': 123}, {'test': 0.9})
    print(f"  - Processing completed: {pdf_doc.processing_status}")
    
    # Clean up
    pdf_doc.delete()
    print("  - Test document cleaned up")
    
    return True

def test_pdf_serving_url():
    """Test PDF serving URL pattern"""
    print("Testing PDF serving URL...")
    
    from django.urls import reverse
    import uuid
    
    test_id = uuid.uuid4()
    test_token = 'test-access-token-123'
    
    try:
        url = reverse('pdf_serve', kwargs={
            'document_id': test_id,
            'access_token': test_token
        })
        print(f"  - URL pattern works: {url}")
        return True
    except Exception as e:
        print(f"  - URL pattern error: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting Simple PDF Integration Tests")
    print("=" * 50)
    
    tests = [
        ("PDFDocument Model", test_pdf_model),
        ("PDF Serving URL", test_pdf_serving_url),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{test_name}:")
            success = test_func()
            if success:
                print(f"  PASSED")
                passed += 1
            else:
                print(f"  FAILED")
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print(f"\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("All core PDF integration components are working!")
        return True
    else:
        print("Some tests failed. Check the output above.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)