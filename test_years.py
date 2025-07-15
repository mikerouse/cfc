#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import FinancialYear

print('Current Financial Years:')
for year in FinancialYear.objects.all().order_by('-label'):
    print(f'  {year.label} - Current: {year.is_current}, Provisional: {year.is_provisional}, Forecast: {year.is_forecast}, Reliability: {year.data_reliability_level}')

print('\nTesting year creation:')
from council_finance.year_utils import create_year_with_smart_defaults, validate_year_label_format

# Test validation
test_year = "2025-26"
is_valid, error_message = validate_year_label_format(test_year)
print(f'Year "{test_year}" validation: {is_valid}, {error_message}')

if is_valid:
    try:
        year, created = create_year_with_smart_defaults(test_year, is_current=False)
        print(f'Year creation result: Created={created}, Provisional={year.is_provisional}, Forecast={year.is_forecast}')
        if created:
            print(f'Successfully created year with reliability level: {year.data_reliability_level}')
        else:
            print('Year already exists')
    except Exception as e:
        print(f'Error creating year: {e}')
