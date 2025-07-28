#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models.factoid import FactoidTemplate
from council_finance.models.counter import CounterDefinition

print('=== FACTOID TEMPLATES ===')
for t in FactoidTemplate.objects.filter(is_active=True)[:5]:
    print(f'  {t.slug} - {t.name}')
    counter_slugs = list(t.counters.values_list('slug', flat=True))
    print(f'    Counters: {counter_slugs}')

print()
print('=== COUNTER DEFINITIONS ===')  
for c in CounterDefinition.objects.all()[:5]:
    print(f'  {c.slug} - {c.name}')
    templates = FactoidTemplate.objects.filter(counters=c, is_active=True)
    template_slugs = list(templates.values_list('slug', flat=True))
    print(f'    Templates: {template_slugs}')

print()
print('=== TOTAL DEBT COUNTER SPECIFICALLY ===')
try:
    total_debt = CounterDefinition.objects.get(slug='total-debt')
    print(f'Found counter: {total_debt.name}')
    templates = FactoidTemplate.objects.filter(counters=total_debt, is_active=True)
    print(f'Templates assigned: {list(templates.values_list("name", flat=True))}')
except CounterDefinition.DoesNotExist:
    print('Total debt counter not found!')
