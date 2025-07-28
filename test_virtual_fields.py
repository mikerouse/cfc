#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models.council import Council, FinancialYear
from council_finance.services.factoid_engine import FactoidEngine

# Test virtual fields
engine = FactoidEngine()
council = Council.objects.first()
year = FinancialYear.objects.first()

print(f"Testing virtual fields with {council.name} for {year.label}")
print("-" * 50)

virtual_fields = ['council_name', 'year_label', 'council_slug', 'council_type']

for field in virtual_fields:
    value = engine.get_field_value(field, council, year)
    print(f"{field}: {value}")
