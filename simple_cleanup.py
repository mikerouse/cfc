#!/usr/bin/env python
"""
Simple database cleanup script - removes legacy data but keeps council names
Run this with: python simple_cleanup.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.db import connection

def cleanup_database():
    """Clean database keeping only essential data"""
    print("🗑️  Cleaning up database...")
    
    with connection.cursor() as cursor:
        # 1. Clear legacy data tables but keep structure
        print("   Clearing FigureSubmission data...")
        cursor.execute("DELETE FROM council_finance_figuresubmission;")
        
        print("   Clearing old Contribution data...")
        cursor.execute("DELETE FROM council_finance_contribution;")
        
        print("   Clearing DataIssue entries...")
        cursor.execute("DELETE FROM council_finance_dataissue;")
        
        print("   Clearing ActivityLog entries...")
        cursor.execute("DELETE FROM council_finance_activitylogentry;")
        
        # 2. Reset user stats but keep accounts
        print("   Resetting user statistics...")
        cursor.execute("""
            UPDATE council_finance_userprofile 
            SET points = 0, 
                contribution_count = 0, 
                first_contribution_date = NULL, 
                last_contribution_date = NULL;
        """)
        
        # 3. Clean council data - keep names but remove stats
        print("   Cleaning council data...")
        cursor.execute("UPDATE council_finance_council SET latest_population = NULL;")
        cursor.execute("DELETE FROM council_finance_council WHERE status IN ('closed', 'merged', 'renamed');")
        
        # 4. Clear any remaining legacy references
        print("   Clearing remaining legacy data...")
        try:
            cursor.execute("DELETE FROM council_finance_debtupdatehistory;")
        except:
            pass  # Table might not exist
        
        try:
            cursor.execute("DELETE FROM council_finance_datachangelog;")
        except:
            pass  # Table might not exist
    
    print("✅ Database cleanup completed!")
    print("   Council names and basic structure preserved.")
    print("   New V2 data models (CouncilCharacteristic, FinancialFigure, ContributionV2) ready for use.")

if __name__ == '__main__':
    print("⚠️  WARNING: This will clear legacy data!")
    print("   Council names will be preserved, but most other data will be removed.")
    response = input("   Continue? (type 'YES' to confirm): ")
    
    if response == 'YES':
        cleanup_database()
        print("\n🎉 Cleanup completed! The application is now using clean V2 architecture.")
    else:
        print("❌ Cleanup cancelled.")
