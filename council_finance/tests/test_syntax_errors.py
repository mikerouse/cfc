"""
Test suite for syntax errors across the codebase.

This test ensures all Python files can be parsed without syntax errors,
including the new React council edit API and view files.
"""

import os
import ast
import sys
from django.test import TestCase
from django.conf import settings


class SyntaxErrorTests(TestCase):
    """Test all Python files for syntax errors."""
    
    def get_python_files(self, directory):
        """Recursively find all Python files in a directory."""
        python_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip certain directories
            skip_dirs = {
                '__pycache__', '.git', 'node_modules', 'venv', 'env', 
                '.venv', 'build', 'dist', 'static', 'media'
            }
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def test_council_finance_syntax(self):
        """Test all Python files in council_finance app for syntax errors."""
        council_finance_dir = os.path.dirname(os.path.dirname(__file__))
        python_files = self.get_python_files(council_finance_dir)
        
        syntax_errors = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # Parse the file
                ast.parse(source_code, filename=file_path)
                
            except SyntaxError as e:
                relative_path = os.path.relpath(file_path, council_finance_dir)
                syntax_errors.append(f"{relative_path}: {str(e)}")
            except UnicodeDecodeError as e:
                # Try with different encoding
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        source_code = f.read()
                    ast.parse(source_code, filename=file_path)
                except (SyntaxError, UnicodeDecodeError) as e:
                    relative_path = os.path.relpath(file_path, council_finance_dir)
                    syntax_errors.append(f"{relative_path}: Encoding error - {str(e)}")
            except Exception as e:
                relative_path = os.path.relpath(file_path, council_finance_dir)
                syntax_errors.append(f"{relative_path}: Unexpected error - {str(e)}")
        
        if syntax_errors:
            error_message = "Syntax errors found in:\n" + "\n".join(syntax_errors)
            self.fail(error_message)
        
        self.assertGreater(len(python_files), 0, "No Python files found to test")
    
    def test_core_app_syntax(self):
        """Test all Python files in core app for syntax errors."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        core_dir = os.path.join(project_root, 'core')
        
        if not os.path.exists(core_dir):
            self.skipTest("Core app directory not found")
        
        python_files = self.get_python_files(core_dir)
        syntax_errors = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                ast.parse(source_code, filename=file_path)
            except SyntaxError as e:
                relative_path = os.path.relpath(file_path, core_dir)
                syntax_errors.append(f"core/{relative_path}: {str(e)}")
            except Exception as e:
                relative_path = os.path.relpath(file_path, core_dir)
                syntax_errors.append(f"core/{relative_path}: {str(e)}")
        
        if syntax_errors:
            error_message = "Syntax errors found in core app:\n" + "\n".join(syntax_errors)
            self.fail(error_message)
    
    def test_specific_new_files_syntax(self):
        """Test syntax of specific new files added for council edit interface."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Test the new council edit API file
        council_edit_api = os.path.join(
            project_root, 'council_finance', 'views', 'council_edit_api.py'
        )
        
        if os.path.exists(council_edit_api):
            try:
                with open(council_edit_api, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                ast.parse(source_code, filename=council_edit_api)
            except SyntaxError as e:
                self.fail(f"Syntax error in council_edit_api.py: {str(e)}")
        else:
            self.fail("council_edit_api.py not found")
        
        # Test that councils.py still compiles after our additions
        councils_view = os.path.join(
            project_root, 'council_finance', 'views', 'councils.py'
        )
        
        if os.path.exists(councils_view):
            try:
                with open(councils_view, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                ast.parse(source_code, filename=councils_view)
            except SyntaxError as e:
                self.fail(f"Syntax error in councils.py: {str(e)}")
        else:
            self.fail("councils.py not found")
    
    def test_imports_work(self):
        """Test that key imports work without syntax errors."""
        try:
            # Test the new council edit API imports
            from council_finance.views.council_edit_api import (
                council_characteristics_api,
                save_council_characteristic_api,
                council_temporal_data_api,
                save_temporal_data_api,
                council_available_years_api,
                council_edit_context_api,
            )
            
            # Test the updated councils view import
            from council_finance.views.councils import council_edit_react
            
        except ImportError as e:
            self.fail(f"Import error: {str(e)}")
        except SyntaxError as e:
            self.fail(f"Syntax error during import: {str(e)}")
    
    def test_urls_configuration(self):
        """Test that URL configuration doesn't have syntax errors."""
        try:
            from django.urls import reverse
            
            # Test that our new URLs can be resolved
            test_urls = [
                ('council_edit_react', ['test-council']),
                ('council_characteristics_api', ['test-council']),
                ('council_temporal_data_api', ['test-council', 1]),
                ('save_temporal_data_api', ['test-council', 1]),
                ('council_available_years_api', ['test-council']),
                ('council_edit_context_api', ['test-council']),
            ]
            
            for url_name, args in test_urls:
                try:
                    reverse(url_name, args=args)
                except Exception as e:
                    self.fail(f"URL configuration error for {url_name}: {str(e)}")
                    
        except ImportError as e:
            self.fail(f"URL import error: {str(e)}")


class ReactComponentTests(TestCase):
    """Test React components for basic structure and syntax."""
    
    def get_jsx_files(self, directory):
        """Find all JSX files in a directory."""
        jsx_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip node_modules and build directories
            dirs[:] = [d for d in dirs if d not in {'node_modules', 'build', 'dist'}]
            
            for file in files:
                if file.endswith(('.jsx', '.js')):
                    jsx_files.append(os.path.join(root, file))
        
        return jsx_files
    
    def test_react_components_exist(self):
        """Test that React components exist and have basic structure."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        frontend_dir = os.path.join(project_root, 'frontend', 'src', 'components')
        
        if not os.path.exists(frontend_dir):
            self.skipTest("Frontend components directory not found")
        
        # Check for key React components
        key_components = [
            'CouncilEditApp.jsx',
            'council-edit/CharacteristicsTab.jsx',
            'council-edit/GeneralDataTab.jsx', 
            'council-edit/FinancialDataTab.jsx',
            'council-edit/FieldEditor.jsx',
            'council-edit/TabNavigation.jsx',
        ]
        
        missing_components = []
        
        for component in key_components:
            component_path = os.path.join(frontend_dir, component)
            if not os.path.exists(component_path):
                missing_components.append(component)
            else:
                # Basic syntax check - look for common patterns
                try:
                    with open(component_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for basic React patterns
                    if 'export default' not in content and 'module.exports' not in content:
                        missing_components.append(f"{component} (no export)")
                    
                except Exception as e:
                    missing_components.append(f"{component} (read error: {str(e)})")
        
        if missing_components:
            self.fail(f"Missing or invalid React components: {', '.join(missing_components)}")
    
    def test_frontend_build_artifacts(self):
        """Test that frontend build artifacts exist."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        static_dir = os.path.join(project_root, 'static', 'frontend')
        
        if not os.path.exists(static_dir):
            self.skipTest("Static frontend directory not found")
        
        # Check for build artifacts
        expected_files = [
            'main-BhCRMDWS.js',  # Current build hash
            'main-BlzmEwI8.css',
        ]
        
        missing_files = []
        for filename in expected_files:
            file_path = os.path.join(static_dir, filename)
            if not os.path.exists(file_path):
                missing_files.append(filename)
        
        if missing_files:
            self.fail(f"Missing frontend build artifacts: {', '.join(missing_files)}")


class TemplateTests(TestCase):
    """Test Django templates for basic syntax."""
    
    def test_council_edit_react_template(self):
        """Test the new React council edit template."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        template_path = os.path.join(
            project_root, 'council_finance', 'templates', 
            'council_finance', 'council_edit_react.html'
        )
        
        if not os.path.exists(template_path):
            self.fail("council_edit_react.html template not found")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required elements
            required_elements = [
                'council-edit-react-root',
                'CouncilEditApp',
                'council_data_json',
                'years_data_json',
                'csrf_token',
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                self.fail(f"Template missing required elements: {', '.join(missing_elements)}")
                
        except Exception as e:
            self.fail(f"Error reading template: {str(e)}")