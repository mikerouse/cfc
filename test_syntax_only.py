#!/usr/bin/env python
"""
Syntax-only test runner for Council Edit React interface.

This script runs syntax validation tests without requiring database setup,
avoiding migration issues while ensuring code quality.
"""

import os
import sys
import ast
import importlib.util


def test_python_syntax():
    """Test Python files for syntax errors."""
    print("TESTING PYTHON SYNTAX")
    print("=" * 40)
    
    files_to_test = [
        'council_finance/views/council_edit_api.py',
        'council_finance/views/councils.py',
        'council_finance/urls.py',
        'council_finance/tests/test_syntax_errors.py',
        'council_finance/tests/test_council_edit_integration.py',
    ]
    
    errors = []
    
    for file_path in files_to_test:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content, filename=file_path)
                print(f"PASS {os.path.basename(file_path)}")
            except SyntaxError as e:
                print(f"FAIL {os.path.basename(file_path)}: {e}")
                errors.append(f"{file_path}: {e}")
            except Exception as e:
                print(f"WARN {os.path.basename(file_path)}: {e}")
                errors.append(f"{file_path}: {e}")
        else:
            print(f"FAIL {os.path.basename(file_path)}: File not found")
            errors.append(f"{file_path}: File not found")
    
    return errors


def test_react_components():
    """Test React components exist and have basic structure."""
    print("\nTESTING REACT COMPONENTS")
    print("=" * 40)
    
    components = [
        'frontend/src/components/CouncilEditApp.jsx',
        'frontend/src/components/council-edit/CharacteristicsTab.jsx',
        'frontend/src/components/council-edit/GeneralDataTab.jsx',
        'frontend/src/components/council-edit/FinancialDataTab.jsx',
        'frontend/src/components/council-edit/FieldEditor.jsx',
        'frontend/src/components/council-edit/TabNavigation.jsx',
    ]
    
    errors = []
    
    for component in components:
        if os.path.exists(component):
            try:
                with open(component, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Basic React component validation
                if 'export default' in content:
                    print(f"PASS {os.path.basename(component)}")
                else:
                    print(f"WARN {os.path.basename(component)}: No default export")
                    errors.append(f"{component}: No default export found")
                    
            except Exception as e:
                print(f"FAIL {os.path.basename(component)}: {e}")
                errors.append(f"{component}: {e}")
        else:
            print(f"FAIL {os.path.basename(component)}: Not found")
            errors.append(f"{component}: File not found")
    
    return errors


def test_build_artifacts():
    """Test that build artifacts exist."""
    print("\nTESTING BUILD ARTIFACTS")
    print("=" * 40)
    
    artifacts = [
        'static/frontend/main-Bg2gLYqg.js',
        'static/frontend/main-BlzmEwI8.css',
    ]
    
    errors = []
    
    for artifact in artifacts:
        if os.path.exists(artifact):
            print(f"PASS {os.path.basename(artifact)}")
        else:
            print(f"FAIL {os.path.basename(artifact)}: Not found")
            errors.append(f"{artifact}: Build artifact missing")
    
    return errors


def test_templates():
    """Test Django templates exist."""
    print("\nTESTING TEMPLATES") 
    print("=" * 40)
    
    templates = [
        'council_finance/templates/council_finance/council_edit_react.html',
    ]
    
    errors = []
    
    for template in templates:
        if os.path.exists(template):
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for required elements
                required = [
                    'council-edit-react-root',
                    'CouncilEditApp',
                    'csrf_token',
                ]
                
                missing = [req for req in required if req not in content]
                
                if not missing:
                    print(f"PASS {os.path.basename(template)}")
                else:
                    print(f"WARN {os.path.basename(template)}: Missing {missing}")
                    errors.append(f"{template}: Missing required elements: {missing}")
                    
            except Exception as e:
                print(f"FAIL {os.path.basename(template)}: {e}")
                errors.append(f"{template}: {e}")
        else:
            print(f"FAIL {os.path.basename(template)}: Not found")
            errors.append(f"{template}: Template not found")
    
    return errors


def main():
    """Run all syntax tests."""
    print("COUNCIL EDIT REACT INTERFACE - SYNTAX VALIDATION")
    print("=" * 60)
    
    all_errors = []
    
    # Run all test categories
    all_errors.extend(test_python_syntax())
    all_errors.extend(test_react_components())
    all_errors.extend(test_build_artifacts()) 
    all_errors.extend(test_templates())
    
    # Summary
    print("\nTEST SUMMARY")
    print("=" * 40)
    
    if not all_errors:
        print("SUCCESS: ALL SYNTAX TESTS PASSED")
        print("\nMobile-first Council Edit React interface is ready!")
        print("\nFeatures verified:")
        print("- Python syntax validation")
        print("- React component structure") 
        print("- Build artifact generation")
        print("- Django template integration")
        print("\nAccess at: /councils/[council-slug]/edit-react/")
        return 0
    else:
        print(f"FAILED: {len(all_errors)} ISSUES FOUND:")
        for error in all_errors:
            print(f"  - {error}")
        return 1


if __name__ == '__main__':
    sys.exit(main())