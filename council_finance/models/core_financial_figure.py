"""
Core Financial Figure Model - Fixed Schema for Reliable Financial Data

This model represents the new fixed-schema approach for storing council financial data.
It replaces the flexible FinancialFigure model with 25 predefined core financial fields
that are common across all UK council financial statements.

Benefits:
- Predictable PDF import mapping
- Atomic data operations  
- Better performance with direct column access
- Type safety and data integrity
- Easier validation and testing
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class CoreFinancialFigure(models.Model):
    """
    Fixed schema for core financial data - reliable and predictable
    
    All monetary values stored in pence for precision (max £999,999,999,999.99)
    Each council/year combination should have exactly one record
    """
    
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='core_figures')
    year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE, related_name='core_figures')
    
    # =================
    # INCOME FIELDS
    # =================
    total_income = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Total income for the financial year"
    )
    council_tax_income = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Income from council tax collection"
    )
    business_rates_income = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Income from business rates (NNDR)"
    )
    government_grants_income = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Government grants and specific grants"
    )
    fees_and_charges_income = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Income from fees and charges for services"
    )
    
    # =================
    # EXPENDITURE FIELDS
    # =================
    total_expenditure = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Total expenditure for the financial year"
    )
    employee_costs = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Staff costs including salaries, pensions, NI"
    )
    premises_costs = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Buildings, maintenance, utilities, business rates"
    )
    transport_costs = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Vehicle costs, fuel, public transport contracts"
    )
    supplies_and_services = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Equipment, supplies, professional services"
    )
    
    # =================
    # ASSET FIELDS
    # =================
    current_assets = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Cash, short-term investments, debtors"
    )
    long_term_assets = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Property, plant, equipment, long-term investments"
    )
    total_assets = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Total of current and long-term assets"
    )
    property_plant_equipment = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Property, plant and equipment at net book value"
    )
    
    # =================
    # LIABILITY FIELDS
    # =================
    current_liabilities = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Short-term debts due within one year"
    )
    long_term_liabilities = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Long-term debts due after one year"
    )
    pension_liability = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Pension fund deficit (can be negative for surplus)"
    )
    finance_leases = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Finance lease obligations and PFI liabilities"
    )
    provisions = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Provisions for future liabilities"
    )
    
    # =================
    # DEBT FIELDS
    # =================
    total_debt = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Total outstanding debt (often calculated field)"
    )
    interest_payments = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Interest paid on borrowings during the year"
    )
    borrowing_costs = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Total borrowing costs including interest and fees"
    )
    
    # =================
    # RESERVE FIELDS
    # =================
    total_reserves = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Total reserves (can be negative for deficit)"
    )
    usable_reserves = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Reserves available to fund future expenditure"
    )
    unusable_reserves = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Reserves not available for spending (revaluation, etc.)"
    )
    general_fund_balance = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Unallocated general fund balance"
    )
    
    # =================
    # CAPITAL FIELDS
    # =================
    capital_expenditure = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Capital expenditure on assets during the year"
    )
    capital_receipts = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Income from sale of capital assets"
    )
    capital_grants = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Capital grants received during the year"
    )
    
    # =================
    # METADATA FIELDS
    # =================
    DATA_SOURCE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('pdf_import', 'PDF Import'),
        ('csv_import', 'CSV Import'),
        ('api_import', 'API Import'),
        ('migration', 'Data Migration'),
    ]
    
    data_source = models.CharField(
        max_length=50, 
        choices=DATA_SOURCE_CHOICES, 
        default='manual',
        help_text="How this data was entered into the system"
    )
    source_file_name = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Name of imported file (if applicable)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='created_core_figures'
    )
    updated_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='updated_core_figures'
    )
    
    class Meta:
        unique_together = ('council', 'year')
        indexes = [
            models.Index(fields=['council', 'year']),
            models.Index(fields=['council']),
            models.Index(fields=['year']),
            models.Index(fields=['data_source']),
            models.Index(fields=['updated_at']),
        ]
        verbose_name = "Core Financial Figure"
        verbose_name_plural = "Core Financial Figures"
    
    def __str__(self):
        return f"{self.council.name} - {self.year.label}"
    
    def clean(self):
        """Validate data consistency"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate that total_assets = current_assets + long_term_assets (if all present)
        if all([self.total_assets, self.current_assets, self.long_term_assets]):
            calculated_total = self.current_assets + self.long_term_assets
            if abs(self.total_assets - calculated_total) > Decimal('100.00'):  # Allow £100 rounding difference
                errors['total_assets'] = f"Total assets ({self.total_assets}) should equal current ({self.current_assets}) + long-term ({self.long_term_assets}) = {calculated_total}"
        
        # Validate that total_reserves = usable_reserves + unusable_reserves (if all present)
        if all([self.total_reserves, self.usable_reserves, self.unusable_reserves]):
            calculated_total = self.usable_reserves + self.unusable_reserves
            if abs(self.total_reserves - calculated_total) > Decimal('100.00'):
                errors['total_reserves'] = f"Total reserves ({self.total_reserves}) should equal usable ({self.usable_reserves}) + unusable ({self.unusable_reserves}) = {calculated_total}"
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def completeness_percentage(self):
        """Calculate what percentage of fields have data"""
        field_names = [
            'total_income', 'council_tax_income', 'business_rates_income', 
            'government_grants_income', 'fees_and_charges_income',
            'total_expenditure', 'employee_costs', 'premises_costs', 
            'transport_costs', 'supplies_and_services',
            'current_assets', 'long_term_assets', 'total_assets', 'property_plant_equipment',
            'current_liabilities', 'long_term_liabilities', 'pension_liability', 
            'finance_leases', 'provisions',
            'total_debt', 'interest_payments', 'borrowing_costs',
            'total_reserves', 'usable_reserves', 'unusable_reserves', 'general_fund_balance',
            'capital_expenditure', 'capital_receipts', 'capital_grants'
        ]
        
        populated_count = sum(1 for field_name in field_names if getattr(self, field_name) is not None)
        return round((populated_count / len(field_names)) * 100, 1)
    
    @property 
    def essential_fields_complete(self):
        """Check if essential fields for basic analysis are present"""
        essential_fields = [
            'total_income', 'total_expenditure', 'current_liabilities', 
            'long_term_liabilities', 'total_reserves'
        ]
        return all(getattr(self, field) is not None for field in essential_fields)
    
    def get_field_value_by_slug(self, field_slug):
        """Get field value using URL-style slug format"""
        field_mapping = {
            'total-income': self.total_income,
            'council-tax-income': self.council_tax_income,
            'business-rates-income': self.business_rates_income,
            'government-grants-income': self.government_grants_income,
            'fees-and-charges-income': self.fees_and_charges_income,
            'total-expenditure': self.total_expenditure,
            'employee-costs': self.employee_costs,
            'premises-costs': self.premises_costs,
            'transport-costs': self.transport_costs,
            'supplies-and-services': self.supplies_and_services,
            'current-assets': self.current_assets,
            'long-term-assets': self.long_term_assets,
            'total-assets': self.total_assets,
            'property-plant-equipment': self.property_plant_equipment,
            'current-liabilities': self.current_liabilities,
            'long-term-liabilities': self.long_term_liabilities,
            'pension-liability': self.pension_liability,
            'finance-leases': self.finance_leases,
            'provisions': self.provisions,
            'total-debt': self.total_debt,
            'interest-payments': self.interest_payments,
            'borrowing-costs': self.borrowing_costs,
            'total-reserves': self.total_reserves,
            'usable-reserves': self.usable_reserves,
            'unusable-reserves': self.unusable_reserves,
            'general-fund-balance': self.general_fund_balance,
            'capital-expenditure': self.capital_expenditure,
            'capital-receipts': self.capital_receipts,
            'capital-grants': self.capital_grants,
        }
        return field_mapping.get(field_slug)


# Field mapping constants for use across the system
CORE_FIELD_MAPPING = {
    # Slug format -> Model attribute
    'total-income': 'total_income',
    'council-tax-income': 'council_tax_income',
    'business-rates-income': 'business_rates_income',
    'government-grants-income': 'government_grants_income',
    'fees-and-charges-income': 'fees_and_charges_income',
    'total-expenditure': 'total_expenditure',
    'employee-costs': 'employee_costs',
    'premises-costs': 'premises_costs',
    'transport-costs': 'transport_costs',
    'supplies-and-services': 'supplies_and_services',
    'current-assets': 'current_assets',
    'long-term-assets': 'long_term_assets',
    'total-assets': 'total_assets',
    'property-plant-equipment': 'property_plant_equipment',
    'current-liabilities': 'current_liabilities',
    'long-term-liabilities': 'long_term_liabilities',
    'pension-liability': 'pension_liability',
    'finance-leases': 'finance_leases',
    'provisions': 'provisions',
    'total-debt': 'total_debt',
    'interest-payments': 'interest_payments',
    'borrowing-costs': 'borrowing_costs',
    'total-reserves': 'total_reserves',
    'usable-reserves': 'usable_reserves',
    'unusable-reserves': 'unusable_reserves',
    'general-fund-balance': 'general_fund_balance',
    'capital-expenditure': 'capital_expenditure',
    'capital-receipts': 'capital_receipts',
    'capital-grants': 'capital_grants',
}

# Financial field slugs that need millions->full amount conversion
FINANCIAL_FIELD_SLUGS = list(CORE_FIELD_MAPPING.keys())
