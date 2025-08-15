#!/usr/bin/env python3
"""
PDF.js Integration Test Suite

Tests the complete PDF.js integration system including:
- PDFDocument model functionality
- Secure PDF serving endpoint
- Access token validation
- File handling and permissions

Run with: python scaffolding/test_pdf_integration.py
"""

import os
import sys
import django
import tempfile
import uuid
from datetime import timedelta

# Django setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from council_finance.models import PDFDocument, Council, FinancialYear
from council_finance.views.council_edit_api import pdf_serve


class PDFDocumentModelTests(TestCase):
    """Test PDFDocument model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.council = Council.objects.create(
            name='Test Council',
            slug='test-council'
        )
        
        self.year = FinancialYear.objects.create(
            label='2024/25',
            start_date='2024-04-01',
            end_date='2025-03-31'
        )
        
        # Create a test PDF file
        self.pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nxref\n%%EOF'
        self.pdf_file = SimpleUploadedFile(
            'test_statement.pdf',
            self.pdf_content,
            content_type='application/pdf'
        )
    
    def test_pdf_document_creation(self):
        """Test basic PDFDocument creation"""
        pdf_doc = PDFDocument.objects.create(
            original_filename='test_statement.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        self.assertEqual(pdf_doc.original_filename, 'test_statement.pdf')
        self.assertEqual(pdf_doc.council, self.council)
        self.assertEqual(pdf_doc.financial_year, self.year)
        self.assertEqual(pdf_doc.uploaded_by, self.user)
        self.assertTrue(pdf_doc.is_active)
        self.assertIsNotNone(pdf_doc.access_token)
        self.assertIsNotNone(pdf_doc.access_expires_at)
    
    def test_access_token_generation(self):
        """Test automatic access token generation"""
        pdf_doc = PDFDocument.objects.create(
            original_filename='test.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        # Should auto-generate access token
        self.assertIsNotNone(pdf_doc.access_token)
        self.assertTrue(len(pdf_doc.access_token) > 32)
        self.assertTrue(pdf_doc.is_access_token_valid())
    
    def test_access_token_expiry(self):
        """Test access token expiry functionality"""
        pdf_doc = PDFDocument.objects.create(
            original_filename='test.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        # Set token to expired
        pdf_doc.access_expires_at = timezone.now() - timedelta(hours=1)
        pdf_doc.save()
        
        self.assertFalse(pdf_doc.is_access_token_valid())
        
        # Refresh token
        pdf_doc.refresh_access_token()
        self.assertTrue(pdf_doc.is_access_token_valid())
    
    def test_user_access_permissions(self):
        """Test user access permission checking"""
        pdf_doc = PDFDocument.objects.create(
            original_filename='test.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        # Owner should have access
        self.assertTrue(pdf_doc.can_be_accessed_by(self.user))
        
        # Other user should not have access
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.assertFalse(pdf_doc.can_be_accessed_by(other_user))
        
        # Staff user should have access
        staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        self.assertTrue(pdf_doc.can_be_accessed_by(staff_user))
        
        # Anonymous user should not have access
        self.assertFalse(pdf_doc.can_be_accessed_by(None))
    
    def test_secure_url_generation(self):
        """Test secure URL generation"""
        pdf_doc = PDFDocument.objects.create(
            original_filename='test.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        secure_url = pdf_doc.get_secure_url()
        
        self.assertIn(str(pdf_doc.id), secure_url)
        self.assertIn(pdf_doc.access_token, secure_url)
        self.assertTrue(secure_url.startswith('/api/pdf/'))
    
    def test_processing_status_workflow(self):
        """Test processing status workflow methods"""
        pdf_doc = PDFDocument.objects.create(
            original_filename='test.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        self.assertEqual(pdf_doc.processing_status, PDFDocument.PROCESSING_PENDING)
        
        # Start processing
        pdf_doc.start_processing()
        self.assertEqual(pdf_doc.processing_status, PDFDocument.PROCESSING_IN_PROGRESS)
        self.assertIsNotNone(pdf_doc.processing_started_at)
        
        # Complete processing
        test_results = {'field1': 123, 'field2': 456}
        test_confidence = {'field1': 0.9, 'field2': 0.8}
        pdf_doc.complete_processing(test_results, test_confidence)
        
        self.assertEqual(pdf_doc.processing_status, PDFDocument.PROCESSING_COMPLETED)
        self.assertIsNotNone(pdf_doc.processing_completed_at)
        self.assertEqual(pdf_doc.extraction_results, test_results)
        self.assertEqual(pdf_doc.confidence_scores, test_confidence)
        
        # Test failure
        pdf_doc2 = PDFDocument.objects.create(
            original_filename='test2.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        pdf_doc2.fail_processing("Test error message")
        self.assertEqual(pdf_doc2.processing_status, PDFDocument.PROCESSING_FAILED)
        self.assertEqual(pdf_doc2.processing_error, "Test error message")


class PDFServingViewTests(TestCase):
    """Test PDF serving endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.council = Council.objects.create(
            name='Test Council',
            slug='test-council'
        )
        
        self.year = FinancialYear.objects.create(
            label='2024/25',
            start_date='2024-04-01',
            end_date='2025-03-31'
        )
        
        # Create test PDF document
        self.pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nxref\n%%EOF'
        self.pdf_file = SimpleUploadedFile(
            'test_statement.pdf',
            self.pdf_content,
            content_type='application/pdf'
        )
        
        self.pdf_doc = PDFDocument.objects.create(
            original_filename='test_statement.pdf',
            file=self.pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
    
    def test_successful_pdf_serving(self):
        """Test successful PDF serving with valid token"""
        self.client.force_login(self.user)
        
        url = reverse('pdf_serve', kwargs={
            'document_id': self.pdf_doc.id,
            'access_token': self.pdf_doc.access_token
        })
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('inline', response['Content-Disposition'])
        self.assertIn('test_statement.pdf', response['Content-Disposition'])
        
        # Check access was recorded
        self.pdf_doc.refresh_from_db()
        self.assertEqual(self.pdf_doc.access_count, 1)
        self.assertIsNotNone(self.pdf_doc.last_accessed_at)
    
    def test_invalid_document_id(self):
        """Test response for non-existent document"""
        self.client.force_login(self.user)
        
        fake_id = uuid.uuid4()
        url = reverse('pdf_serve', kwargs={
            'document_id': fake_id,
            'access_token': 'fake-token'
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_invalid_access_token(self):
        """Test response for invalid access token"""
        self.client.force_login(self.user)
        
        url = reverse('pdf_serve', kwargs={
            'document_id': self.pdf_doc.id,
            'access_token': 'invalid-token'
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_expired_access_token(self):
        """Test response for expired access token"""
        self.client.force_login(self.user)
        
        # Expire the token
        self.pdf_doc.access_expires_at = timezone.now() - timedelta(hours=1)
        self.pdf_doc.save()
        
        url = reverse('pdf_serve', kwargs={
            'document_id': self.pdf_doc.id,
            'access_token': self.pdf_doc.access_token
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 410)  # Gone
    
    def test_unauthorized_user_access(self):
        """Test access denial for unauthorized users"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        self.client.force_login(other_user)
        
        url = reverse('pdf_serve', kwargs={
            'document_id': self.pdf_doc.id,
            'access_token': self.pdf_doc.access_token
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_inactive_document(self):
        """Test access to inactive document"""
        self.client.force_login(self.user)
        
        # Deactivate document
        self.pdf_doc.is_active = False
        self.pdf_doc.save()
        
        url = reverse('pdf_serve', kwargs={
            'document_id': self.pdf_doc.id,
            'access_token': self.pdf_doc.access_token
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class PDFIntegrationFullWorkflowTest(TestCase):
    """Test complete PDF integration workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.council = Council.objects.create(
            name='Test Council',
            slug='test-council'
        )
        
        self.year = FinancialYear.objects.create(
            label='2024/25',
            start_date='2024-04-01',
            end_date='2025-03-31'
        )
    
    def test_full_pdf_workflow(self):
        """Test the complete workflow from document creation to serving"""
        # 1. Create PDF document
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nxref\n%%EOF'
        pdf_file = SimpleUploadedFile(
            'financial_statement.pdf',
            pdf_content,
            content_type='application/pdf'
        )
        
        pdf_doc = PDFDocument.objects.create(
            original_filename='financial_statement.pdf',
            file=pdf_file,
            council=self.council,
            financial_year=self.year,
            uploaded_by=self.user
        )
        
        # 2. Verify document was created with proper defaults
        self.assertEqual(pdf_doc.processing_status, PDFDocument.PROCESSING_PENDING)
        self.assertTrue(pdf_doc.is_active)
        self.assertIsNotNone(pdf_doc.access_token)
        self.assertTrue(pdf_doc.is_access_token_valid())
        
        # 3. Simulate processing workflow
        pdf_doc.start_processing()
        self.assertEqual(pdf_doc.processing_status, PDFDocument.PROCESSING_IN_PROGRESS)
        
        # Simulate successful extraction
        extraction_results = {
            'total-income': {'value': 1500000000, 'confidence': 0.95},
            'total-expenditure': {'value': 1400000000, 'confidence': 0.87}
        }
        confidence_scores = {
            'total-income': 0.95,
            'total-expenditure': 0.87
        }
        
        pdf_doc.complete_processing(extraction_results, confidence_scores)
        self.assertEqual(pdf_doc.processing_status, PDFDocument.PROCESSING_COMPLETED)
        
        # 4. Test secure URL generation
        secure_url = pdf_doc.get_secure_url()
        self.assertTrue(secure_url.startswith('/api/pdf/'))
        self.assertIn(str(pdf_doc.id), secure_url)
        
        # 5. Test PDF serving
        self.client.force_login(self.user)
        response = self.client.get(secure_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.content, pdf_content)
        
        # 6. Verify access tracking
        pdf_doc.refresh_from_db()
        self.assertEqual(pdf_doc.access_count, 1)
        self.assertIsNotNone(pdf_doc.last_accessed_at)


def run_tests():
    """Run all PDF integration tests"""
    import unittest
    from io import StringIO
    
    # Create test suite
    test_classes = [
        PDFDocumentModelTests,
        PDFServingViewTests,
        PDFIntegrationFullWorkflowTest
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)
    
    # Print results
    print("=" * 70)
    print("PDF.js Integration Test Results")
    print("=" * 70)
    
    if result.wasSuccessful():
        print(f"✅ All tests passed! ({result.testsRun} tests)")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        
        for failure in result.failures:
            print(f"\nFAILURE: {failure[0]}")
            print(failure[1])
            
        for error in result.errors:
            print(f"\nERROR: {error[0]}")
            print(error[1])
    
    print("\nTest Summary:")
    print(f"- Tests run: {result.testsRun}")
    print(f"- Failures: {len(result.failures)}")
    print(f"- Errors: {len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Starting PDF.js Integration Tests...")
    print("Testing: PDFDocument model, PDF serving, access control")
    print()
    
    success = run_tests()
    
    if success:
        print("\n🎉 PDF.js integration is ready!")
        print("Next steps:")
        print("1. Test frontend PDF viewer component")
        print("2. Implement Phase 2: Extraction highlighting")
        print("3. Integrate with council edit interface")
    else:
        print("\n🔧 Please fix the failing tests before proceeding.")
    
    exit(0 if success else 1)