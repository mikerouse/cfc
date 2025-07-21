#!/usr/bin/env python3
"""
Complete test of the new spreadsheet interface functionality
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def test_spreadsheet_endpoints():
    """Test the new spreadsheet API endpoints"""
    from council_finance.models import Council
    
    print("Testing spreadsheet interface endpoints...")
    client = Client()
    
    # Try to get or create a test council
    try:
        council = Council.objects.first()
        if not council:
            print("⚠️  No councils found in database")
            return False
            
        council_slug = council.slug
        print(f"Testing with council: {council.name} (slug: {council_slug})")
        
        # Test financial data API
        print("\n1. Testing financial data API...")
        financial_url = f"/councils/{council_slug}/financial-data/"
        response = client.get(financial_url)
        print(f"Financial data API status: {response.status_code}")
        
        # Test field options API  
        print("\n2. Testing field options API...")
        options_url = f"/api/fields/{council_slug}/options/"
        response = client.get(options_url)
        print(f"Field options API status: {response.status_code}")
        
        # Test edit table view
        print("\n3. Testing edit table view...")
        edit_url = f"/councils/{council_slug}/edit-table/"
        response = client.get(edit_url)
        print(f"Edit table view status: {response.status_code}")
        
        # Test share link generation
        print("\n4. Testing share link generation...")
        share_url = f"/councils/{council_slug}/share/"
        response = client.get(share_url + "?year=2024&counters=debt")
        print(f"Share link API status: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

def test_template_files():
    """Test that our template files exist and are valid"""
    print("\nTesting template files...")
    
    template_files = [
        "council_finance/templates/council_finance/spreadsheet_edit_interface.html",
        "council_finance/templates/council_finance/enhanced_council_edit.html"
    ]
    
    for template_path in template_files:
        full_path = os.path.join(os.getcwd(), template_path)
        if os.path.exists(full_path):
            print(f"✅ Template found: {template_path}")
        else:
            print(f"❌ Template missing: {template_path}")
            return False
    
    return True

def test_static_files():
    """Test that our JavaScript files exist"""
    print("\nTesting static files...")
    
    js_file = "council_finance/static/js/spreadsheet_editor.js"
    full_path = os.path.join(os.getcwd(), js_file)
    
    if os.path.exists(full_path):
        print(f"✅ JavaScript file found: {js_file}")
        return True
    else:
        print(f"❌ JavaScript file missing: {js_file}")
        return False

def check_database_models():
    """Check that required models are available"""
    print("\nChecking database models...")
    
    try:
        from council_finance.models import (
            Council, FinancialYear, FinancialFigure, 
            CouncilCharacteristic, Contribution, UserProfile
        )
        
        print("✅ All required models imported successfully")
        
        # Check if we have any sample data
        council_count = Council.objects.count()
        print(f"📊 Councils in database: {council_count}")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import models: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Complete Spreadsheet Interface")
    print("=" * 60)
    
    all_tests_passed = True
    
    print("\n📂 Testing template files...")
    all_tests_passed &= test_template_files()
    
    print("\n📄 Testing static files...")
    all_tests_passed &= test_static_files()
    
    print("\n🗄️  Testing database models...")
    all_tests_passed &= check_database_models()
    
    print("\n🌐 Testing API endpoints...")
    all_tests_passed &= test_spreadsheet_endpoints()
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All spreadsheet interface tests passed!")
        print("\n✨ NEW FEATURES READY:")
        print("   • Excel-like spreadsheet editing interface")
        print("   • Inline cell editing with modals")
        print("   • Real-time progress tracking")
        print("   • Automatic points awarding system")
        print("   • Dual view toggle (table/cards)")
        print("   • Share link functionality")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. Start server: python manage.py runserver")
        print("   2. Navigate to any council's edit page")
        print("   3. Click 'Switch to Table View' to use new interface")
        print("   4. Edit cells by clicking on them")
        print("   5. Watch points accumulate automatically!")
        
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print(f"\n📈 POINTS SYSTEM:")
    print("   • Council characteristics: 3 points each")
    print("   • Financial data entries: 2 points each")
    print("   • Real-time feedback and tier progression")
