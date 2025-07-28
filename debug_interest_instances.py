#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models.factoid import FactoidInstance
from council_finance.models.council import Council, FinancialYear
from council_finance.models.counter import CounterDefinition

council = Council.objects.get(slug='worcestershire')
year = FinancialYear.objects.get(label='2024/25')
counter = CounterDefinition.objects.get(slug='total-debt')

# Check all interest instances 
interest_instances = FactoidInstance.objects.filter(
    council=council,
    financial_year=year,
    template__slug__icontains='interest'
)

print(f'Found {interest_instances.count()} interest instances:')
for instance in interest_instances:
    print(f'  Counter: {instance.counter.slug if instance.counter else "None"}')
    print(f'  Text: {instance.rendered_text}')
    print()
