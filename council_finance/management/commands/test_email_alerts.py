"""
Management command to test the email alert system

This command allows testing different types of email alerts to ensure
the system is working correctly.
"""

from django.core.management.base import BaseCommand, CommandError
from django.http import HttpRequest
from council_finance.utils.email_alerts import (
    send_error_alert, 
    send_template_missing_alert, 
    send_syntax_error_alert,
    email_alert_service
)


class Command(BaseCommand):
    help = 'Test the email alert system with different error types'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['template', 'syntax', 'generic', 'import', 'all'],
            default='generic',
            help='Type of alert to test (default: generic)'
        )
        
        parser.add_argument(
            '--config-check',
            action='store_true',
            help='Check email alert configuration without sending emails'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Email Alert System'))
        self.stdout.write('=' * 50)
        
        # Configuration check
        if options['config_check']:
            self.check_configuration()
            return
        
        # Test specific alert types
        alert_type = options['type']
        
        if alert_type == 'all':
            self.test_all_alerts()
        elif alert_type == 'template':
            self.test_template_alert()
        elif alert_type == 'syntax':
            self.test_syntax_alert()
        elif alert_type == 'generic':
            self.test_generic_alert()
        elif alert_type == 'import':
            self.test_import_alert()
        
        self.stdout.write(self.style.SUCCESS('\nEmail alert test completed!'))
    
    def check_configuration(self):
        """Check if email alerting is properly configured"""
        service = email_alert_service
        
        self.stdout.write('\nEmail Alert Configuration:')
        self.stdout.write('-' * 30)
        
        # Check API key
        if service.api_key:
            self.stdout.write(self.style.SUCCESS('[OK] BREVO_API_KEY configured'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] BREVO_API_KEY missing'))
        
        # Check alert email
        if service.alert_email:
            self.stdout.write(self.style.SUCCESS(f'[OK] ERROR_ALERTS_EMAIL_ADDRESS configured: {service.alert_email}'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] ERROR_ALERTS_EMAIL_ADDRESS missing'))
        
        # Check Brevo library
        try:
            import brevo_python
            self.stdout.write(self.style.SUCCESS('[OK] brevo-python library available'))
        except ImportError:
            self.stdout.write(self.style.ERROR('[ERROR] brevo-python library not installed'))
        
        # Check from email
        self.stdout.write(f'From email: {service.from_email}')
        self.stdout.write(f'From name: {service.from_name}')
        
        # Overall status
        if service.api_key and service.alert_email:
            self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Email alerts should work properly'))
        else:
            self.stdout.write(self.style.WARNING('\n[WARNING] Email alerts will be logged only (missing configuration)'))
    
    def test_all_alerts(self):
        """Test all types of alerts"""
        self.stdout.write('\nTesting all alert types:')
        self.stdout.write('-' * 30)
        
        self.test_template_alert()
        self.test_syntax_alert()
        self.test_generic_alert()
        self.test_import_alert()
    
    def test_template_alert(self):
        """Test template missing alert"""
        self.stdout.write('\nTesting Template Missing Alert...')
        
        # Create a mock request
        request = self.create_mock_request()
        
        try:
            result = send_template_missing_alert('test_missing_template.html', request)
            if result:
                self.stdout.write(self.style.SUCCESS('[OK] Template missing alert sent successfully'))
            else:
                self.stdout.write(self.style.WARNING('[LOG] Template missing alert logged (no email sent)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Template missing alert failed: {e}'))
    
    def test_syntax_alert(self):
        """Test syntax error alert"""
        self.stdout.write('\nTesting Syntax Error Alert...')
        
        try:
            result = send_syntax_error_alert(
                error_details="invalid syntax (test_file.py, line 42)",
                file_path="/path/to/test_file.py"
            )
            if result:
                self.stdout.write(self.style.SUCCESS('[OK] Syntax error alert sent successfully'))
            else:
                self.stdout.write(self.style.WARNING('[LOG] Syntax error alert logged (no email sent)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Syntax error alert failed: {e}'))
    
    def test_generic_alert(self):
        """Test generic error alert"""
        self.stdout.write('\nTesting Generic Error Alert...')
        
        # Create a mock request and exception
        request = self.create_mock_request()
        
        try:
            # Create a test exception
            test_exception = ValueError("This is a test error for email alert system")
            
            context = {
                'test_mode': True,
                'alert_type': 'TestAlert',
                'suggested_action': 'This is a test - no action required'
            }
            
            result = send_error_alert(test_exception, request, context)
            if result:
                self.stdout.write(self.style.SUCCESS('[OK] Generic error alert sent successfully'))
            else:
                self.stdout.write(self.style.WARNING('[LOG] Generic error alert logged (no email sent)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Generic error alert failed: {e}'))
    
    def test_import_alert(self):
        """Test import error alert"""
        self.stdout.write('\nTesting Import Error Alert...')
        
        request = self.create_mock_request()
        
        try:
            # Create a mock import error
            import_error = ImportError("No module named 'nonexistent_test_module'")
            import_error.name = 'nonexistent_test_module'
            
            context = {
                'test_mode': True,
                'alert_type': 'TestImportError',
                'suggested_action': 'This is a test - no action required'
            }
            
            result = send_error_alert(import_error, request, context)
            if result:
                self.stdout.write(self.style.SUCCESS('[OK] Import error alert sent successfully'))
            else:
                self.stdout.write(self.style.WARNING('[LOG] Import error alert logged (no email sent)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Import error alert failed: {e}'))
    
    def create_mock_request(self):
        """Create a mock Django request for testing"""
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/test-email-alerts/'
        request.META = {
            'HTTP_USER_AGENT': 'Test Command Email Alert System',
            'HTTP_REFERER': 'Management Command',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        # Mock user
        class MockUser:
            def __str__(self):
                return 'TestUser (Management Command)'
        
        request.user = MockUser()
        
        # Mock resolver match
        class MockResolverMatch:
            view_name = 'test_email_alerts'
            url_name = 'test_command'
        
        request.resolver_match = MockResolverMatch()
        
        return request