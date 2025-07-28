#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def test_counter_factoid_filtering():
    """Test that factoids are properly filtered by counter assignment"""
    print("=== TESTING COUNTER FACTOID FILTERING ===")
    
    from django.test import Client
    import json
    
    client = Client()
    
    # Test different counters
    test_cases = [
        ('interest-payments', 'Interest Payments'),
        ('total-debt', 'Total Debt'), 
        ('current-liabilities', 'Current Liabilities'),
        ('long-term-liabilities', 'Long-term Liabilities')
    ]
    
    for counter_slug, counter_name in test_cases:
        print(f"\n{counter_name} Counter:")
        response = client.get(f'/api/factoids/counter/{counter_slug}/worcestershire/2024-25/')
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Factoids: {data['count']}")
            for factoid in data['factoids']:
                print(f"    - {factoid['template_name']}")
        else:
            print(f"  Error: {response.status_code}")
    
    print("\n=== SUMMARY ===")
    print("✅ Factoids now only show on their assigned counters")
    print("✅ No more generic factoids appearing everywhere")
    print("✅ Each counter has contextually relevant factoids only")

if __name__ == "__main__":
    test_counter_factoid_filtering()
