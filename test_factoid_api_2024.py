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

# Test the API endpoint without year (should work)
print("Testing factoid API endpoint without year...")
response = client.get('/api/factoid/counter/worcestershire/total-debt/')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'Found {data["count"]} factoids for {data["council"]} - {data["counter"]}')
    print(f'Year: {data.get("year", "Not specified")}')
    print()
    for factoid in data['factoids']:
        print(f'- {factoid["template_name"]}: {factoid["rendered_text"][:100]}...')
        print()
else:
    print(f'Error response: {response.content.decode()}')

print("\n" + "="*50 + "\n")

# Now test with financial year format
print("Testing factoid API endpoint with financial year (2024/25)...")
response = client.get('/api/factoid/counter/worcestershire/total-debt/2024/25/')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'Found {data["count"]} factoids for {data["council"]} - {data["counter"]} ({data["year"]})')
    print()
    for factoid in data['factoids']:
        print(f'- {factoid["template_name"]}: {factoid["rendered_text"][:100]}...')
        print()
else:
    print(f'Error response: {response.content.decode()}')
