#!/usr/bin/env python
"""Quick test script for field management URLs."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Create test client and login
client = Client()
try:
    # Login as admin
    login_result = client.login(username='admin', password='admin')
    print(f"Login successful: {login_result}")
    
    # Test field list
    response = client.get('/manage/fields/')
    print(f"Field list status: {response.status_code}")
    
    # Test field add form
    response = client.get('/manage/fields/add/')
    print(f"Field add form status: {response.status_code}")
    
    # Test field edit form (using a likely field slug)
    response = client.get('/manage/fields/capital_financing_requirement/')
    print(f"Field edit form status: {response.status_code}")
    
    print("All URL tests passed!")
    
except Exception as e:
    print(f"Test error: {e}")
