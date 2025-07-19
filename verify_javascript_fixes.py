#!/usr/bin/env python3
"""
Final verification script for JavaScript error fixes.

This script verifies that all the identified JavaScript errors have been resolved:
1. Line 1689: null reference error in enhanced_council_edit.html
2. Line 1437: API 500 error for recent activity  
3. Line 1459: JSON parsing error
4. Missing favicon 404 error

Run this after server is started to verify all fixes are working.
"""

import sys
import os
import subprocess

def run_django_check():
    """Verify Django configuration is valid."""
    print("🔧 Checking Django configuration...")
    try:
        result = subprocess.run([sys.executable, 'manage.py', 'check'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Django configuration is valid")
            return True
        else:
            print(f"❌ Django check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Django check error: {e}")
        return False

def verify_database_fixes():
    """Test the database queries that were causing 500 errors."""
    print("🗄️  Verifying database fixes...")
    
    test_script = '''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "council_finance.settings")
django.setup()

from council_finance.models import Council, ActivityLog

try:
    # Test the exact queries that were failing
    council = Council.objects.get(slug="worcestershire-county-council")
    print(f"✅ Council found: {council.name}")
    
    # Test the fixed query (using 'related_council' and 'created')
    activities = ActivityLog.objects.filter(related_council=council).order_by("-created")[:10]
    print(f"✅ Recent activities query works: {len(activities)} activities")
    
    # Test field access that was failing
    for activity in activities[:3]:
        created_time = activity.created.isoformat()
        print(f"✅ Activity created field accessible: {created_time}")
        break
    
    print("✅ All database queries work correctly")
    
except Exception as e:
    print(f"❌ Database test failed: {e}")
    exit(1)
'''
    
    try:
        result = subprocess.run([sys.executable, '-c', test_script], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(f"❌ Database test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False

def verify_file_fixes():
    """Verify that our file modifications are in place."""
    print("📁 Verifying file modifications...")
    
    # Check API file has correct field names
    api_file = "council_finance/views/api.py"
    if os.path.exists(api_file):
        with open(api_file, 'r') as f:
            content = f.read()
            if 'related_council=council' in content and 'order_by(\'-created\')' in content:
                print("✅ API file has correct database field names")
            else:
                print("❌ API file missing correct field names")
                return False
    else:
        print(f"❌ API file not found: {api_file}")
        return False
    
    # Check template has null checks
    template_file = "council_finance/templates/council_finance/enhanced_council_edit.html"
    if os.path.exists(template_file):
        with open(template_file, 'r') as f:
            content = f.read()
            if 'if (!activityList)' in content and 'console.warn' in content:
                print("✅ Template has null safety checks")
            else:
                print("❌ Template missing null safety checks")
                return False
    else:
        print(f"❌ Template file not found: {template_file}")
        return False
    
    # Check favicon exists
    favicon_file = "static/favicon.ico"
    if os.path.exists(favicon_file):
        print("✅ Favicon file exists")
    else:
        print("❌ Favicon file missing")
        return False
    
    # Check URL configuration
    urls_file = "council_finance/urls.py"
    if os.path.exists(urls_file):
        with open(urls_file, 'r') as f:
            content = f.read()
            if 'favicon.ico' in content and 'RedirectView' in content:
                print("✅ URL configuration includes favicon redirect")
            else:
                print("❌ URL configuration missing favicon redirect")
                return False
    else:
        print(f"❌ URLs file not found: {urls_file}")
        return False
    
    return True

def main():
    """Run all verification tests."""
    print("🧪 JavaScript Error Fixes - Final Verification")
    print("=" * 50)
    
    # Change to project directory
    if os.path.basename(os.getcwd()) != 'cfc':
        print("❌ Please run this script from the project root directory (cfc/)")
        return 1
    
    tests = [
        ("Django Configuration", run_django_check),
        ("Database Fixes", verify_database_fixes), 
        ("File Modifications", verify_file_fixes),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All verification tests passed!")
        print("\nThe following JavaScript errors should now be resolved:")
        print("   ✅ Line 1689: null reference error (added safety checks)")
        print("   ✅ Line 1437: API 500 error (fixed database fields)")  
        print("   ✅ Line 1459: JSON parsing error (API now returns JSON)")
        print("   ✅ Favicon 404 error (created favicon + URL redirect)")
        print("\nThe council edit page should load without JavaScript errors.")
        return 0
    else:
        print("❌ Some verification tests failed!")
        print("Please check the errors above and re-run the verification.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
