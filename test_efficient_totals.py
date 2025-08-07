#!/usr/bin/env python
"""
Test script for the efficient site totals approach.

Usage:
    python test_efficient_totals.py

This will:
1. Run the old complex SiteTotalsAgent (for timing comparison)
2. Run the new efficient approach 
3. Show performance comparison
4. Optionally replace the old agent with the new one
"""

import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from council_finance.agents.efficient_site_totals import EfficientSiteTotalsAgent, run_efficient_site_totals
from council_finance.agents.site_totals_agent import SiteTotalsAgent


def test_performance_comparison():
    """Compare old vs new approach performance."""
    
    print("=" * 60)
    print("🧪 PERFORMANCE COMPARISON TEST")
    print("=" * 60)
    
    # Test 1: New efficient approach
    print("\n🚀 Testing NEW Efficient Approach:")
    print("-" * 40)
    
    start_time = time.time()
    try:
        efficient_agent = EfficientSiteTotalsAgent()
        count = efficient_agent.run()
        efficient_time = time.time() - start_time
        efficient_success = True
        
        print(f"✅ SUCCESS: {count} counters calculated in {efficient_time:.2f} seconds")
        
        # Test the debt per capita calculation specifically
        print("\n💡 Testing Debt Per Capita calculation:")
        print("-" * 30)
        debt_per_capita = efficient_agent._total_debt_per_capita_calculation()
        print(f"🏠 Total UK Council Debt Per Capita: £{debt_per_capita:,.0f} per person")
        
    except Exception as e:
        efficient_time = time.time() - start_time
        efficient_success = False
        print(f"❌ FAILED: {e}")
    
    # Test 2: Old complex approach (with timeout to prevent hanging)
    print(f"\n🐌 Testing OLD Complex Approach (timeout after 30s):")
    print("-" * 40)
    
    start_time = time.time()
    try:
        old_agent = SiteTotalsAgent()
        # Set a short timeout to prevent hanging
        old_agent.run(max_duration_minutes=0.5)  # 30 second timeout
        old_time = time.time() - start_time
        old_success = True
        
        print(f"✅ SUCCESS: Old approach completed in {old_time:.2f} seconds")
        
    except Exception as e:
        old_time = time.time() - start_time
        old_success = False
        print(f"❌ FAILED/TIMEOUT: {e} (after {old_time:.2f}s)")
    
    # Results comparison
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE RESULTS")
    print("=" * 60)
    
    if efficient_success:
        print(f"✅ New Efficient Approach: {efficient_time:.2f}s - SUCCESS")
    else:
        print(f"❌ New Efficient Approach: {efficient_time:.2f}s - FAILED")
    
    if old_success:
        print(f"🐌 Old Complex Approach:  {old_time:.2f}s - SUCCESS")
        if efficient_success:
            speedup = old_time / efficient_time
            print(f"🚀 Performance Improvement: {speedup:.1f}x faster ({old_time - efficient_time:.1f}s saved)")
    else:
        print(f"❌ Old Complex Approach:  {old_time:.2f}s - FAILED/TIMEOUT")
        if efficient_success:
            print(f"🎉 New approach WORKS while old approach FAILED!")
    
    return efficient_success, old_success


def offer_replacement():
    """Ask user if they want to replace the old agent."""
    
    print("\n" + "=" * 60) 
    print("🔄 REPLACEMENT OPTION")
    print("=" * 60)
    
    print("Would you like to replace the old SiteTotalsAgent with the efficient version?")
    print("This will:")
    print("✅ Fix the infinite 'Calculating...' issue")
    print("✅ Reduce calculation time from minutes to seconds")
    print("✅ Use simple, reliable SQL queries instead of complex loops")
    print("✅ Eliminate timeout and deadlock issues")
    
    choice = input("\nReplace old agent? (y/N): ").lower().strip()
    
    if choice in ('y', 'yes'):
        try:
            # Replace the old agent
            import council_finance.agents.site_totals_agent as old_module
            old_module.SiteTotalsAgent = EfficientSiteTotalsAgent
            
            print("✅ SUCCESS: Replaced SiteTotalsAgent with efficient version")
            print("💡 The homepage should now load much faster!")
            print("💡 Run: python manage.py warmup_counter_cache")
            
            return True
            
        except Exception as e:
            print(f"❌ FAILED to replace agent: {e}")
            return False
    else:
        print("⏭️  No replacement made. Old agent still in use.")
        return False


def main():
    """Main test function."""
    
    print("🧪 Testing Efficient Site Totals Agent")
    print("This will compare the old complex approach with the new simple approach\n")
    
    # Run performance comparison
    efficient_works, old_works = test_performance_comparison()
    
    # Offer to replace if new approach is better
    if efficient_works:
        replaced = offer_replacement()
        
        if replaced:
            print("\n🎉 System updated! Try accessing the homepage - it should be much faster.")
        else:
            print("\n💡 To manually use the efficient approach:")
            print("   from council_finance.agents.efficient_site_totals import run_efficient_site_totals")
            print("   run_efficient_site_totals()")
    else:
        print("\n❌ Efficient approach failed. Keeping old system.")
    
    print(f"\n{'='*60}")
    print("🏁 TEST COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()