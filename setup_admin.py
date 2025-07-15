#!/usr/bin/env python
"""Quick script to ensure admin user has proper profile setup."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.contrib.auth.models import User
from council_finance.models import UserProfile, TrustTier

# Get admin user
try:
    admin_user = User.objects.get(username='admin')
    print(f"Found admin user: {admin_user.username}")
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=admin_user)
    print(f"Profile {'created' if created else 'found'}")
    
    # Ensure profile has a tier
    if not profile.tier:
        tier = TrustTier.objects.first()
        if tier:
            profile.tier = tier
            profile.save()
            print(f"Assigned tier: {tier}")
        else:
            print("No tiers available")
    else:
        print(f"Profile already has tier: {profile.tier}")
        
    # Check superuser status
    print(f"Is superuser: {admin_user.is_superuser}")
        
except User.DoesNotExist:
    print("Admin user not found")
except Exception as e:
    print(f"Error: {e}")
