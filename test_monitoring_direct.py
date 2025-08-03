#!/usr/bin/env python
"""
Test monitoring dashboard directly without Django server caching issues.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import importlib
import sys

# Force reload the monitoring module
if 'council_finance.services.realtime_monitoring' in sys.modules:
    del sys.modules['council_finance.services.realtime_monitoring']
if 'council_finance.views.ai_monitoring_dashboard' in sys.modules:
    del sys.modules['council_finance.views.ai_monitoring_dashboard']

print("Testing monitoring dashboard with fresh module imports...")

# Create a test client
client = Client()

# Create or get a staff user
user = User.objects.filter(is_staff=True).first()
if not user:
    user = User.objects.create_user('testuser', 'test@test.com', 'testpass')
    user.is_staff = True
    user.save()

# Login the user
client.force_login(user)

try:
    print("Making request to /ai-tools/monitoring/...")
    response = client.get('/ai-tools/monitoring/')
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("SUCCESS: Monitoring dashboard loaded successfully!")
        print("The issue was with Django server caching. The fix is working.")
    else:
        print(f"ERROR: Unexpected status code {response.status_code}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()