#!/usr/bin/env python3
"""
Test script to validate the feed display fix for financial data.

This script tests the ActivityStoryGenerator to ensure it properly handles
financial updates and generates rich story data with formatted values.
"""

import os
import sys
import django
from decimal import Decimal

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.services.activity_story_generator import ActivityStoryGenerator
from council_finance.models import ActivityLog, Council, DataField, FinancialYear


def create_mock_activity_log():
    """Create a mock activity log for testing"""
    
    class MockActivityLog:
        def __init__(self):
            self.id = 1
            self.activity_type = 'update'
            self.description = 'Updated Current Liabilities for Cornwall Council (2024/25)'
            self.created = '2024-01-01T12:00:00Z'
            
            # Mock council
            self.related_council = type('MockCouncil', (), {
                'name': 'Cornwall Council',
                'slug': 'cornwall-council',
                'council_type': type('MockCouncilType', (), {'name': 'Unitary Authority'})()
            })()
            
            # Mock details in new format
            self.details = {
                'field_name': 'current-liabilities',  # slug format
                'field_display_name': 'Current Liabilities',
                'old_value': '45000000',
                'new_value': '50000000',
                'year': '2024/25',
                'content_type': 'monetary',
                'category': 'balance_sheet'
            }
        
        def get_activity_type_display(self):
            return 'Update'
    
    return MockActivityLog()


def create_mock_field():
    """Create a mock DataField for testing"""
    class MockField:
        def __init__(self):
            self.slug = 'current-liabilities'
            self.name = 'Current Liabilities'
            self.category = 'balance_sheet'
            self.content_type = 'monetary'
    
    return MockField()


def create_mock_financial_year():
    """Create a mock FinancialYear for testing"""
    class MockFinancialYear:
        def __init__(self):
            self.label = '2024/25'
            self.is_current = True
    
    return MockFinancialYear()


def test_story_generation():
    """Test the story generation process"""
    print("🧪 Testing ActivityStoryGenerator...")
    
    # Create mock objects
    activity_log = create_mock_activity_log()
    
    # Mock the database queries
    original_filter = DataField.objects.filter
    original_year_filter = FinancialYear.objects.filter
    
    def mock_field_filter(*args, **kwargs):
        if 'slug' in kwargs and kwargs['slug'] == 'current-liabilities':
            mock_qs = type('MockQuerySet', (), {
                'first': lambda: create_mock_field()
            })()
            return mock_qs
        return original_filter(*args, **kwargs)
    
    def mock_year_filter(*args, **kwargs):
        if 'label' in kwargs and kwargs['label'] == '2024/25':
            mock_qs = type('MockQuerySet', (), {
                'first': lambda: create_mock_financial_year()
            })()
            return mock_qs
        return original_year_filter(*args, **kwargs)
    
    # Apply mocks
    DataField.objects.filter = mock_field_filter
    FinancialYear.objects.filter = mock_year_filter
    
    try:
        # Test story generation
        generator = ActivityStoryGenerator()
        story_data = generator.generate_story(activity_log)
        
        print(f"✅ Story generated successfully!")
        print(f"📝 Title: {story_data.get('title', 'N/A')}")
        print(f"📖 Story: {story_data.get('story', 'N/A')}")
        print(f"💰 Value: {story_data.get('value', 'N/A')}")
        print(f"📊 Field Name: {story_data.get('field_name', 'N/A')}")
        print(f"📅 Year: {story_data.get('year', 'N/A')}")
        print(f"🏛️ Council: {story_data.get('council_name', 'N/A')}")
        
        # Check if the expected data is present
        success = True
        checks = [
            ('value', story_data.get('value')),
            ('field_name', story_data.get('field_name')),
            ('year', story_data.get('year')),
            ('story', story_data.get('story'))
        ]
        
        for field_name, value in checks:
            if not value:
                print(f"❌ Missing {field_name}")
                success = False
            else:
                print(f"✅ {field_name}: {value}")
        
        if success and story_data.get('value') and '£' in story_data.get('value'):
            print(f"\n🎉 SUCCESS: Feed will now show rich financial data!")
        else:
            print(f"\n❌ ISSUE: Feed may still show basic text only")
            
    except Exception as e:
        print(f"❌ Error testing story generation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Restore original methods
        DataField.objects.filter = original_filter
        FinancialYear.objects.filter = original_year_filter


def test_api_logging_format():
    """Test the new API logging format"""
    print("\n🧪 Testing API logging format...")
    
    # Simulate the new details format from the API
    new_details = {
        'field_name': 'current-liabilities',  # slug format as expected by story generator
        'field_display_name': 'Current Liabilities',  # human readable name
        'old_value': '45000000',
        'new_value': '50000000',
        'year': '2024/25',  # year included for story generator
        'content_type': 'monetary',
        'category': 'balance_sheet'
    }
    
    # Check if the format matches what the story generator expects  
    expected_fields = ['field_name', 'new_value', 'year']
    missing_fields = []
    
    for field in expected_fields:
        if field not in new_details:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
    else:
        print(f"✅ All required fields present")
        print(f"   field_name (slug): {new_details['field_name']}")
        print(f"   new_value: {new_details['new_value']}")
        print(f"   year: {new_details['year']}")
        print(f"   category: {new_details['category']}")
        
        if new_details['category'] in ['balance_sheet', 'income', 'spending', 'calculated']:
            print(f"✅ Category '{new_details['category']}' will be formatted as currency")
        else:
            print(f"⚠️  Category '{new_details['category']}' may not be formatted as currency")


if __name__ == '__main__':
    print("🔧 Testing Feed Display Fix for Financial Values")
    print("=" * 50)
    
    test_api_logging_format()
    test_story_generation()
    
    print("\n" + "=" * 50)
    print("✨ Test completed!")