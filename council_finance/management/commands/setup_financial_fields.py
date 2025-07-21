from django.core.management.base import BaseCommand
from council_finance.models import DataField


class Command(BaseCommand):
    help = 'Create sample financial data fields for testing enhanced spreadsheet interface'

    def handle(self, *args, **options):
        """Create sample financial data fields."""
        
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
                self.stdout.write(
                    self.style.SUCCESS(f'Created field: {field.name} ({field.category})')
                )
            else:
                self.stdout.write(f'Field already exists: {field.name} ({field.category})')
        
        self.stdout.write(
            self.style.SUCCESS(f'\nCreated {created_count} new financial fields.')
        )
        
        total_financial = DataField.objects.filter(
            category__in=['balance_sheet', 'cash_flow', 'income', 'spending']
        ).count()
        
        self.stdout.write(
            self.style.SUCCESS(f'Total financial fields: {total_financial}')
        )
