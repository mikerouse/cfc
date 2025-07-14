#!/usr/bin/env python
"""
Safe Django ORM cleanup script
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.db import transaction

def safe_cleanup():
    """Safe cleanup using Django ORM"""
    print("🗑️  Starting safe cleanup...")
    
    try:
        # Import models
        from council_finance.models.council import FigureSubmission
        from council_finance.models.contribution import Contribution
        from council_finance.models.data_issue import DataIssue
        from council_finance.models.user_profile import UserProfile
        
        with transaction.atomic():
            # Clear in safe order
            print("   Clearing DataIssue entries...")
            DataIssue.objects.all().delete()
            
            print("   Clearing old Contribution data...")
            Contribution.objects.all().delete()
            
            print("   Clearing FigureSubmission data...")
            FigureSubmission.objects.all().delete()
            
            # Reset user stats
            print("   Resetting user statistics...")
            UserProfile.objects.all().update(
                points=0,
                contribution_count=0,
                first_contribution_date=None,
                last_contribution_date=None
            )
            
            print("✅ Safe cleanup completed!")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        print("   Some data may have been cleared, but the process was interrupted.")

if __name__ == '__main__':
    print("⚠️  WARNING: This will clear legacy data!")
    response = input("   Continue? (type 'YES' to confirm): ")
    
    if response == 'YES':
        safe_cleanup()
        print("\n🎉 Cleanup completed!")
        print("   The application now has a clean state with just council names.")
        print("   You can now test the contribute page with the new V2 architecture.")
    else:
        print("❌ Cleanup cancelled.")
