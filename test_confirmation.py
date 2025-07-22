#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import PendingProfileChange
from django.contrib.auth.models import User

def test_confirmation_process():
    """Test the confirmation process with the actual token"""
    
    token = "dvaHgoKWkZ53xCJgB3xZYUIjxXdU80KIBoSM4Lz5cTgxKD1hepdPxclUcJ9hp1Sb"
    
    print("=== TESTING CONFIRMATION PROCESS ===")
    print(f"Testing token: {token}")
    
    try:
        # Test the lookup logic from the view
        pending_change = PendingProfileChange.objects.get(token=token)
        print(f"✅ Token found: ID {pending_change.id}")
        print(f"   User: {pending_change.user.username}")
        print(f"   Field: {pending_change.field}")
        print(f"   New Value: {pending_change.new_value}")
        print(f"   Is Expired: {pending_change.is_expired}")
        print(f"   Is Valid: {pending_change.is_valid}")
        print(f"   Expires At: {pending_change.expires_at}")
        
        if pending_change.is_valid:
            print("✅ Token is valid and can be used for confirmation!")
            print(f"🔗 You can now visit: http://127.0.0.1:8000/accounts/profile/change/{token}/")
        else:
            print("❌ Token is not valid (expired or already used)")
            
    except PendingProfileChange.DoesNotExist:
        print("❌ Token not found in database")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_confirmation_process()
