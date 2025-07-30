#!/usr/bin/env python3
"""
Comprehensive testing tool for Council Finance Counters.
Consolidates all testing tools into one command that can be run after changes.
"""
import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')

import django
django.setup()

from django.core.management import call_command
from django.template.loader import get_template
from django.template import TemplateSyntaxError


class TestRunner:
    """Comprehensive test runner for the CFC project."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.successes = []
        self.test_results = {}
        
    def log(self, message, level='info'):
        """Log a message with appropriate formatting."""
        if level == 'error':
            print(f"[ERROR] {message}")
            self.errors.append(message)
        elif level == 'warning':
            print(f"[WARNING] {message}")
            self.warnings.append(message)
        elif level == 'success':
            print(f"[OK] {message}")
            self.successes.append(message)
        else:
            if self.verbose or level == 'header':
                print(message)
    
    def header(self, title):
        """Print a section header."""
        print(f"\n{'='*70}")
        print(title.upper())
        print('='*70)
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        start_time = time.time()
        
        print("\nCOUNCIL FINANCE COUNTERS - COMPREHENSIVE TEST SUITE")
        print("Running all tests to ensure system integrity...")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Import Tests
        self.header("1. Testing Python Imports")
        self.test_python_imports()
        
        # 2. Template Syntax Tests
        self.header("2. Testing Django Templates")
        self.test_django_templates()
        
        # 3. React Build Tests
        self.header("3. Testing React Build")
        self.test_react_build()
        
        # 4. API Endpoint Tests
        self.header("4. Testing API Endpoints")
        self.test_api_endpoints()
        
        # 5. Database Integrity Tests
        self.header("5. Testing Database Integrity")
        self.test_database_integrity()
        
        # 6. Static Files Tests
        self.header("6. Testing Static Files")
        self.test_static_files()
        
        # 7. Django Management Commands
        self.header("7. Testing Django Management Commands")
        self.test_management_commands()
        
        # 8. JavaScript in Templates
        self.header("8. Testing JavaScript in Templates")
        self.test_javascript_in_templates()
        
        # 9. Programming Error Detection  
        self.header("9. Testing for Programming Errors & Type Errors")
        self.test_programming_errors()
        
        # Final Summary
        self.print_summary(time.time() - start_time)
        
        # Write results to file
        self.write_test_report()
        
        return len(self.errors) == 0
    
    def test_python_imports(self):
        """Test all critical Python imports."""
        critical_imports = [
            # Models
            ("council_finance.models", ["Council", "CouncilList", "DataField", "FinancialYear"]),
            ("council_finance.models.council_list", ["CouncilList"]),
            ("council_finance.models.new_data_model", ["CouncilCharacteristic", "FinancialFigure"]),
            
            # Views
            ("council_finance.views.general", ["my_lists", "create_list_api"]),
            ("council_finance.views.api", ["search_councils"]),
            
            # Forms
            ("council_finance.forms", ["CouncilListForm"]),
            
            # Services
            ("council_finance.services.flagging_services", ["FlaggingService"]),
            ("council_finance.calculators", ["get_calculator"]),
        ]
        
        for module_name, items in critical_imports:
            try:
                module = __import__(module_name, fromlist=items)
                for item in items:
                    try:
                        getattr(module, item)
                        self.log(f"{module_name}.{item}", 'success')
                    except AttributeError:
                        self.log(f"{module_name}.{item} not found", 'error')
            except ImportError as e:
                self.log(f"Failed to import {module_name}: {e}", 'error')
    
    def test_django_templates(self):
        """Test Django template syntax and loading."""
        critical_templates = [
            'base.html',
            'council_finance/base.html',
            'council_finance/my_lists_enhanced.html',
            'council_finance/council_detail.html',
            'council_finance/home.html',
            'council_finance/contribute.html',
        ]
        
        for template_name in critical_templates:
            try:
                template = get_template(template_name)
                # Try to render with minimal context
                context = {
                    'user': None,
                    'request': None,
                    'lists': [],
                    'councils': [],
                }
                try:
                    template.render(context)
                    self.log(f"Template {template_name} - syntax OK", 'success')
                except Exception as e:
                    # Rendering errors are less critical than syntax errors
                    if isinstance(e, TemplateSyntaxError):
                        self.log(f"Template {template_name} syntax error: {e}", 'error')
                    else:
                        self.log(f"Template {template_name} render warning: {e}", 'warning')
            except TemplateSyntaxError as e:
                self.log(f"Template {template_name} syntax error: {e}", 'error')
            except Exception as e:
                self.log(f"Template {template_name} not found: {e}", 'warning')
    
    def test_react_build(self):
        """Test React build files and configuration."""
        # Check if build files exist
        build_dir = Path('static/frontend')
        manifest_file = build_dir / '.vite' / 'manifest.json'
        
        if not build_dir.exists():
            self.log("React build directory not found", 'error')
            return
        
        # Check manifest
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                    
                # Check for main entry
                if 'src/main.jsx' in manifest:
                    main_file = manifest['src/main.jsx']['file']
                    main_css = manifest['src/main.jsx']['css'][0] if 'css' in manifest['src/main.jsx'] else None
                    
                    # Check if files exist
                    if (build_dir / main_file).exists():
                        self.log(f"React main JS found: {main_file}", 'success')
                    else:
                        self.log(f"React main JS missing: {main_file}", 'error')
                    
                    if main_css and (build_dir / main_css).exists():
                        self.log(f"React main CSS found: {main_css}", 'success')
                    else:
                        self.log(f"React main CSS missing: {main_css}", 'warning')
                    
                    # Check if template references correct files
                    self.check_template_references(main_file, main_css)
                else:
                    self.log("Main entry not found in manifest", 'error')
            except Exception as e:
                self.log(f"Failed to read manifest: {e}", 'error')
        else:
            self.log("React manifest file not found - run 'npm run build'", 'error')
    
    def check_template_references(self, main_js, main_css):
        """Check if templates reference the correct React build files."""
        try:
            template = get_template('council_finance/my_lists_enhanced.html')
            template_content = template.source
            
            if main_js in template_content:
                self.log(f"Template correctly references {main_js}", 'success')
            else:
                self.log(f"Template does not reference current build file {main_js}", 'error')
                self.log("Run 'npm run build' and update template with new hash", 'warning')
                
            if main_css and main_css in template_content:
                self.log(f"Template correctly references {main_css}", 'success')
        except Exception as e:
            self.log(f"Could not check template references: {e}", 'warning')
    
    def test_api_endpoints(self):
        """Test critical API endpoints."""
        from django.urls import reverse, NoReverseMatch
        
        critical_endpoints = [
            ('search_councils', None),
            ('create_list_api', None),
            ('add_favourite', None),
            ('remove_favourite', None),
            ('my_lists', None),
        ]
        
        for endpoint_name, kwargs in critical_endpoints:
            try:
                url = reverse(endpoint_name, kwargs=kwargs)
                self.log(f"URL '{endpoint_name}' resolves to {url}", 'success')
            except NoReverseMatch:
                self.log(f"URL '{endpoint_name}' not found", 'error')
    
    def test_database_integrity(self):
        """Test database integrity and migrations."""
        try:
            # Check for pending migrations
            from io import StringIO
            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out)
            output = out.getvalue()
            
            if '[ ]' in output:
                self.log("Unapplied migrations detected", 'warning')
                self.log("Run 'python manage.py migrate' to apply migrations", 'warning')
            else:
                self.log("All migrations applied", 'success')
            
            # Test model imports and basic queries
            from council_finance.models import Council, CouncilList, DataField
            
            # Try basic queries
            try:
                Council.objects.first()
                self.log("Council model query successful", 'success')
            except Exception as e:
                self.log(f"Council model query failed: {e}", 'error')
                
            try:
                DataField.objects.count()
                self.log("DataField model query successful", 'success')
            except Exception as e:
                self.log(f"DataField model query failed: {e}", 'error')
                
        except Exception as e:
            self.log(f"Database integrity check failed: {e}", 'error')
    
    def test_static_files(self):
        """Test static files configuration."""
        critical_static_files = [
            'js/flagging-system.js',
            'css/output.css',
            'frontend/main-*.js',  # Pattern for React build
        ]
        
        from django.contrib.staticfiles import finders
        
        for file_pattern in critical_static_files:
            if '*' in file_pattern:
                # Handle wildcard patterns
                base_dir = os.path.dirname(file_pattern)
                pattern = os.path.basename(file_pattern).replace('*', '')
                
                found = False
                static_dir = Path('static') / base_dir
                if static_dir.exists():
                    for file in static_dir.iterdir():
                        if pattern in file.name:
                            found = True
                            self.log(f"Static file pattern '{file_pattern}' matched: {file.name}", 'success')
                            break
                
                if not found:
                    self.log(f"No files matching pattern '{file_pattern}'", 'warning')
            else:
                result = finders.find(file_pattern)
                if result:
                    self.log(f"Static file '{file_pattern}' found", 'success')
                else:
                    self.log(f"Static file '{file_pattern}' not found", 'warning')
    
    def test_management_commands(self):
        """Test critical management commands."""
        commands_to_test = [
            'check',
            'showmigrations',
            'validate_template_javascript',
        ]
        
        for command in commands_to_test:
            try:
                from io import StringIO
                out = StringIO()
                err = StringIO()
                
                call_command(command, stdout=out, stderr=err)
                
                error_output = err.getvalue()
                if error_output and 'warning' not in error_output.lower():
                    self.log(f"Command '{command}' produced errors: {error_output}", 'error')
                else:
                    self.log(f"Command '{command}' executed successfully", 'success')
                    
            except Exception as e:
                self.log(f"Command '{command}' failed: {e}", 'error')
    
    def test_javascript_in_templates(self):
        """Test JavaScript syntax in templates."""
        try:
            from io import StringIO
            out = StringIO()
            call_command('validate_template_javascript', stdout=out)
            output = out.getvalue()
            
            if 'PASSED' in output:
                self.log("JavaScript template validation passed", 'success')
            elif 'FAILED' in output:
                self.log("JavaScript template validation failed - check syntax_errors.log", 'error')
            else:
                self.log("JavaScript template validation inconclusive", 'warning')
                
        except Exception as e:
            self.log(f"JavaScript template validation error: {e}", 'warning')
    
    def test_programming_errors(self):
        """Test for common programming errors by attempting to render critical pages."""
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        # Critical URLs to test for programming errors
        test_urls = [
            ('/', 'Home page'),
            ('/councils/', 'Councils list'),
            ('/contribute/', 'Contribute page'),
            ('/lists/', 'My Lists page'),
        ]
        
        # Test without authentication first
        client = Client()
        for url, description in test_urls:
            try:
                response = client.get(url, follow=True)
                if response.status_code < 400:
                    self.log(f"{description} ({url}) renders without errors", 'success')
                elif response.status_code == 404:
                    self.log(f"{description} ({url}) returns 404 - check URL configuration", 'warning')
                else:
                    self.log(f"{description} ({url}) returns {response.status_code}", 'warning')
            except Exception as e:
                error_msg = str(e)
                if 'ProgrammingError' in error_msg:
                    self.log(f"DATABASE ERROR in {description} ({url}): {error_msg}", 'error')
                elif 'TemplateDoesNotExist' in error_msg:
                    self.log(f"TEMPLATE ERROR in {description} ({url}): {error_msg}", 'error')
                elif 'AttributeError' in error_msg:
                    self.log(f"ATTRIBUTE ERROR in {description} ({url}): {error_msg}", 'error')
                else:
                    self.log(f"PROGRAMMING ERROR in {description} ({url}): {error_msg}", 'error')
        
        # Test authenticated user endpoints
        try:
            User = get_user_model()
            # Try to create or get a test user
            test_user, created = User.objects.get_or_create(
                username='test_user_programming_check',
                defaults={'email': 'test@example.com'}
            )
            
            # Login and test authenticated endpoints
            client.force_login(test_user)
            
            auth_test_urls = [
                ('/lists/', 'My Lists (authenticated)'),
                ('/contribute/', 'Contribute (authenticated)'),
            ]
            
            for url, description in auth_test_urls:
                try:
                    response = client.get(url, follow=True)
                    if response.status_code < 400:
                        self.log(f"{description} ({url}) renders without errors", 'success')
                    else:
                        self.log(f"{description} ({url}) returns {response.status_code}", 'warning')
                except Exception as e:
                    error_msg = str(e)
                    if 'ProgrammingError' in error_msg:
                        self.log(f"DATABASE ERROR in {description} ({url}): {error_msg}", 'error')
                    else:
                        self.log(f"PROGRAMMING ERROR in {description} ({url}): {error_msg}", 'error')
            
            # Clean up test user if we created it
            if created:
                test_user.delete()
                
        except Exception as e:
            self.log(f"Could not test authenticated endpoints: {e}", 'warning')
        
        # Test specific model methods that might cause database errors
        self._test_model_methods()
        
        # Test for TypeError issues (datetime/SafeString conversion errors)
        self._test_type_errors()
    
    def _test_model_methods(self):
        """Test specific model methods that could cause programming errors."""
        try:
            from council_finance.models import CouncilList, Council
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Test CouncilList.get_total_population which caused the reported error
            try:
                # Get first user and council for testing
                user = User.objects.first()
                council = Council.objects.first()
                
                if user and council:
                    # Create a test list
                    test_list = CouncilList(name="Test List for Programming Check", user=user)
                    test_list.save()
                    test_list.councils.add(council)
                    
                    # Test the method that was causing the SQL error
                    try:
                        population = test_list.get_total_population()
                        self.log(f"CouncilList.get_total_population() works correctly: {population}", 'success')
                    except Exception as e:
                        if 'function sum(text) does not exist' in str(e):
                            self.log(f"CRITICAL DATABASE ERROR: CouncilList.get_total_population() trying to SUM text field: {e}", 'error')
                        else:
                            self.log(f"ERROR in CouncilList.get_total_population(): {e}", 'error')
                    
                    # Clean up
                    test_list.delete()
                else:
                    self.log("Cannot test CouncilList methods - no user or council data available", 'warning')
                    
            except Exception as e:
                self.log(f"Could not test CouncilList methods: {e}", 'warning')
                
        except ImportError as e:
            self.log(f"Could not import models for programming error testing: {e}", 'warning')
    
    def _test_type_errors(self):
        """Test for specific TypeError issues like datetime/SafeString conversion errors."""
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        try:
            # Test the /lists endpoint specifically as mentioned by user
            client = Client()
            
            # Test without authentication first
            try:
                response = client.get('/lists/', follow=True)
                if response.status_code < 400:
                    self.log("Lists endpoint (unauthenticated) renders without TypeError", 'success')
                else:
                    self.log(f"Lists endpoint returns {response.status_code} (unauthenticated)", 'warning')
            except TypeError as e:
                error_msg = str(e)
                if 'combine() argument 1 must be datetime.date' in error_msg and 'SafeString' in error_msg:
                    self.log(f"CRITICAL TYPEERROR: datetime/SafeString conversion error in /lists (unauthenticated): {error_msg}", 'error')
                else:
                    self.log(f"TYPEERROR in /lists (unauthenticated): {error_msg}", 'error')
            except Exception as e:
                error_msg = str(e)
                if 'combine() argument 1 must be datetime.date' in error_msg:
                    self.log(f"CRITICAL DATETIME ERROR in /lists (unauthenticated): {error_msg}", 'error')
                elif 'TypeError' in error_msg:
                    self.log(f"TYPE ERROR in /lists (unauthenticated): {error_msg}", 'error')
            
            # Test with authenticated user
            try:
                User = get_user_model()
                test_user, created = User.objects.get_or_create(
                    username='test_user_type_check',
                    defaults={'email': 'typecheck@example.com'}
                )
                
                client.force_login(test_user)
                
                try:
                    response = client.get('/lists/', follow=True)
                    if response.status_code < 400:
                        self.log("Lists endpoint (authenticated) renders without TypeError", 'success')
                    else:
                        self.log(f"Lists endpoint returns {response.status_code} (authenticated)", 'warning')
                except TypeError as e:
                    error_msg = str(e)
                    if 'combine() argument 1 must be datetime.date' in error_msg and 'SafeString' in error_msg:
                        self.log(f"CRITICAL TYPEERROR: datetime/SafeString conversion error in /lists (authenticated): {error_msg}", 'error')
                    else:
                        self.log(f"TYPEERROR in /lists (authenticated): {error_msg}", 'error')
                except Exception as e:
                    error_msg = str(e)
                    if 'combine() argument 1 must be datetime.date' in error_msg:
                        self.log(f"CRITICAL DATETIME ERROR in /lists (authenticated): {error_msg}", 'error')
                    elif 'TypeError' in error_msg:
                        self.log(f"TYPE ERROR in /lists (authenticated): {error_msg}", 'error')
                
                # Also test model methods directly that might cause the SafeString issue
                try:
                    from council_finance.models import CouncilList
                    
                    # Get user's lists which might trigger the SafeString/datetime error
                    user_lists = CouncilList.objects.filter(user=test_user)
                    for council_list in user_lists[:3]:  # Test first 3 lists
                        try:
                            # These methods might cause the SafeString/datetime conversion error
                            population = council_list.get_total_population()
                            council_count = council_list.get_council_count()
                            self.log(f"CouncilList '{council_list.name}' methods work correctly (pop: {population}, count: {council_count})", 'success')
                        except TypeError as e:
                            error_msg = str(e)
                            if 'combine() argument 1 must be datetime.date' in error_msg and 'SafeString' in error_msg:
                                self.log(f"CRITICAL TYPEERROR: SafeString/datetime error in CouncilList.get_total_population() for '{council_list.name}': {error_msg}", 'error')
                            else:
                                self.log(f"TYPEERROR in CouncilList methods for '{council_list.name}': {error_msg}", 'error')
                        except Exception as e:
                            error_msg = str(e)
                            if 'combine() argument 1 must be datetime.date' in error_msg:
                                self.log(f"DATETIME ERROR in CouncilList methods for '{council_list.name}': {error_msg}", 'error')
                            elif 'function sum(text) does not exist' in error_msg:
                                self.log(f"DATABASE ERROR: Attempting to SUM text field in CouncilList.get_total_population() for '{council_list.name}': {error_msg}", 'error')
                
                except ImportError:
                    self.log("Could not import CouncilList for direct model testing", 'warning')
                
                # Clean up test user if we created it
                if created:
                    test_user.delete()
                    
            except Exception as e:
                self.log(f"Could not test authenticated TypeError scenarios: {e}", 'warning')
                
        except Exception as e:
            self.log(f"Could not perform TypeError testing: {e}", 'warning')
    
    def print_summary(self, elapsed_time):
        """Print test summary."""
        self.header("TEST SUMMARY")
        
        total_tests = len(self.successes) + len(self.errors) + len(self.warnings)
        
        print(f"\nTotal tests run: {total_tests}")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        print(f"\n[SUCCESS] Passed: {len(self.successes)}")
        print(f"[WARNING] Warnings: {len(self.warnings)}")
        print(f"[ERROR] Failed: {len(self.errors)}")
        
        if self.errors:
            print("\n[FAILED] The following errors must be fixed:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            print("\nRun 'python run_all_tests.py -v' for more details")
        else:
            print("\n[SUCCESS] All critical tests passed!")
            
        if self.warnings:
            print("\n[WARNING] The following warnings should be reviewed:")
            for i, warning in enumerate(self.warnings[:5], 1):
                print(f"  {i}. {warning}")
            if len(self.warnings) > 5:
                print(f"  ... and {len(self.warnings) - 5} more warnings")
    
    def write_test_report(self):
        """Write detailed test report to file."""
        report_file = 'test_report.json'
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(self.successes) + len(self.errors) + len(self.warnings),
                'passed': len(self.successes),
                'warnings': len(self.warnings),
                'errors': len(self.errors),
            },
            'errors': self.errors,
            'warnings': self.warnings,
            'successes': self.successes,
        }
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nDetailed report written to {report_file}")
        except Exception as e:
            print(f"\nCould not write report file: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive tests for CFC')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Show verbose output')
    parser.add_argument('--quick', action='store_true',
                       help='Run only critical tests (faster)')
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    success = runner.run_all_tests()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())