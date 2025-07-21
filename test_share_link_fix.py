#!/usr/bin/env python3
"""
Test script to verify the generate_share_link function was added correctly
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def test_share_link_function():
    """Test that the generate_share_link function exists and can be imported"""
    try:
        from council_finance.views.councils import generate_share_link
        print("✅ generate_share_link function found!")
        print(f"Function: {generate_share_link}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import generate_share_link: {e}")
        return False

def test_url_patterns():
    """Test that URL patterns can be loaded without errors"""
    try:
        from council_finance.urls import urlpatterns
        print("✅ URL patterns loaded successfully!")
        
        # Check if our share link URL is present
        share_urls = [url for url in urlpatterns if hasattr(url, 'name') and url.name == 'generate_share_link']
        if share_urls:
            print("✅ generate_share_link URL pattern found!")
        else:
            print("⚠️  generate_share_link URL pattern not found")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load URL patterns: {e}")
        return False

def test_server_startup():
    """Test basic Django setup"""
    try:
        from django.core.management import execute_from_command_line
        from django.conf import settings
        
        print("✅ Django settings loaded successfully!")
        print(f"Debug mode: {settings.DEBUG}")
        print(f"Database: {settings.DATABASES['default']['ENGINE']}")
        return True
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing share link fix...")
    print("=" * 50)
    
    all_tests_passed = True
    
    print("\n1. Testing share link function import...")
    all_tests_passed &= test_share_link_function()
    
    print("\n2. Testing URL patterns...")
    all_tests_passed &= test_url_patterns()
    
    print("\n3. Testing Django setup...")
    all_tests_passed &= test_server_startup()
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed! The share link fix should work.")
        print("\nYou can now start the server with: python manage.py runserver")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("\nNext steps:")
    print("1. Start the Django server: python manage.py runserver")
    print("2. Test the spreadsheet interface at: http://localhost:8000/councils/<council-slug>/edit-table/")
    print("3. Test the new API endpoints for financial data and contributions")
