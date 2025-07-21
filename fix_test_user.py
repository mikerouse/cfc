#!/usr/bin/env python3
"""
Fix test user password
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.contrib.auth.models import User

# Get or create user
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

# Set password
user.set_password('testpass123')
user.save()
print(f"Updated password for user: {user.username}")

# Test authentication
from django.contrib.auth import authenticate
auth_user = authenticate(username='testuser', password='testpass123')
if auth_user:
    print("Authentication test successful!")
else:
    print("Authentication test failed!")
