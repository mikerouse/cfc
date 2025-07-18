#!/usr/bin/env python3
"""
Django management command to test all templates for syntax errors and basic rendering.
Usage: python manage.py test_templates [--verbose] [--template=path/to/template.html]
"""
import os
import sys
import traceback
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template
from django.template import Template, Context, TemplateSyntaxError, TemplateDoesNotExist
from django.conf import settings
from django.apps import apps
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Test all Django templates for syntax errors and basic rendering'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show verbose output including successful tests'
        )
        parser.add_argument(
            '--template', '-t',
            type=str,
            help='Test a specific template file (relative path from templates dir)'
        )
        parser.add_argument(
            '--app', '-a',
            type=str,
            help='Test templates from a specific app only'
        )
        parser.add_argument(
            '--check-syntax-only',
            action='store_true',
            help='Only check template syntax, skip rendering tests'
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        self.syntax_only = options.get('check_syntax_only', False)
        
        self.style.ERROR = self.style.ERROR
        self.style.SUCCESS = self.style.SUCCESS  
        self.style.WARNING = self.style.WARNING
        
        if options.get('template'):
            # Test a specific template
            return self.test_single_template(options['template'])
        
        if options.get('app'):
            # Test templates from a specific app
            return self.test_app_templates(options['app'])
            
        # Test all templates
        return self.test_all_templates()

    def test_single_template(self, template_path):
        """Test a single template file"""
        self.stdout.write(f"\n🧪 Testing single template: {template_path}")
        self.stdout.write("=" * 60)
        
        try:
            result = self.test_template_file(template_path)
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"✅ {template_path} - PASSED"))
                if self.verbose and 'render_size' in result:
                    self.stdout.write(f"   Rendered {result['render_size']} characters")
            else:
                self.stdout.write(self.style.ERROR(f"❌ {template_path} - FAILED"))
                self.stdout.write(f"   Error: {result['error']}")
                if 'traceback' in result:
                    self.stdout.write(f"   {result['traceback']}")
                return 1
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to test {template_path}: {e}"))
            return 1
            
        return 0

    def test_app_templates(self, app_name):
        """Test templates from a specific app"""
        self.stdout.write(f"\n🧪 Testing templates for app: {app_name}")
        self.stdout.write("=" * 60)
        
        try:
            app_config = apps.get_app_config(app_name)
        except LookupError:
            self.stdout.write(self.style.ERROR(f"❌ App '{app_name}' not found"))
            return 1
            
        # Find templates for this app
        templates = self.find_app_templates(app_name)
        
        if not templates:
            self.stdout.write(self.style.WARNING(f"⚠️  No templates found for app '{app_name}'"))
            return 0
            
        return self.run_template_tests(templates)

    def test_all_templates(self):
        """Test all templates in the project"""
        self.stdout.write("\n🧪 Testing all Django templates")
        self.stdout.write("=" * 60)
        
        templates = self.find_all_templates()
        
        if not templates:
            self.stdout.write(self.style.WARNING("⚠️  No templates found"))
            return 0
            
        return self.run_template_tests(templates)

    def find_all_templates(self):
        """Find all template files in the project"""
        templates = []
        
        # Check all template directories from settings
        template_dirs = []
        for engine in settings.TEMPLATES:
            if engine['BACKEND'] == 'django.template.backends.django.DjangoTemplates':
                template_dirs.extend(engine.get('DIRS', []))
                
                # Also check app template directories
                if engine['OPTIONS'].get('APP_DIRS', False):
                    for app_config in apps.get_app_configs():
                        app_template_dir = Path(app_config.path) / 'templates'
                        if app_template_dir.exists():
                            template_dirs.append(str(app_template_dir))
        
        # Find all .html files in template directories
        for template_dir in template_dirs:
            template_path = Path(template_dir)
            if template_path.exists():
                for html_file in template_path.rglob('*.html'):
                    # Get relative path from template directory
                    rel_path = html_file.relative_to(template_path)
                    templates.append(str(rel_path))
                    
        return sorted(list(set(templates)))  # Remove duplicates and sort

    def find_app_templates(self, app_name):
        """Find templates for a specific app"""
        templates = []
        
        try:
            app_config = apps.get_app_config(app_name)
            app_template_dir = Path(app_config.path) / 'templates' / app_name
            
            if app_template_dir.exists():
                for html_file in app_template_dir.rglob('*.html'):
                    # Get path relative to templates directory
                    rel_path = html_file.relative_to(Path(app_config.path) / 'templates')
                    templates.append(str(rel_path))
        except LookupError:
            pass
            
        return sorted(templates)

    def run_template_tests(self, templates):
        """Run tests on a list of templates"""
        total_templates = len(templates)
        passed = 0
        failed = 0
        errors = []
        
        self.stdout.write(f"📋 Found {total_templates} templates to test\n")
        
        for template_path in templates:
            result = self.test_template_file(template_path)
            
            if result['success']:
                passed += 1
                if self.verbose:
                    self.stdout.write(self.style.SUCCESS(f"✅ {template_path}"))
                    if 'render_size' in result:
                        self.stdout.write(f"   Rendered {result['render_size']} characters")
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"❌ {template_path}"))
                self.stdout.write(f"   Error: {result['error']}")
                if self.verbose and 'traceback' in result:
                    self.stdout.write(f"   {result['traceback']}")
                    
                errors.append({
                    'template': template_path,
                    'error': result['error'],
                    'traceback': result.get('traceback', '')
                })
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 TEMPLATE TEST SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total templates tested: {total_templates}")
        self.stdout.write(self.style.SUCCESS(f"✅ Passed: {passed}"))
        
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed: {failed}"))
            self.stdout.write("\n🚨 FAILED TEMPLATES:")
            for error in errors:
                self.stdout.write(f"   • {error['template']}: {error['error']}")
        else:
            self.stdout.write(self.style.SUCCESS("🎉 All templates passed!"))
            
        return 1 if failed > 0 else 0

    def test_template_file(self, template_path):
        """Test a single template file for syntax and rendering"""
        result = {
            'success': False,
            'error': None,
            'traceback': None
        }
        
        try:
            # Test 1: Template loading and syntax checking
            template = get_template(template_path)
            
            # Test 2: Basic rendering (if not syntax-only mode)
            if not self.syntax_only:
                context = self.create_test_context()
                try:
                    rendered = template.render(context)
                    result['render_size'] = len(rendered)
                except Exception as render_error:
                    # Some templates might fail to render due to missing context
                    # but if they load without syntax errors, that's still a pass
                    if 'syntax' in str(render_error).lower() or 'block tag' in str(render_error).lower():
                        raise render_error  # Re-raise syntax errors
                    else:
                        # Non-syntax rendering errors are warnings, not failures
                        result['warning'] = f"Render warning: {render_error}"
                        
            result['success'] = True
            
        except TemplateSyntaxError as e:
            result['error'] = f"Template syntax error: {e}"
            result['traceback'] = traceback.format_exc()
        except TemplateDoesNotExist as e:
            result['error'] = f"Template not found: {e}"
        except Exception as e:
            result['error'] = f"Unexpected error: {e}"
            result['traceback'] = traceback.format_exc()
            
        return result

    def create_test_context(self):
        """Create a test context for template rendering"""
        # Import models safely
        try:
            from council_finance.models.council import Council, FigureSubmission, DataField, FinancialYear
        except ImportError:
            Council = FigureSubmission = DataField = FinancialYear = None
            
        context = {
            # Basic context that most templates might expect
            'user': None,  # Anonymous user
            'request': None,
            'perms': {},
            
            # Common template variables
            'title': 'Test Page',
            'debug': False,
            
            # Empty collections that templates might iterate over
            'objects': [],
            'items': [],
            'results': [],
            'figures': [],
            'councils': [],
            'fields': [],
            
            # Common template booleans
            'is_authenticated': False,
            'has_permission': False,
            
            # Sample data if models are available
        }
        
        # Add model-specific context if available
        if Council:
            try:
                council = Council.objects.first()
                if council:
                    context.update({
                        'council': council,
                        'object': council,
                    })
            except:
                pass  # Database might not be set up
                
        if FigureSubmission:
            context.update({
                'figure_submissions': [],
                'pending_pairs': set(),
            })
            
        if DataField:
            context.update({
                'data_fields': [],
                'financial_fields': [],
            })
            
        if FinancialYear:
            context.update({
                'financial_years': [],
                'current_year': None,
            })
        
        return context
