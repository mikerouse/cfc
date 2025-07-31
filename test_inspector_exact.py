#!/usr/bin/env python
"""
Test the exact same data gathering that the inspector uses.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import CouncilDataGatherer
from django.core.cache import cache


def test_exact_inspector_flow():
    print("Testing Exact Inspector Data Flow")
    print("=" * 60)
    
    # Clear all caches
    cache.clear()
    print("[OK] All caches cleared")
    
    # Get council exactly as inspector does
    from django.shortcuts import get_object_or_404
    council = get_object_or_404(Council, slug='worcestershire')
    print(f"Council: {council.name}")
    
    # Call gatherer exactly as inspector does
    gatherer = CouncilDataGatherer()
    council_data = gatherer.gather_council_data(council)
    
    print(f"\nCouncil data keys: {list(council_data.keys())}")
    
    # Check financial time series specifically
    fts = council_data.get('financial_time_series', {})
    print(f"Financial time series type: {type(fts)}")
    print(f"Financial time series length: {len(fts)}")
    
    if fts:
        print(f"First few fields: {list(fts.keys())[:3]}")
        first_field = list(fts.values())[0]
        print(f"First field structure: {first_field}")
    else:
        print("[ERROR] No financial time series data found!")
        
        # Let's debug why
        print("\nDebugging financial data gathering...")
        
        # Test the method directly
        raw_fts = gatherer._get_financial_time_series(council)
        print(f"Raw _get_financial_time_series result length: {len(raw_fts)}")
        
        if raw_fts:
            print(f"Raw first field: {list(raw_fts.keys())[0]}")
            print(f"Raw first value: {raw_fts[list(raw_fts.keys())[0]]}")
        
        # Check database directly
        from council_finance.models import FinancialFigure
        ff_count = FinancialFigure.objects.filter(council=council).count()
        print(f"FinancialFigure records in DB: {ff_count}")
        
        if ff_count > 0:
            ff = FinancialFigure.objects.filter(council=council).first()
            print(f"First FF: {ff.field.slug}, value={ff.value}, text_value={ff.text_value}")
    
    # Test cache behavior
    cache_key = f"ai_council_data:{council.slug}"
    cached_data = cache.get(cache_key)
    if cached_data:
        print(f"\nCached data found, keys: {list(cached_data.keys())}")
        cached_fts = cached_data.get('financial_time_series', {})
        print(f"Cached FTS length: {len(cached_fts)}")
    else:
        print("\nNo cached data found")


if __name__ == '__main__':
    test_exact_inspector_flow()