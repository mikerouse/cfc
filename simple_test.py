#!/usr/bin/env python
"""
Simple verification that the trust tier fixes are working
"""

# Test the imports and basic functionality
def test_basic_functionality():
    try:
        print("Testing basic Django setup...")
        
        # Test that we can import Django
        import django
        print("✅ Django imports successfully")
        
        # Test that we can access the models
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
        django.setup()
        
        from council_finance.models import UserProfile, TrustTier, Council
        print("✅ Models import successfully")
        
        # Test that we can query without AttributeError
        profiles = UserProfile.objects.all()
        print(f"✅ UserProfile query works: {profiles.count()} profiles")
        
        # Test tier access
        if profiles.exists():
            profile = profiles.first()
            tier_level = profile.tier.level
            print(f"✅ Tier level access works: {tier_level}")
        
        # Test tier-based filtering
        tier_2_plus = UserProfile.objects.filter(tier__level__gte=2)
        print(f"✅ Tier filtering works: {tier_2_plus.count()} users with tier >= 2")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_basic_functionality()
