#!/usr/bin/env python3
"""
Test script to check if imports are working.
"""
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.abspath('.'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')

# Import Django and configure
import django
django.setup()

print("Django setup complete")

# Test the imports
try:
    from council_finance.emails import send_confirmation_email
    print("✓ Successfully imported send_confirmation_email")
except ImportError as e:
    print(f"✗ Failed to import send_confirmation_email: {e}")

try:
    from council_finance.notifications import create_notification
    print("✓ Successfully imported create_notification")
except ImportError as e:
    print(f"✗ Failed to import create_notification: {e}")

try:
    from council_finance.forms import SignUpForm
    print("✓ Successfully imported SignUpForm")
except ImportError as e:
    print(f"✗ Failed to import SignUpForm: {e}")

try:
    from council_finance.views.general import log_activity
    print("✓ Successfully imported log_activity from general.py")
except ImportError as e:
    print(f"✗ Failed to import log_activity: {e}")

print("Import test complete")
