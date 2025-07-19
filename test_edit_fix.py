#!/usr/bin/env python
"""
Test script to verify the edit tab fix.
This script tests both authenticated and non-authenticated access to the edit tab.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council, UserProfile, TrustTier


def test_edit_tab_functionality():
    """Test the edit tab functionality for both logged in and logged out users."""
    
    client = Client()
    
    # Get a test council
    council = Council.objects.first()
    if not council:
        print("❌ No councils found in database")
        return False
    
    print(f"🧪 Testing edit functionality for council: {council.name}")
    
    # Test 1: Non-authenticated user accessing edit tab
    print("\n1️⃣ Testing non-authenticated user access...")
    
    edit_url = reverse('council_detail', kwargs={'slug': council.slug}) + '?tab=edit'
    response = client.get(edit_url)
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Should contain login prompt, not recursive content
        if 'Login Required to Edit' in content:
            print("✅ Non-authenticated user sees login prompt")
        else:
            print("❌ Non-authenticated user doesn't see expected login prompt")
            return False
            
        # Should NOT contain the edit form multiple times
        edit_form_count = content.count('Edit ' + council.name)
        if edit_form_count <= 2:  # Header + edit section = max 2
            print("✅ No recursive content detected")
        else:
            print(f"❌ Recursive content detected: {edit_form_count} instances of edit form")
            return False
    else:
        print(f"❌ Unexpected status code: {response.status_code}")
        return False
    
    # Test 2: Authenticated user with appropriate tier
    print("\n2️⃣ Testing authenticated user with Tier 2 access...")
    
    # Get or create test user
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Ensure user has Tier 2 access
    try:
        tier2 = TrustTier.objects.get(level=2)
        user.profile.tier = tier2
        user.profile.save()
    except TrustTier.DoesNotExist:
        print("❌ Tier 2 not found in database")
        return False
    
    # Login the user
    login_success = client.login(username='testuser', password='testpass123')
    if not login_success:
        print("❌ Failed to login test user")
        return False
    
    # Access edit tab as authenticated user
    response = client.get(edit_url)
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Should contain edit interface
        if 'Edit ' + council.name in content and 'Quick Actions' in content:
            print("✅ Authenticated user sees edit interface")
        else:
            print("❌ Authenticated user doesn't see expected edit interface")
            return False
            
        # Should NOT contain login prompt
        if 'Login Required to Edit' not in content:
            print("✅ No login prompt shown to authenticated user")
        else:
            print("❌ Login prompt still shown to authenticated user")
            return False
    else:
        print(f"❌ Unexpected status code for authenticated user: {response.status_code}")
        return False
    
    print("\n🎉 All tests passed! Edit tab functionality is working correctly.")
    return True


if __name__ == '__main__':
    print("🔧 Testing Council Edit Tab Fix")
    print("=" * 50)
    
    success = test_edit_tab_functionality()
    
    if success:
        print("\n✅ CONCLUSION: Edit tab fix successful!")
        print("   - Non-authenticated users see login prompt")
        print("   - Authenticated users see edit interface")
        print("   - No recursive content issues detected")
        sys.exit(0)
    else:
        print("\n❌ CONCLUSION: Edit tab fix needs more work")
        sys.exit(1)
