#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import PendingProfileChange

def cleanup_duplicates():
    """Remove duplicate email change requests, keeping the most recent"""
    
    print("=== CLEANING UP DUPLICATES ===")
    
    # Group by user and field
    users_with_changes = {}
    all_changes = PendingProfileChange.objects.filter(status='pending').order_by('-created_at')
    
    for change in all_changes:
        key = f"{change.user.id}_{change.field}_{change.new_value}"
        if key not in users_with_changes:
            users_with_changes[key] = []
        users_with_changes[key].append(change)
    
    for key, changes in users_with_changes.items():
        if len(changes) > 1:
            print(f"Found {len(changes)} duplicate changes for {key}")
            # Keep the most recent one
            to_keep = changes[0]
            to_delete = changes[1:]
            
            print(f"Keeping: ID {to_keep.id} (created {to_keep.created_at})")
            for change in to_delete:
                print(f"Deleting: ID {change.id} (created {change.created_at})")
                change.delete()
            print()
    
    print("=== FINAL STATE ===")
    remaining = PendingProfileChange.objects.filter(status='pending')
    for change in remaining:
        print(f"ID {change.id}: {change.user.username} - {change.field} -> {change.new_value}")
        print(f"  Token: {change.token}")
        print(f"  Valid until: {change.expires_at}")

if __name__ == '__main__':
    cleanup_duplicates()
