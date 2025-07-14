#!/usr/bin/env python
"""
Legacy System Cleanup Script

This script removes old legacy systems and data, keeping only:
- Council names and basic info
- New V2 data architecture (CouncilCharacteristic, FinancialFigure, ContributionV2)
- Essential models for the new system

DANGER: This will delete most existing data! Only run if you're sure.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.db import transaction

def cleanup_legacy_data():
    """Remove legacy data but keep council names"""
    print("🗑️  Starting legacy data cleanup...")
    
    # Import models as needed to avoid circular imports
    from council_finance.models.council import Council, FigureSubmission
    from council_finance.models.contribution import Contribution  
    from council_finance.models.data_issue import DataIssue
    from council_finance.models.activity_log import ActivityLogEntry
    from council_finance.models.user_profile import UserProfile
    
    with transaction.atomic():
        # 1. Clear legacy FigureSubmission data
        print("   Removing FigureSubmission data...")
        FigureSubmission.objects.all().delete()
        
        # 2. Clear old Contribution data (keep ContributionV2)
        print("   Removing old Contribution data...")
        Contribution.objects.all().delete()
        
        # 3. Clear DataIssue entries
        print("   Removing DataIssue entries...")
        DataIssue.objects.all().delete()
        
        # 4. Clear ActivityLog entries
        print("   Removing ActivityLog entries...")
        ActivityLogEntry.objects.all().delete()
        
        # 5. Clear UserProfile points/stats but keep basic profiles
        print("   Resetting UserProfile stats...")
        UserProfile.objects.all().update(
            points=0,
            contribution_count=0,
            first_contribution_date=None,
            last_contribution_date=None
        )
        
        # 6. Keep only essential council data
        print("   Cleaning council data...")
        Council.objects.filter(status__in=['closed', 'merged', 'renamed']).delete()
        Council.objects.update(latest_population=None)
        
        print("✅ Legacy data cleanup completed!")

def remove_legacy_files():
    """Remove legacy files that are no longer needed"""
    legacy_files = [
        'council_finance/views_v2.py',
        'council_finance/urls_v2.py',
        'test_god_mode_enhanced.py',
        'test_enhanced_merge.py', 
        'test_enhanced_features.py',
        'test_contribute_fix.py',
        'test_approval.py',
        'test_activity_log.py'
    ]
    
    print("🗑️  Removing legacy files...")
    base_path = '/'.join(__file__.split('/')[:-1])
    
    for file_path in legacy_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"   Removed: {file_path}")
        else:
            print(f"   Not found: {file_path}")
    
    print("✅ Legacy files cleanup completed!")

def create_migration_to_remove_legacy_models():
    """Create a Django migration to remove legacy model fields and tables"""
    migration_content = '''
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('council_finance', '0049_contributionv2_councilcharacteristic_and_more'),
    ]

    operations = [
        # Remove legacy model references but keep essential structure
        migrations.RunSQL(
            """
            -- Clean up legacy data but keep essential tables
            DELETE FROM council_finance_figuresubmission;
            DELETE FROM council_finance_contribution;
            DELETE FROM council_finance_dataissue;
            DELETE FROM council_finance_activitylogentry;
            
            -- Reset user stats
            UPDATE council_finance_userprofile SET 
                points = 0, 
                contribution_count = 0, 
                first_contribution_date = NULL, 
                last_contribution_date = NULL;
            
            -- Clean council data
            UPDATE council_finance_council SET latest_population = NULL;
            DELETE FROM council_finance_council WHERE status IN ('closed', 'merged', 'renamed');
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
'''
    
    migration_file = 'council_finance/migrations/0050_cleanup_legacy_systems.py'
    with open(migration_file, 'w') as f:
        f.write(migration_content)
    
    print(f"✅ Created migration: {migration_file}")

if __name__ == '__main__':
    print("⚠️  WARNING: This will delete most existing data!")
    print("   Only council names and new V2 architecture will remain.")
    response = input("   Continue? (type 'YES' to confirm): ")
    
    if response == 'YES':
        cleanup_legacy_data()
        remove_legacy_files() 
        create_migration_to_remove_legacy_models()
        print("\n🎉 Legacy cleanup completed!")
        print("   Run: python manage.py migrate")
        print("   Then restart the server.")
    else:
        print("❌ Cleanup cancelled.")
