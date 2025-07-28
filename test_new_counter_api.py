#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
import json

# Create a test client
client = Client()

# Test the new counter-based API endpoint
print("Testing new counter-based factoid API endpoint...")
response = client.get('/api/factoids/counter/total-debt/worcestershire/2024-25/')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'Success: {data.get("success")}')
    print(f'Found {data.get("count", 0)} factoids for {data.get("council")} - {data.get("counter")} ({data.get("year")})')
    print()
    for factoid in data.get('factoids', []):
        print(f'- {factoid["template_name"]}: {factoid["rendered_text"][:100]}...')
        print()
else:
    print(f'Error response: {response.content.decode()}')
