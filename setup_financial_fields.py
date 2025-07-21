#!/usr/bin/env python
"""
Script to create sample financial data fields for testing the spreadsheet interface.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import DataField

def create_financial_fields():
    """Create sample financial data fields for testing."""
    
    # Balance Sheet fields
    balance_sheet_fields = [
        {
            'name': 'Total Assets',
            'slug': 'total_assets',
            'category': 'balance_sheet',
            'content_type': 'monetary',
            'explanation': 'Total value of all assets owned by the council',
        },
        {
            'name': 'Current Assets',
            'slug': 'current_assets',
            'category': 'balance_sheet',
            'content_type': 'monetary',
            'explanation': 'Assets that can be converted to cash within one year',
        },
        {
            'name': 'Fixed Assets',
            'slug': 'fixed_assets',
            'category': 'balance_sheet',
            'content_type': 'monetary',
            'explanation': 'Long-term tangible assets such as buildings and equipment',
        },
        {
            'name': 'Total Liabilities',
            'slug': 'total_liabilities',
            'category': 'balance_sheet',
            'content_type': 'monetary',
            'explanation': 'Total amount owed by the council',
        },
    ]
    
    # Cash Flow fields
    cash_flow_fields = [
        {
            'name': 'Operating Cash Flow',
            'slug': 'operating_cash_flow',
            'category': 'cash_flow',
            'content_type': 'monetary',
            'explanation': 'Cash generated from day-to-day operations',
        },
        {
            'name': 'Investment Cash Flow',
            'slug': 'investment_cash_flow',
            'category': 'cash_flow',
            'content_type': 'monetary',
            'explanation': 'Cash flow from investment activities',
        },
        {
            'name': 'Financing Cash Flow',
            'slug': 'financing_cash_flow',
            'category': 'cash_flow',
            'content_type': 'monetary',
            'explanation': 'Cash flow from financing activities',
        },
    ]
    
    # Income fields
    income_fields = [
        {
            'name': 'Council Tax Revenue',
            'slug': 'council_tax_revenue',
            'category': 'income',
            'content_type': 'monetary',
            'explanation': 'Revenue collected from council tax',
        },
        {
            'name': 'Government Grants',
            'slug': 'government_grants',
            'category': 'income',
            'content_type': 'monetary',
            'explanation': 'Grants received from central government',
        },
        {
            'name': 'Business Rates',
            'slug': 'business_rates',
            'category': 'income',
            'content_type': 'monetary',
            'explanation': 'Revenue from business rates',
        },
        {
            'name': 'Other Income',
            'slug': 'other_income',
            'category': 'income',
            'content_type': 'monetary',
            'explanation': 'Miscellaneous income sources',
        },
    ]
    
    # Spending fields
    spending_fields = [
        {
            'name': 'Staff Costs',
            'slug': 'staff_costs',
            'category': 'spending',
            'content_type': 'monetary',
            'explanation': 'Total expenditure on staff salaries and benefits',
        },
        {
            'name': 'Service Delivery Costs',
            'slug': 'service_delivery_costs',
            'category': 'spending',
            'content_type': 'monetary',
            'explanation': 'Costs of delivering council services',
        },
        {
            'name': 'Infrastructure Investment',
            'slug': 'infrastructure_investment',
            'category': 'spending',
            'content_type': 'monetary',
            'explanation': 'Investment in infrastructure projects',
        },
        {
            'name': 'Debt Servicing',
            'slug': 'debt_servicing',
            'category': 'spending',
            'content_type': 'monetary',
            'explanation': 'Interest and principal payments on debt',
        },
    ]
    
    all_fields = balance_sheet_fields + cash_flow_fields + income_fields + spending_fields
    
    created_count = 0
    for field_data in all_fields:
        field, created = DataField.objects.get_or_create(
            slug=field_data['slug'],
            defaults=field_data
        )
        if created:
            created_count += 1
            print(f"Created field: {field.name} ({field.category})")
        else:
            print(f"Field already exists: {field.name} ({field.category})")
    
    print(f"\nCreated {created_count} new financial fields.")
    print(f"Total financial fields: {DataField.objects.filter(category__in=['balance_sheet', 'cash_flow', 'income', 'spending']).count()}")

if __name__ == '__main__':
    create_financial_fields()
