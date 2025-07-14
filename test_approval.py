"""
Direct test of the contribution approval functionality.
This bypasses the URL routing to test the new _apply_contribution_v2 function directly.
"""

import os
import sys
import django

# Add the project path
sys.path.append('/f/mikerouse/Documents/Projects/Council Finance Counters/v3/cfc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')

django.setup()

from django.contrib.auth.models import User
from council_finance.models import Council, DataField, Contribution
from council_finance.views import _apply_contribution_v2

def test_contribution_approval():
    """Test approving a contribution using the new system."""
    
    print("🧪 Testing contribution approval...")
    
    # Get test data
    user = User.objects.first()
    council = Council.objects.first()
    characteristic_field = DataField.objects.filter(category='characteristic').first()
    
    if not all([user, council, characteristic_field]):
        print("❌ Missing test data. Ensure you have users, councils, and characteristic fields.")
        return
    
    print(f"✅ Found test data:")
    print(f"   User: {user.username}")
    print(f"   Council: {council.name}")
    print(f"   Field: {characteristic_field.name} (category: {characteristic_field.category})")
    
    # Find a pending contribution
    pending_contribution = Contribution.objects.filter(
        status='pending',
        field=characteristic_field
    ).first()
    
    if not pending_contribution:
        print("❌ No pending contributions found for characteristic fields.")
        print("   Creating a test contribution...")
        
        pending_contribution = Contribution.objects.create(
            user=user,
            council=council,
            field=characteristic_field,
            value='TEST123',
            old_value='OLD123',
            status='pending'
        )
        print(f"✅ Created test contribution: {pending_contribution.id}")
    
    print(f"📝 Testing contribution:")
    print(f"   ID: {pending_contribution.id}")
    print(f"   Field: {pending_contribution.field.name}")
    print(f"   Value: {pending_contribution.value}")
    print(f"   Old Value: {pending_contribution.old_value}")
    
    # Test the new approval function
    try:
        print("🔄 Applying contribution using new system...")
        _apply_contribution_v2(pending_contribution, user)
        
        # Mark as approved
        pending_contribution.status = 'approved'
        pending_contribution.save()
        
        print("✅ SUCCESS! Contribution applied without errors.")
        print(f"   Contribution {pending_contribution.id} is now approved.")
        
        # Check what was created in the new system
        from council_finance.models.new_data_model import CouncilCharacteristic
        
        try:
            char = CouncilCharacteristic.objects.get(
                council=council,
                field=characteristic_field
            )
            print(f"✅ CouncilCharacteristic created/updated:")
            print(f"   Value: {char.value}")
            print(f"   Updated by: {char.updated_by}")
        except CouncilCharacteristic.DoesNotExist:
            print("⚠️  No CouncilCharacteristic found (may be expected for financial fields)")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_contribution_approval()
