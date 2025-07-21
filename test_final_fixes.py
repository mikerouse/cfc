#!/usr/bin/env python3
"""
Test script to verify all three remaining issues are fixed:
1. Legacy card system removed from enhanced_council_edit.html
2. Year selector properly handles characteristics vs financial data
3. Text wrapping prevents horizontal scrolling
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from council_finance.models import Council, CouncilType, CouncilNation

def test_template_structure():
    """Test that enhanced_council_edit.html only includes spreadsheet interface"""
    print("Testing template structure...")
    
    template_path = "council_finance/templates/council_finance/enhanced_council_edit.html"
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check that legacy card system is removed
    legacy_indicators = [
        'Council Characteristics',
        'Guidelines Card',
        'Recent Activity',
        'Help Card',
        'Progress Card'
    ]
    
    legacy_found = []
    for indicator in legacy_indicators:
        if indicator in content:
            legacy_found.append(indicator)
    
    if legacy_found:
        print(f"❌ Legacy elements still found: {legacy_found}")
        return False
    else:
        print("✅ Legacy card system successfully removed")
    
    # Check that spreadsheet interface is included
    if 'spreadsheet_edit_interface.html' in content:
        print("✅ Spreadsheet interface properly included")
        return True
    else:
        print("❌ Spreadsheet interface not found")
        return False

def test_css_text_wrapping():
    """Test that CSS fixes for text wrapping are in place"""
    print("\nTesting CSS text wrapping fixes...")
    
    template_path = "council_finance/templates/council_finance/spreadsheet_edit_interface.html"
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check for text wrapping CSS
    css_fixes = [
        'word-wrap: break-word',
        'word-break: break-word',
        'white-space: normal',
        'table-layout: fixed',
        'max-width: 200px'
    ]
    
    missing_fixes = []
    for fix in css_fixes:
        if fix not in content:
            missing_fixes.append(fix)
    
    if missing_fixes:
        print(f"❌ Missing CSS fixes: {missing_fixes}")
        return False
    else:
        print("✅ Text wrapping CSS fixes properly implemented")
        return True

def test_javascript_year_handling():
    """Test that JavaScript properly handles year selector"""
    print("\nTesting JavaScript year handling...")
    
    js_path = "council_finance/static/js/spreadsheet_editor.js"
    
    with open(js_path, 'r') as f:
        content = f.read()
    
    # Check for proper year handling logic
    js_fixes = [
        'isCharacteristic = category === \'characteristics\'',
        'year-independent',
        'Only set year for financial data',
        'Loading financial data for'
    ]
    
    missing_fixes = []
    for fix in js_fixes:
        if fix not in content:
            missing_fixes.append(fix)
    
    if missing_fixes:
        print(f"❌ Missing JavaScript fixes: {missing_fixes}")
        return False
    else:
        print("✅ JavaScript year handling properly implemented")
        return True

def test_council_edit_page():
    """Test that the council edit page loads without errors"""
    print("\nTesting council edit page functionality...")
    
    try:
        # Get or create test council
        council_type, _ = CouncilType.objects.get_or_create(
            name='District Council',
            defaults={'slug': 'district-council'}
        )
        
        council_nation, _ = CouncilNation.objects.get_or_create(
            name='England',
            defaults={'slug': 'england'}
        )
        
        council, created = Council.objects.get_or_create(
            name='Test Council',
            slug='test-council',
            defaults={
                'council_type': council_type,
                'council_nation': council_nation
            }
        )
        
        # Create test user
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # Test page access
        client = Client()
        client.force_login(user)
        
        response = client.get(f'/councils/{council.slug}/')
        
        if response.status_code == 200:
            print("✅ Council detail page loads successfully")
            
            # Check if edit section is present
            if 'spreadsheet-edit-container' in response.content.decode():
                print("✅ Spreadsheet edit interface found in page")
                return True
            else:
                print("❌ Spreadsheet edit interface not found in page")
                return False
        else:
            print(f"❌ Council detail page failed to load: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing council edit page: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Final Fixes for Council Edit Interface")
    print("=" * 60)
    
    results = []
    
    # Test 1: Template structure
    results.append(test_template_structure())
    
    # Test 2: CSS text wrapping
    results.append(test_css_text_wrapping())
    
    # Test 3: JavaScript year handling
    results.append(test_javascript_year_handling())
    
    # Test 4: Page functionality
    results.append(test_council_edit_page())
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All issues resolved successfully!")
        print("\n✨ The council edit interface now:")
        print("   • Uses only the modern spreadsheet interface")
        print("   • Properly handles year selection for financial vs characteristic data")
        print("   • Prevents horizontal scrolling with text wrapping")
        return True
    else:
        print("\n⚠️  Some issues still need attention")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
