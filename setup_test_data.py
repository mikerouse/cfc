import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

# Import models
from council_finance.models import DataField, FinancialYear

print("Creating financial fields...")

# Financial field data
fields_data = [
    {'name': 'Total Assets', 'slug': 'total_assets', 'category': 'balance_sheet', 'content_type': 'monetary'},
    {'name': 'Current Assets', 'slug': 'current_assets', 'category': 'balance_sheet', 'content_type': 'monetary'},
    {'name': 'Total Liabilities', 'slug': 'total_liabilities', 'category': 'balance_sheet', 'content_type': 'monetary'},
    {'name': 'Operating Cash Flow', 'slug': 'operating_cash_flow', 'category': 'cash_flow', 'content_type': 'monetary'},
    {'name': 'Investment Cash Flow', 'slug': 'investment_cash_flow', 'category': 'cash_flow', 'content_type': 'monetary'},
    {'name': 'Council Tax Revenue', 'slug': 'council_tax_revenue', 'category': 'income', 'content_type': 'monetary'},
    {'name': 'Government Grants', 'slug': 'government_grants', 'category': 'income', 'content_type': 'monetary'},
    {'name': 'Staff Costs', 'slug': 'staff_costs', 'category': 'spending', 'content_type': 'monetary'},
    {'name': 'Service Delivery Costs', 'slug': 'service_delivery_costs', 'category': 'spending', 'content_type': 'monetary'},
]

for field_data in fields_data:
    field, created = DataField.objects.get_or_create(
        slug=field_data['slug'],
        defaults=field_data
    )
    if created:
        print(f"✓ Created: {field.name}")
    else:
        print(f"  Exists: {field.name}")

# Create financial year
year, created = FinancialYear.objects.get_or_create(
    label='2025/26',
    defaults={'display': '2025/26'}
)
if created:
    print(f"✓ Created financial year: {year.label}")
else:
    print(f"  Financial year exists: {year.label}")

print("Setup completed!")
