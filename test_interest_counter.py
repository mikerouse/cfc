#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import CounterDefinition, Council
from council_finance.services.factoid_engine import FactoidEngine

def test_interest_counter():
    print("=== TESTING INTEREST PAYMENTS COUNTER ===")
    
    try:
        # Get the correct counter and council  
        counter = CounterDefinition.objects.get(slug='interest-payments')
        council = Council.objects.get(slug='worcestershire')
        
        print(f"Counter: {counter.name} ({counter.slug})")
        print(f"Council: {council.name} ({council.slug})")
        print()
        
        # Test the factoid engine for this counter
        from council_finance.models import FinancialYear
        year = FinancialYear.objects.get(label='2024/25')
        
        engine = FactoidEngine()
        factoids = engine.get_factoids_for_counter(counter, council, year)
        print(f"Found {len(factoids)} factoids for this counter")
        for i, factoid in enumerate(factoids):
            print(f"  {i+1}. {factoid.rendered_text}")
        print()
        
        # Test the API URL that frontend will call
        frontend_year = '2024/25'.replace('/', '-')  # Convert to URL safe
        print(f"Frontend will call: /api/factoids/counter/{counter.slug}/{council.slug}/{frontend_year}/")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_interest_counter()
