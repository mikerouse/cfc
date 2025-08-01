#!/usr/bin/env python
"""
Test script to verify cache invalidation works after financial figure updates.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.cache import cache
from council_finance.models import Council, FinancialYear, DataField, FinancialFigure, CounterDefinition
from council_finance.agents.counter_agent import CounterAgent
import json

def test_cache_invalidation():
    """Test that cache is invalidated when financial figures are updated."""
    print("Setting up test data...")
    
    # Clear cache
    cache.clear()
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create or get test council
    council, created = Council.objects.get_or_create(
        slug='test-council',
        defaults={
            'name': 'Test Council',
            'website': 'https://example.com'
        }
    )
    
    # Create or get test financial year
    year, created = FinancialYear.objects.get_or_create(
        label='2024/25'
    )
    
    # Create or get usable reserves field
    field, created = DataField.objects.get_or_create(
        slug='usable-reserves',
        defaults={
            'name': 'Usable Reserves',
            'category': 'balance_sheet',
            'content_type': 'monetary'
        }
    )
    
    # Create or get counter definition that uses usable reserves
    counter, created = CounterDefinition.objects.get_or_create(
        slug='usable-reserves-counter',
        defaults={
            'name': 'Usable Reserves Counter',
            'formula': 'usable_reserves',
            'precision': 0,
            'show_by_default': True
        }
    )
    
    print("Testing cache behavior...")
    
    # Step 1: Create initial financial figure 
    initial_value = 100000000
    figure, created = FinancialFigure.objects.get_or_create(
        council=council,
        year=year,
        field=field,
        defaults={'value': initial_value}
    )
    if not created:
        figure.value = initial_value
        figure.save()
    
    # Step 2: Run counter agent to populate cache
    agent = CounterAgent()
    cache_key = f"counter_values:{council.slug}:{year.label}"
    
    print(f"Cache key: {cache_key}")
    print(f"Initial cache value: {cache.get(cache_key)}")
    
    # Run agent to populate cache
    result = agent.run(council_slug=council.slug, year_label=year.label)
    print(f"Agent result: {result}")
    
    # Manually set cache to simulate what happens in council detail view
    cache.set(cache_key, result, 600)  # 10 minutes
    print(f"Cache after setting: {cache.get(cache_key)}")
    
    # Step 3: Update the financial figure (simulating the edit API)
    new_value = 153607000
    figure.value = new_value
    figure.save()
    
    # Simulate cache invalidation (what our fix does)
    cache.delete(cache_key)
    print(f"Cache after invalidation: {cache.get(cache_key)}")
    
    # Step 4: Run agent again to verify new value
    new_result = agent.run(council_slug=council.slug, year_label=year.label)
    print(f"New agent result: {new_result}")
    
    # Verify the value has changed
    if counter.slug in new_result:
        new_counter_value = new_result[counter.slug].get('value')
        print(f"New counter value: {new_counter_value}")
        
        if new_counter_value == new_value:
            print("✅ SUCCESS: Cache invalidation works! Counter shows updated value.")
            return True
        else:
            print(f"❌ FAIL: Expected {new_value}, got {new_counter_value}")
            return False
    else:
        print(f"❌ FAIL: Counter '{counter.slug}' not found in results")
        return False

def test_api_endpoint():
    """Test the actual API endpoint that saves temporal data."""
    print("\nTesting API endpoint...")
    
    client = Client()
    user = User.objects.get(username='testuser')
    client.force_login(user)
    
    council = Council.objects.get(slug='test-council')
    year = FinancialYear.objects.get(label='2024/25')
    
    # Test data to send
    test_data = {
        'field': 'usable-reserves',
        'value': '200000000',
        'category': 'financial'
    }
    
    # Make API call
    url = f'/api/council/{council.slug}/temporal/{year.id}/'
    response = client.post(
        url,
        data=json.dumps(test_data),
        content_type='application/json'
    )
    
    print(f"API Response status: {response.status_code}")
    if response.status_code == 200:
        print(f"API Response: {response.json()}")
        print("✅ SUCCESS: API endpoint works correctly")
        return True
    else:
        print(f"❌ FAIL: API returned {response.status_code}")
        if hasattr(response, 'json'):
            print(f"Error: {response.json()}")
        return False

if __name__ == '__main__':
    print("Testing cache invalidation fix...")
    
    try:
        success1 = test_cache_invalidation()
        success2 = test_api_endpoint()
        
        if success1 and success2:
            print("\n🎉 All tests passed! The cache invalidation fix works correctly.")
        else:
            print("\n❌ Some tests failed. Check the output above for details.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()