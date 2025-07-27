"""
Management command to validate JavaScript syntax in Django templates.

This command renders templates with test data and validates that the resulting
JavaScript is syntactically correct, helping prevent runtime errors.
"""

import os
import re
import json
import tempfile
import subprocess
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template
from django.template import Context
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from council_finance.models import DataField, Council, FinancialYear


class Command(BaseCommand):
    help = 'Validate JavaScript syntax in Django templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            type=str,
            help='Specific template to validate (e.g., "council_finance/admin/field_form.html")'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each template'
        )
        parser.add_argument(
            '--fix-errors',
            action='store_true',
            help='Attempt to automatically fix common JavaScript errors'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        # Templates with embedded JavaScript to validate
        templates_to_check = [
            'council_finance/admin/field_form.html',
            'council_finance/enhanced_council_edit.html',
            'council_finance/council_edit_modal.html',
            'council_finance/contribute.html',
            'council_finance/spreadsheet_edit_interface.html',
        ]
        
        # If specific template specified, check only that one
        if options.get('template'):
            templates_to_check = [options['template']]
        
        total_errors = 0
        
        for template_name in templates_to_check:
            if self.verbose:
                self.stdout.write(f"\nValidating template: {template_name}")
            
            try:
                errors = self.validate_template(template_name)
                if errors:
                    total_errors += len(errors)
                    self.stdout.write(
                        self.style.ERROR(f"FAIL {template_name}: {len(errors)} error(s)")
                    )
                    for error in errors:
                        self.stdout.write(f"  - {error}")
                else:
                    if self.verbose:
                        self.stdout.write(
                            self.style.SUCCESS(f"PASS {template_name}: JavaScript syntax valid")
                        )
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f"ERROR {template_name}: Validation failed - {e}")
                )
        
        # Summary
        if total_errors > 0:
            self.stdout.write(
                self.style.ERROR(f"\nValidation completed with {total_errors} error(s)")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nAll templates passed JavaScript validation PASS")
            )
        
        return total_errors
    
    def validate_template(self, template_name):
        """Validate JavaScript in a specific template"""
        errors = []
        
        try:
            template = get_template(template_name)
        except Exception as e:
            return [f"Could not load template: {e}"]
        
        # Create test context data
        context_data = self.create_test_context()
        
        try:
            # Render the template
            rendered_content = template.render(context_data)
            
            # Extract and validate JavaScript
            js_errors = self.validate_javascript_in_content(rendered_content)
            errors.extend(js_errors)
            
        except Exception as e:
            errors.append(f"Template rendering failed: {e}")
        
        return errors
    
    def create_test_context(self):
        """Create test context data for template rendering"""
        # Create mock request
        factory = RequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        
        # Create test data
        test_council = {
            'name': 'Test Council',
            'slug': 'test-council'
        }
        
        test_year = {
            'label': '2023-24',
            'display_label': '2023-24'
        }
        
        test_field = {
            'id': 1,
            'name': 'Test Field',
            'slug': 'test-field'
        }
        
        return {
            'request': request,
            'user': request.user,
            'councils_json': json.dumps([test_council]),
            'years_json': json.dumps([test_year]),
            'councils': [test_council],  # Legacy format
            'years': [test_year],  # Legacy format
            'field': test_field,
            'is_editing': True,
            'cache_version': '1.0.0',
            'debug_mode': True,
            'form': None,  # Mock form object
            'page_title': 'Test Page',
        }
    
    def validate_javascript_in_content(self, content):
        """Extract and validate JavaScript from rendered content"""
        errors = []
        
        # Extract JavaScript blocks
        js_blocks = self.extract_javascript_blocks(content)
        
        for i, js_code in enumerate(js_blocks):
            js_errors = self.validate_javascript_syntax(js_code, f"block_{i+1}")
            errors.extend(js_errors)
        
        # Check for common template variable issues in JavaScript
        template_errors = self.check_template_variable_issues(content)
        errors.extend(template_errors)
        
        return errors
    
    def extract_javascript_blocks(self, content):
        """Extract JavaScript code blocks from HTML content"""
        js_blocks = []
        
        # Find <script> tags with JavaScript
        script_pattern = r'<script[^>]*>(.*?)</script>'
        matches = re.findall(script_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            # Skip empty scripts or ones that are just loading external files
            if match.strip() and not match.strip().startswith('//'):
                js_blocks.append(match)
        
        return js_blocks
    
    def validate_javascript_syntax(self, js_code, block_name):
        """Validate JavaScript syntax using Node.js if available"""
        errors = []
        
        try:
            # Try to validate with Node.js if available
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(js_code)
                temp_file = f.name
            
            # Use Node.js to check syntax
            try:
                result = subprocess.run(
                    ['node', '-c', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0:
                    errors.append(f"JavaScript syntax error in {block_name}: {result.stderr}")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Node.js not available, do basic validation
                basic_errors = self.basic_javascript_validation(js_code, block_name)
                errors.extend(basic_errors)
            
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
                    
        except Exception as e:
            errors.append(f"Could not validate JavaScript in {block_name}: {e}")
        
        return errors
    
    def basic_javascript_validation(self, js_code, block_name):
        """Basic JavaScript validation without external tools"""
        errors = []
        
        # Check for unclosed strings
        if js_code.count('"') % 2 != 0 or js_code.count("'") % 2 != 0:
            errors.append(f"Unclosed string in {block_name}")
        
        # Check for balanced braces, brackets, and parentheses
        braces = js_code.count('{') - js_code.count('}')
        brackets = js_code.count('[') - js_code.count(']')
        parens = js_code.count('(') - js_code.count(')')
        
        if braces != 0:
            errors.append(f"Unbalanced braces in {block_name} (difference: {braces})")
        if brackets != 0:
            errors.append(f"Unbalanced brackets in {block_name} (difference: {brackets})")
        if parens != 0:
            errors.append(f"Unbalanced parentheses in {block_name} (difference: {parens})")
        
        # Check for obvious template variable issues
        if '{{ ' in js_code and ' }}' in js_code:
            errors.append(f"Unescaped Django template variables in {block_name}")
        
        return errors
    
    def check_template_variable_issues(self, content):
        """Check for common Django template variable issues in JavaScript"""
        errors = []
        
        # Look for problematic patterns
        patterns = [
            (r'{{ *\w+\|yesno:"[^"]*"[^}]*}}', 'yesno filter without proper JavaScript handling'),
            (r'{{ *\w+\.\w+ *}}(?![^<]*</script>)', 'Unescaped object property in JavaScript'),
            (r'const \w+ = {{ *\w+ *}};', 'Direct template variable assignment without escaping'),
        ]
        
        for pattern, description in patterns:
            matches = re.findall(pattern, content)
            if matches:
                errors.append(f"Potential issue: {description} (found {len(matches)} occurrence(s))")
        
        return errors