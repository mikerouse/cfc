#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.services.factoid_engine import FactoidEngine
from council_finance.models.council import Council, FinancialYear
from council_finance.models.counter import CounterDefinition

print("=== DEBUGGING INTEREST PAYMENTS FACTOIDS ===")
print("Following instructions debugging strategy...")

# 1. Test the lowest level first - direct field access
print("\n1. DIRECT FIELD ACCESS:")
engine = FactoidEngine()
council = Council.objects.get(slug='worcestershire')
year = FinancialYear.objects.get(label='2024/25')

value = engine.get_field_value('interest_payments_per_capita', council, year)
print(f'   interest_payments_per_capita: {value}')

# 2. Check for multiple instances
print("\n2. CHECK FOR MULTIPLE INSTANCES:")
from council_finance.models.factoid import FactoidInstance
counter = CounterDefinition.objects.get(slug='total-debt')

instances = FactoidInstance.objects.filter(
    council=council,
    financial_year=year,
    template__slug__icontains='interest'
)

for instance in instances:
    print(f'   Counter: {instance.counter.slug if instance.counter else "None"}')
    print(f'   Text: {instance.rendered_text}')
    print(f'   Expires: {instance.expires_at}')
    print()

# 3. Test computation directly
print("3. TEST COMPUTATION DIRECTLY:")
factoids = engine.get_factoids_for_counter(counter, council, year)
interest_factoids = [f for f in factoids if 'interest' in f.template.name.lower()]

print(f'   Found {len(interest_factoids)} interest factoids from engine')
for factoid in interest_factoids:
    print(f'   Text: {factoid.rendered_text}')

# 4. Test API integration 
print("\n4. TEST API INTEGRATION:")
from django.test import Client
client = Client()

response = client.get('/api/factoids/counter/total-debt/worcestershire/2024-25/')
if response.status_code == 200:
    import json
    data = json.loads(response.content)
    interest_factoids_api = [f for f in data['factoids'] if 'interest' in f['template_name'].lower()]
    print(f'   API returned {len(interest_factoids_api)} interest factoids')
    for factoid in interest_factoids_api:
        print(f'   API Text: {factoid["rendered_text"]}')
else:
    print(f'   API error: {response.status_code}')
