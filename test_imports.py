#!/usr/bin/env python3
"""
Test script to verify all model imports work correctly.
Run this after making changes to models to catch ImportErrors early.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def test_imports():
    """Test all critical imports in the project."""
    print("\n" + "="*70)
    print("TESTING MODEL IMPORTS")
    print("="*70)
    
    errors = []
    successful = []
    
    # List of imports to test
    imports_to_test = [
        # Core models
        ("council_finance.models", ["Council", "CouncilList", "DataField", "FinancialYear"]),
        ("council_finance.models.council", ["Council"]),
        ("council_finance.models.council_list", ["CouncilList"]),
        ("council_finance.models.field", ["DataField"]),
        ("council_finance.models.new_data_model", ["CouncilCharacteristic", "FinancialFigure"]),
        
        # Views
        ("council_finance.views.general", ["my_lists", "create_list_api"]),
        ("council_finance.views.api", ["search_councils"]),
        
        # Forms
        ("council_finance.forms", ["CouncilListForm"]),
    ]
    
    for module_name, items in imports_to_test:
        print(f"\nTesting {module_name}...")
        try:
            module = __import__(module_name, fromlist=items)
            for item in items:
                try:
                    getattr(module, item)
                    successful.append(f"{module_name}.{item}")
                    print(f"  [OK] {item}")
                except AttributeError as e:
                    errors.append(f"{module_name}.{item}: {e}")
                    print(f"  [ERROR] {item} - NOT FOUND")
        except ImportError as e:
            errors.append(f"{module_name}: {e}")
            print(f"  [ERROR] Module import failed: {e}")
    
    # Test specific method imports that caused issues
    print("\nTesting specific method calls...")
    try:
        from council_finance.models.council_list import CouncilList
        # Test get_total_population which had the import error
        test_list = CouncilList(name="Test", user_id=1)
        # Don't actually call it, just check the method exists
        if hasattr(test_list, 'get_total_population'):
            print("  [OK] CouncilList.get_total_population exists")
            successful.append("CouncilList.get_total_population")
        else:
            print("  [ERROR] CouncilList.get_total_population NOT FOUND")
            errors.append("CouncilList.get_total_population: Method not found")
    except Exception as e:
        errors.append(f"CouncilList method test: {e}")
        print(f"  [ERROR] Error testing CouncilList methods: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("IMPORT TEST SUMMARY")
    print("="*70)
    print(f"Successful imports: {len(successful)}")
    print(f"Failed imports: {len(errors)}")
    
    if errors:
        print("\n[FAILED] IMPORTS:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n[SUCCESS] All imports successful!")
        return True

def test_template_loading():
    """Test that key templates can be loaded."""
    print("\n" + "="*70)
    print("TESTING TEMPLATE LOADING")
    print("="*70)
    
    from django.template.loader import get_template
    from django.template import TemplateSyntaxError
    
    templates_to_test = [
        'council_finance/my_lists_enhanced.html',
        'council_finance/base.html',
        'base.html',
    ]
    
    errors = []
    for template_name in templates_to_test:
        print(f"\nTesting {template_name}...")
        try:
            template = get_template(template_name)
            print(f"  [OK] Template loaded successfully")
        except TemplateSyntaxError as e:
            errors.append(f"{template_name}: {e}")
            print(f"  [ERROR] Template syntax error: {e}")
        except Exception as e:
            errors.append(f"{template_name}: {e}")
            print(f"  [ERROR] Error: {e}")
    
    return len(errors) == 0

def main():
    """Run all tests."""
    print("\nDJANGO PROJECT IMPORT TESTER")
    print("Testing imports and templates after changes...")
    
    import_success = test_imports()
    template_success = test_template_loading()
    
    print("\n" + "="*70)
    print("FINAL RESULT")
    print("="*70)
    
    if import_success and template_success:
        print("[SUCCESS] All tests passed! Safe to proceed.")
        return 0
    else:
        print("[FAILED] Some tests failed. Fix the issues before proceeding.")
        return 1

if __name__ == '__main__':
    sys.exit(main())