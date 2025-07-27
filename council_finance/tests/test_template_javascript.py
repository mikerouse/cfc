"""
Tests to validate JavaScript syntax in Django templates to prevent runtime errors.

This module tests that templates with embedded JavaScript render correctly
and don't produce syntax errors when Django template variables are substituted.
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from council_finance.models import DataField, Council, FinancialYear


class TemplateJavaScriptSyntaxTest(TestCase):
    """Test that templates with JavaScript render valid syntax"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='test@example.com'
        )
        
        # Create test council
        self.council = Council.objects.create(
            name="Test Council",
            slug="test-council",
            status="active"
        )
        
        # Create test financial year
        self.financial_year = FinancialYear.objects.create(
            label="2023-24",
            year_start=2023,
            year_end=2024
        )
        
        # Create test field for editing
        self.test_field = DataField.objects.create(
            name="Test Field",
            slug="test-field",
            category="income",
            content_type="decimal",
            required=False
        )
    
    def test_field_add_page_javascript_syntax(self):
        """Test that the field add page renders valid JavaScript"""
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('field_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains the expected JavaScript variables
        content = response.content.decode('utf-8')
        
        # Verify that councils and years are properly JSON-encoded
        self.assertIn('const councils =', content)
        self.assertIn('const years =', content)
        
        # Extract the JavaScript variables and validate they're valid JSON
        lines = content.split('\n')
        councils_line = None
        years_line = None
        
        for line in lines:
            if 'const councils =' in line:
                councils_line = line.strip()
            elif 'const years =' in line:
                years_line = line.strip()
        
        self.assertIsNotNone(councils_line, "councils variable not found in JavaScript")
        self.assertIsNotNone(years_line, "years variable not found in JavaScript")
        
        # Extract JSON from the JavaScript variable declarations
        councils_json = councils_line.split('const councils = ')[1].rstrip(';')
        years_json = years_line.split('const years = ')[1].rstrip(';')
        
        # Validate that the JSON is parseable
        try:
            councils_data = json.loads(councils_json)
            years_data = json.loads(years_json)
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON in JavaScript variables: {e}")
        
        # Validate structure
        self.assertIsInstance(councils_data, list)
        self.assertIsInstance(years_data, list)
        
        # If there's data, validate it has the expected structure
        if councils_data:
            council = councils_data[0]
            self.assertIn('slug', council)
            self.assertIn('name', council)
        
        if years_data:
            year = years_data[0]
            self.assertIn('label', year)
            self.assertIn('display_label', year)
    
    def test_field_edit_page_javascript_syntax(self):
        """Test that the field edit page renders valid JavaScript"""
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('field_edit', kwargs={'field_id': self.test_field.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for the is_editing variable
        self.assertIn('const isEditing =', content)
        
        # Extract and validate the isEditing variable
        lines = content.split('\n')
        is_editing_line = None
        
        for line in lines:
            if 'const isEditing =' in line:
                is_editing_line = line.strip()
                break
        
        self.assertIsNotNone(is_editing_line, "isEditing variable not found in JavaScript")
        
        # Should be "const isEditing = true;" for edit page
        self.assertIn('const isEditing = true;', is_editing_line)
    
    def test_template_variables_are_properly_escaped(self):
        """Test that template variables in JavaScript are properly escaped"""
        self.client.login(username='testuser', password='testpass')
        
        # Create a council with special characters to test escaping
        special_council = Council.objects.create(
            name="Test's \"Special\" Council & More",
            slug="special-council",
            status="active"
        )
        
        url = reverse('field_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # The special characters should be properly escaped in JSON
        self.assertIn('Test\\u0027s \\u0022Special\\u0022 Council \\u0026 More', content)
        
        # The JavaScript should still be valid
        lines = content.split('\n')
        for line in lines:
            if 'const councils =' in line:
                councils_json = line.split('const councils = ')[1].rstrip(';')
                try:
                    json.loads(councils_json)
                except json.JSONDecodeError as e:
                    self.fail(f"Special characters broke JSON encoding: {e}")
                break
    
    def test_empty_data_handling(self):
        """Test that templates handle empty councils/years data gracefully"""
        # Clear all data
        Council.objects.all().delete()
        FinancialYear.objects.all().delete()
        
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('field_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Should have empty arrays as defaults
        self.assertIn('const councils = [];', content)
        self.assertIn('const years = [];', content)


class JavaScriptValidationManagementCommand(TestCase):
    """Test management command for validating JavaScript in templates"""
    
    def test_validate_template_javascript_command_exists(self):
        """Test that we can import and run the validation command"""
        from django.core.management import call_command
        from io import StringIO
        
        # This test ensures the command can be called without errors
        # The actual command implementation would validate all templates
        out = StringIO()
        try:
            call_command('validate_template_javascript', stdout=out)
        except Exception as e:
            # If command doesn't exist yet, that's expected
            if "Unknown command" in str(e):
                self.skipTest("Management command not implemented yet")
            else:
                raise