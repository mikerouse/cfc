#!/usr/bin/env python3
"""
Debug script to check calculated fields availability
"""
import os
import sys
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council, FinancialYear, CounterDefinition
from council_finance.calculators import get_data_context_for_council
from council_finance.agents.counter_agent import CounterAgent

def debug_counter_data():
    """Debug counter data sources"""
    
    print("🔍 Debugging Counter Data Sources")
    print("=" * 50)
    
    # Get test data
    council = Council.objects.get(slug='worcestershire')
    year = FinancialYear.objects.get(label='2024/25')
    counter = CounterDefinition.objects.get(slug='gov-funding-per-head-no-strings')
    
    print(f"Council: {council.name}")
    print(f"Year: {year.label}")
    print(f"Counter: {counter.name}")
    print(f"Formula: {counter.formula}")
    print()
    
    # Check data context (used by preview)
    print("📊 Data Context (Preview Tool Uses This):")
    context = get_data_context_for_council(council, year)
    
    print(f"Available calculated fields: {len(context.get('calculated', {}))}")
    for field, value in context.get('calculated', {}).items():
        print(f"  {field}: {value}")
    
    target_field = 'non_ring_fenced_government_grant_income_per_capita'
    print(f"\nLooking for: {target_field}")
    if target_field in context.get('calculated', {}):
        print(f"✅ Found: {context['calculated'][target_field]}")
    else:
        print("❌ Not found in calculated fields")
    
    print()
    
    # Check CounterAgent (used by council detail)
    print("🤖 CounterAgent (Council Detail Uses This):")
    agent = CounterAgent()
    try:
        results = agent.run(council_slug=council.slug, year_label=year.label)
        counter_result = results.get(counter.slug, {})
        print(f"Counter result: {counter_result}")
        
        if counter_result.get('value') is not None:
            print(f"✅ Counter has value: {counter_result['value']}")
        else:
            print(f"❌ Counter shows: {counter_result.get('formatted', 'No result')}")
            
    except Exception as e:
        print(f"❌ CounterAgent error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_counter_data()
