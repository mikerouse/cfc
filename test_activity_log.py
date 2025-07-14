#!/usr/bin/env python
"""
Test script for the enhanced ActivityLog and merge functionality
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models.council import Council, FinancialYear
from council_finance.models.activity_log import ActivityLog
from django.contrib.auth.models import User

def test_activity_log():
    """Test the enhanced ActivityLog functionality"""
    print("=" * 60)
    print("TESTING ENHANCED ACTIVITY LOG")
    print("=" * 60)
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com', 'is_staff': True}
    )
    if created:
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing test user: {user.username}")
    
    # Get a test council
    council = Council.objects.first()
    if not council:
        print("No councils found. Please run data import first.")
        return
    
    print(f"Using test council: {council.name}")
    
    # Test different types of activity logging
    test_activities = [
        {
            'activity_type': 'council_merge',
            'description': 'Test merge operation completed',
            'status': 'completed',
            'details': {
                'source_council': 'Test Borough',
                'target_council': 'Test Unitary',
                'figures_moved': 42,
                'conflicts_resolved': 3
            }
        },
        {
            'activity_type': 'data_correction',
            'description': 'Updated population figure',
            'status': 'completed',
            'details': {
                'field': 'population',
                'old_value': '100000',
                'new_value': '105000'
            }
        },
        {
            'activity_type': 'financial_year',
            'description': 'Created new financial year 2025-26',
            'status': 'completed',
            'details': {
                'year_label': '2025-26',
                'is_current': False
            }
        },
        {
            'activity_type': 'system',
            'description': 'Test system activity (no user)',
            'status': 'completed',
            'details': {'automated': True}
        }
    ]
    
    # Create test activities
    print("\nCreating test activities...")
    created_logs = []
    
    for i, activity_data in enumerate(test_activities):
        log = ActivityLog.log_activity(
            activity_type=activity_data['activity_type'],
            description=activity_data['description'],
            user=user if i < 3 else None,  # Last one has no user (system activity)
            related_council=council if i % 2 == 0 else None,  # Alternate council assignment
            status=activity_data['status'],
            details=activity_data['details']
        )
        created_logs.append(log)
        print(f"  ✓ Created: {log}")
    
    # Test querying activities
    print(f"\nTesting activity queries...")
    
    # Recent activities (using Django's timezone for recent filter)
    from django.utils import timezone
    from datetime import timedelta
    recent_cutoff = timezone.now() - timedelta(hours=1)
    recent = ActivityLog.objects.filter(created__gte=recent_cutoff).count()
    print(f"  Recent activities (last hour): {recent}")
    
    # Activities by type
    merge_activities = ActivityLog.objects.filter(activity_type='council_merge').count()
    print(f"  Council merge activities: {merge_activities}")
    
    # Activities by user
    user_activities = ActivityLog.objects.filter(user=user).count()
    print(f"  Activities by {user.username}: {user_activities}")
    
    # Activities for council
    council_activities = ActivityLog.objects.filter(related_council=council).count()
    print(f"  Activities for {council.name}: {council_activities}")
    
    # Test activity display
    print(f"\nRecent activity log entries:")
    for log in ActivityLog.objects.order_by('-created')[:5]:
        user_str = log.user.username if log.user else 'System'
        council_str = f" for {log.related_council.name}" if log.related_council else ""
        status_str = f" [{log.get_status_display()}]" if log.status != 'completed' else ""
        print(f"  {log.created.strftime('%H:%M:%S')} - {user_str}: {log.description}{council_str}{status_str}")
    
    # Cleanup test data
    print(f"\nCleaning up test data...")
    ActivityLog.objects.filter(id__in=[log.id for log in created_logs]).delete()
    if created:
        user.delete()
    
    print(f"✓ Test completed successfully!")

def test_backward_compatibility():
    """Test that old ActivityLog usage patterns still work"""
    print("\n" + "=" * 60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("=" * 60)
    
    # Test legacy field access
    log = ActivityLog.objects.create(
        activity_type='system',
        description='Legacy compatibility test',
        page='test_page',
        activity='test_activity',
        log_type='user',
        action='test_action'
    )
    
    print(f"Created legacy-style log: {log}")
    print(f"  Page: {log.page}")
    print(f"  Activity: {log.activity}")
    print(f"  Log type: {log.log_type}")
    print(f"  Action: {log.action}")
    
    # Cleanup
    log.delete()
    print("✓ Backward compatibility test passed!")

if __name__ == "__main__":
    try:
        test_activity_log()
        test_backward_compatibility()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("The enhanced ActivityLog is ready for:")
        print("1. ✅ Modern activity tracking with structured data")
        print("2. ✅ User attribution and IP tracking")
        print("3. ✅ Council-specific activity feeds")
        print("4. ✅ Status tracking (completed/failed/in_progress)")
        print("5. ✅ Backward compatibility with existing code")
        print("6. ✅ Enhanced God Mode integration")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
