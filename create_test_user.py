#!/usr/bin/env python3
"""
Create test user and council for testing
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.contrib.auth.models import User
from council_finance.models import Council, UserProfile, TrustTier

# Create superuser
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True
    }
)
if created:
    user.set_password('testpass123')
    user.save()
    print(f"Created user: {user.username}")
else:
    print(f"User already exists: {user.username}")

# Create user profile with high trust tier
try:
    tier = TrustTier.objects.get(level=5)
except TrustTier.DoesNotExist:
    tier = TrustTier.objects.create(
        name='God Mode',
        level=5,
        description='Full system access'
    )
    print(f"Created trust tier: {tier.name}")

profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={'tier': tier, 'points': 1000}
)
if created:
    print(f"Created profile for: {user.username}")

# Create Aberdeenshire Council if it doesn't exist
council, created = Council.objects.get_or_create(
    slug='aberdeenshire-council',
    defaults={
        'name': 'Aberdeenshire Council',
        'status': 'active'
    }
)
if created:
    print(f"Created council: {council.name}")
else:
    print(f"Council already exists: {council.name}")

print("Test setup complete!")
print(f"Login with: {user.username} / testpass123")
