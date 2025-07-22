#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import PendingProfileChange
from django.utils import timezone
import datetime

def fix_expired_records():
    """Fix the existing expired records by extending their expiration time"""
    
    print("=== FIXING EXPIRED RECORDS ===")
    
    # Get all pending changes
    all_changes = PendingProfileChange.objects.all()
    print(f"Total pending changes: {all_changes.count()}")
    
    for change in all_changes:
        if change.is_expired and change.status == 'pending':
            print(f"Fixing expired record ID {change.id} for user {change.user.username}")
            print(f"  Old expiration: {change.expires_at}")
            
            # Extend expiration by 24 hours from now
            change.expires_at = timezone.now() + datetime.timedelta(hours=24)
            change.save()
            
            print(f"  New expiration: {change.expires_at}")
            print(f"  Is now valid: {change.is_valid}")
            print()
    
    print("=== VERIFICATION ===")
    valid_changes = PendingProfileChange.objects.filter(status='pending')
    for change in valid_changes:
        print(f"ID {change.id}: {change.user.username} - {change.field} -> {change.new_value}")
        print(f"  Expires: {change.expires_at}")
        print(f"  Valid: {change.is_valid}")
        print(f"  Token: {change.token}")
        print()

if __name__ == '__main__':
    fix_expired_records()
