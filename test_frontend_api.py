#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
import json

client = Client()
response = client.get('/api/factoids/counter/total-debt/worcestershire/2024-25/')
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'Found {data["count"]} factoids')
    for factoid in data['factoids']:
        if 'interest' in factoid['template_name'].lower():
            print(f'Interest factoid: {factoid["rendered_text"]}')
        else:
            print(f'{factoid["template_name"]}: {factoid["rendered_text"][:50]}...')
else:
    print(f'Error: {response.content.decode()}')
