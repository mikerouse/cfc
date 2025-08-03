#!/usr/bin/env python3
"""
Test script to debug Worcestershire AI factoid caching issue.

This script will:
1. Check current cache status for Worcestershire
2. Test AI factoid generation
3. Test cache retrieval
4. Provide detailed debugging output
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.core.cache import cache
from django.utils import timezone
from council_finance.models import Council
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer

def check_cache_status(council_slug):
    """Check current cache status for a council."""
    print(f"\nCACHE INSPECTION: {council_slug}")
    print("=" * 50)
    
    # Check primary cache
    cache_key = f"ai_factoids:{council_slug}"
    cached_data = cache.get(cache_key)
    print(f"Primary cache key: {cache_key}")
    print(f"Primary cache status: {'CACHED' if cached_data else 'NOT CACHED'}")
    
    if cached_data:
        print(f"Primary cache data type: {type(cached_data)}")
        if isinstance(cached_data, dict):
            print(f"Primary factoid count: {cached_data.get('factoid_count', 'unknown')}")
            print(f"Primary generated at: {cached_data.get('generated_at', 'unknown')}")
            print(f"Primary AI model: {cached_data.get('ai_model', 'unknown')}")
    
    # Check stale cache
    cache_key_stale = f"ai_factoids_stale:{council_slug}"
    stale_cached_data = cache.get(cache_key_stale)
    print(f"\nStale cache key: {cache_key_stale}")
    print(f"Stale cache status: {'CACHED' if stale_cached_data else 'NOT CACHED'}")
    
    if stale_cached_data:
        print(f"Stale cache data type: {type(stale_cached_data)}")
        if isinstance(stale_cached_data, dict):
            print(f"Stale factoid count: {stale_cached_data.get('factoid_count', 'unknown')}")
            print(f"Stale generated at: {stale_cached_data.get('generated_at', 'unknown')}")
            print(f"Stale AI model: {stale_cached_data.get('ai_model', 'unknown')}")
    
    # Check data cache
    data_cache_key = f"ai_council_data:{council_slug}"
    data_cached = cache.get(data_cache_key)
    print(f"\nData cache key: {data_cache_key}")
    print(f"Data cache status: {'CACHED' if data_cached else 'NOT CACHED'}")
    
    return {
        'primary_cached': bool(cached_data),
        'stale_cached': bool(stale_cached_data),
        'data_cached': bool(data_cached),
        'primary_data': cached_data,
        'stale_data': stale_cached_data
    }

def test_ai_generation(council_slug):
    """Test AI factoid generation for a council."""
    print(f"\nAI GENERATION TEST: {council_slug}")
    print("=" * 50)
    
    try:
        council = Council.objects.get(slug=council_slug)
        print(f"Council found: {council.name}")
        
        # Test data gathering
        print("\nTesting data gathering...")
        gatherer = CouncilDataGatherer()
        council_data = gatherer.gather_council_data(council)
        
        financial_data = council_data.get('financial_time_series', {})
        print(f"Financial fields gathered: {len(financial_data)}")
        
        if financial_data:
            print("Sample financial fields:")
            for i, (field, data) in enumerate(list(financial_data.items())[:3]):
                years = data.get('years', {}) if isinstance(data, dict) else {}
                print(f"  {i+1}. {field}: {len(years)} years of data")
        
        # Test AI generation
        print("\nTesting AI generation...")
        generator = AIFactoidGenerator()
        print(f"AI Model: {generator.model}")
        print(f"OpenAI Client Available: {generator.client is not None}")
        
        if generator.client:
            start_time = timezone.now()
            factoids = generator.generate_insights(
                council_data=council_data,
                limit=3,
                style='news_ticker'
            )
            end_time = timezone.now()
            
            processing_time = (end_time - start_time).total_seconds()
            print(f"AI generation successful!")
            print(f"Generated {len(factoids)} factoids in {processing_time:.2f} seconds")
            
            for i, factoid in enumerate(factoids):
                print(f"  {i+1}. {factoid.get('text', 'No text')}")
                print(f"      Type: {factoid.get('insight_type', 'unknown')}")
                print(f"      Confidence: {factoid.get('confidence', 'unknown')}")
            
            return factoids
        else:
            print("OpenAI client not available")
            return None
            
    except Exception as e:
        print(f"AI generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function."""
    council_slug = "worcestershire"
    
    print("WORCESTERSHIRE AI FACTOID DEBUGGING")
    print("=" * 60)
    print(f"Testing council: {council_slug}")
    print(f"Test time: {timezone.now()}")
    
    # Step 1: Check current cache status
    cache_status = check_cache_status(council_slug)
    
    # Step 2: Test AI generation if no cache
    if not cache_status['primary_cached']:
        print(f"\nNo primary cache found, testing fresh AI generation...")
        factoids = test_ai_generation(council_slug)
        
        if factoids:
            print(f"\nFresh generation successful - would typically be cached now")
        else:
            print(f"\nFresh generation failed - this explains the caching issue")
    else:
        print(f"\nPrimary cache exists - should be serving cached results")
        
        # Show cached factoids
        cached_factoids = cache_status['primary_data'].get('factoids', [])
        print(f"Cached factoids ({len(cached_factoids)}):")
        for i, factoid in enumerate(cached_factoids[:3]):
            print(f"  {i+1}. {factoid.get('text', 'No text')}")
    
    # Step 3: Final diagnosis
    print(f"\nDIAGNOSIS")
    print("=" * 30)
    
    if cache_status['primary_cached']:
        print("Cache is working - Worcestershire should show cached AI insights")
        print("If user sees 'being generated' message, check frontend API calls")
    elif cache_status['stale_cached']:
        print("Only stale cache available - may indicate rate limiting or recent failures")
        print("Check API rate limits and recent error logs")
    else:
        print("No cache available - this explains the 'being generated' message")
        print("Possible causes:")
        print("   - OpenAI API key issues")
        print("   - Network connectivity problems")
        print("   - Rate limiting")
        print("   - Recent cache clearing")

if __name__ == "__main__":
    main()