# Financial Schema Redesign: Fixed Core Fields + Dynamic Calculated Fields

**Date**: 2025-08-15  
**Status**: In Progress  
**Priority**: Critical - Fixes data integrity issues with PDF imports

## Problem Statement

The current flexible field creation system has become overly complex and unreliable, causing data integrity issues where users enter one figure but a different figure appears after saving. Key issues:

- **Leeds PDF Import Failure**: Wrong long-term liabilities saved despite rejection, interest payments not saved
- **Multiple Abstraction Layers**: PDF Processing → Field Mapping → Frontend Review → Individual API Saves → Database Storage
- **Inconsistent Field Mappings**: Multiple naming conventions between systems
- **Non-atomic Saves**: Individual field saves through separate API calls
- **Complex Category Resolution**: Dynamic field creation causes performance and reliability issues

## Solution: Hybrid Architecture

Combine the reliability of fixed schemas with the analytical flexibility of calculated fields.

### Core Concept

1. **Fixed Core Financial Fields** (25 essential fields): Predictable, reliable, direct PDF mapping
2. **Dynamic Calculated Fields**: Unlimited custom analysis and data manipulation  
3. **Unified Counter System**: Can display either core fields or calculated field results

## Implementation Phases

### Phase 1: Core Financial Schema (Weeks 1-2)
**Goal**: Create reliable foundation for essential financial data

#### 1.1 Define Core Financial Fields
```python
CORE_FINANCIAL_FIELDS = {
    'income': [
        'total-income', 'council-tax-income', 'business-rates-income', 
        'government-grants-income', 'fees-and-charges-income'
    ],
    'expenditure': [
        'total-expenditure', 'employee-costs', 'premises-costs', 
        'transport-costs', 'supplies-and-services'
    ],
    'assets': [
        'current-assets', 'long-term-assets', 'total-assets', 
        'property-plant-equipment'
    ],
    'liabilities': [
        'current-liabilities', 'long-term-liabilities', 'pension-liability', 
        'finance-leases', 'provisions'
    ],
    'debt': [
        'total-debt', 'interest-payments', 'borrowing-costs'
    ],
    'reserves': [
        'total-reserves', 'usable-reserves', 'unusable-reserves', 
        'general-fund-balance'
    ],
    'capital': [
        'capital-expenditure', 'capital-receipts', 'capital-grants'
    ]
}
```

#### 1.2 Create New Data Model
```python
class CoreFinancialFigure(models.Model):
    """Fixed schema for core financial data - reliable and predictable"""
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    
    # Income fields (in pence for precision)
    total_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    council_tax_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    business_rates_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    government_grants_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fees_and_charges_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Expenditure fields
    total_expenditure = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    employee_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    premises_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    transport_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    supplies_and_services = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Asset fields
    current_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    long_term_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    property_plant_equipment = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Liability fields  
    current_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    long_term_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pension_liability = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    finance_leases = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    provisions = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Debt fields
    total_debt = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    interest_payments = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    borrowing_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Reserve fields
    total_reserves = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    usable_reserves = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unusable_reserves = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    general_fund_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Capital fields
    capital_expenditure = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    capital_receipts = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    capital_grants = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(max_length=50, choices=[
        ('manual', 'Manual Entry'),
        ('pdf_import', 'PDF Import'),
        ('csv_import', 'CSV Import'),
        ('api_import', 'API Import')
    ], default='manual')
    
    class Meta:
        unique_together = ('council', 'year')
        indexes = [
            models.Index(fields=['council', 'year']),
            models.Index(fields=['council']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return f"{self.council.name} - {self.year.label}"
```

#### 1.3 Migration Strategy
- Create data migration to move existing FinancialFigure data to CoreFinancialFigure
- Map field slugs to model attributes using predefined mapping
- Validate data integrity during migration
- Keep existing models temporarily for rollback capability

### Phase 2: Calculated Fields System (Weeks 3-4)
**Goal**: Restore analytical flexibility with clean architecture

#### 2.1 Calculated Field Models
```python
class CalculatedField(models.Model):
    """User-defined calculated fields for custom analysis"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    formula = models.TextField()  # Python expression using field names
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_core = models.BooleanField(default=False)  # Core vs user-defined
    is_public = models.BooleanField(default=False)  # Shareable with other users
    
    # Formula validation
    is_valid = models.BooleanField(default=True)
    validation_error = models.TextField(blank=True)
    last_validated = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validate formula syntax and field references"""
        # Implementation in Phase 2
        pass
    
    def calculate_value(self, core_figure):
        """Calculate value for given CoreFinancialFigure instance"""
        # Implementation in Phase 2
        pass

class CalculatedFieldValue(models.Model):
    """Computed values for calculated fields"""
    calculated_field = models.ForeignKey(CalculatedField, on_delete=models.CASCADE)
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('calculated_field', 'council', 'year')
        indexes = [
            models.Index(fields=['calculated_field', 'council', 'year']),
            models.Index(fields=['council', 'year']),
        ]
```

#### 2.2 Core Calculated Fields
```python
CORE_CALCULATED_FIELDS = {
    'total-debt': {
        'name': 'Total Debt',
        'formula': 'current_liabilities + long_term_liabilities + finance_leases',
        'description': 'Sum of all debt components'
    },
    'net-worth': {
        'name': 'Net Worth', 
        'formula': 'total_assets - (current_liabilities + long_term_liabilities)',
        'description': 'Assets minus total liabilities'
    },
    'debt-to-income-ratio': {
        'name': 'Debt to Income Ratio',
        'formula': '(total_debt / total_income) * 100 if total_income else 0',
        'description': 'Total debt as percentage of income'
    },
    'interest-burden': {
        'name': 'Interest Burden',
        'formula': '(interest_payments / total_income) * 100 if total_income else 0', 
        'description': 'Interest payments as percentage of income'
    },
    'reserves-ratio': {
        'name': 'Reserves Ratio',
        'formula': '(total_reserves / total_expenditure) * 100 if total_expenditure else 0',
        'description': 'Reserves as percentage of annual expenditure'
    }
}
```

#### 2.3 Formula Builder UI
- **Field Selector**: Dropdown with all 25 core fields
- **Operator Palette**: +, -, *, /, (), mathematical functions
- **Real-time Validation**: Check formula syntax as user types
- **Live Preview**: Show calculated result for selected council/year
- **Formula Templates**: Common calculations (ratios, per capita, etc.)

### Phase 3: Counter System Integration (Week 5)
**Goal**: Unified display system for both core and calculated fields

#### 3.1 Enhanced Counter Models
```python
class Counter(models.Model):
    """Enhanced counter supporting both core and calculated fields"""
    COUNTER_TYPES = [
        ('core', 'Core Financial Field'),
        ('calculated', 'Calculated Field')
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    counter_type = models.CharField(max_length=20, choices=COUNTER_TYPES)
    
    # For core field counters
    core_field_name = models.CharField(max_length=100, blank=True)
    
    # For calculated field counters  
    calculated_field = models.ForeignKey(
        CalculatedField, 
        on_delete=models.CASCADE, 
        null=True, blank=True
    )
    
    # Display formatting
    display_format = models.CharField(max_length=50, default='currency')
    precision = models.IntegerField(default=2)
    show_millions = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 3.2 Counter Value Resolution
```python
class CounterAgent:
    """Enhanced agent supporting both core and calculated fields"""
    
    def get_counter_value(self, counter, council, year):
        """Get value for any counter type"""
        if counter.counter_type == 'core':
            return self._get_core_field_value(counter.core_field_name, council, year)
        elif counter.counter_type == 'calculated':
            return self._get_calculated_field_value(counter.calculated_field, council, year)
    
    def _get_core_field_value(self, field_name, council, year):
        """Direct access to CoreFinancialFigure field"""
        try:
            core_figure = CoreFinancialFigure.objects.get(council=council, year=year)
            return getattr(core_figure, field_name, None)
        except CoreFinancialFigure.DoesNotExist:
            return None
    
    def _get_calculated_field_value(self, calculated_field, council, year):
        """Get or compute calculated field value"""
        # Try cache first
        try:
            cached_value = CalculatedFieldValue.objects.get(
                calculated_field=calculated_field,
                council=council, 
                year=year
            )
            # Return if fresh (computed within last hour)
            if timezone.now() - cached_value.computed_at < timedelta(hours=1):
                return cached_value.value
        except CalculatedFieldValue.DoesNotExist:
            pass
        
        # Compute fresh value
        try:
            core_figure = CoreFinancialFigure.objects.get(council=council, year=year)
            value = calculated_field.calculate_value(core_figure)
            
            # Cache result
            CalculatedFieldValue.objects.update_or_create(
                calculated_field=calculated_field,
                council=council,
                year=year,
                defaults={'value': value}
            )
            
            return value
        except Exception as e:
            # Log error to Event Viewer
            SystemEvent.objects.create(
                source='counter_agent',
                level='error',
                category='data_processing',
                title='Calculated Field Computation Failed',
                message=f'Failed to compute {calculated_field.name}: {str(e)}',
                details={
                    'calculated_field_id': calculated_field.id,
                    'council_slug': council.slug,
                    'year_label': year.label,
                    'formula': calculated_field.formula
                }
            )
            return None
```

### Phase 4: PDF Processing Integration (Week 6)
**Goal**: Direct mapping from PDF to CoreFinancialFigure

#### 4.1 Enhanced PDF Extractor
```python
class CoreFinancialExtractor:
    """PDF extractor targeting CoreFinancialFigure directly"""
    
    FIELD_MAPPING = {
        # Direct mapping from PDF field names to model attributes
        'total-income': 'total_income',
        'council-tax-income': 'council_tax_income', 
        'current-liabilities': 'current_liabilities',
        'long-term-liabilities': 'long_term_liabilities',
        'interest-payments': 'interest_payments',
        # ... complete mapping for all 25 fields
    }
    
    def extract_to_core_figure(self, pdf_content, council, year):
        """Extract directly to CoreFinancialFigure instance"""
        # Extract all fields atomically
        extracted_data = self._extract_all_fields(pdf_content)
        
        # Create or update CoreFinancialFigure
        core_figure, created = CoreFinancialFigure.objects.get_or_create(
            council=council,
            year=year,
            defaults={'data_source': 'pdf_import'}
        )
        
        # Update all fields in single atomic operation
        with transaction.atomic():
            for pdf_field, model_attr in self.FIELD_MAPPING.items():
                if pdf_field in extracted_data:
                    setattr(core_figure, model_attr, extracted_data[pdf_field])
            
            core_figure.save()
            
            # Log successful extraction
            SystemEvent.objects.create(
                source='pdf_extractor',
                level='info',
                category='data_processing',
                title='PDF Extraction Completed',
                message=f'Successfully extracted {len(extracted_data)} fields',
                details={
                    'council_slug': council.slug,
                    'year_label': year.label,
                    'fields_extracted': list(extracted_data.keys()),
                    'extraction_method': 'core_financial_extractor'
                }
            )
        
        return core_figure
```

#### 4.2 Atomic Save API
```python
# In council_edit_api.py
@require_http_methods(["POST"])
def save_core_financial_data(request):
    """Atomic save for all core financial fields"""
    try:
        data = json.loads(request.body)
        council_slug = data.get('council_slug')
        year_label = data.get('year_label')
        field_data = data.get('fields', {})
        
        council = get_object_or_404(Council, slug=council_slug)
        year = get_object_or_404(Year, label=year_label)
        
        # Atomic update of all fields
        with transaction.atomic():
            core_figure, created = CoreFinancialFigure.objects.get_or_create(
                council=council,
                year=year,
                defaults={'data_source': 'manual'}
            )
            
            updated_fields = []
            for field_slug, value in field_data.items():
                model_attr = CORE_FIELD_MAPPING.get(field_slug)
                if model_attr and value is not None:
                    # Convert millions to full amount for financial fields
                    if field_slug in FINANCIAL_FIELD_SLUGS:
                        value = Decimal(str(value)) * 1000000
                    
                    setattr(core_figure, model_attr, value)
                    updated_fields.append(field_slug)
            
            core_figure.save()
            
            # Invalidate calculated field caches
            CalculatedFieldValue.objects.filter(
                council=council,
                year=year
            ).delete()
            
            return JsonResponse({
                'success': True,
                'updated_fields': updated_fields,
                'message': f'Successfully updated {len(updated_fields)} fields atomically'
            })
            
    except Exception as e:
        # Log error to Event Viewer  
        SystemEvent.objects.create(
            source='council_edit_api',
            level='error', 
            category='data_processing',
            title='Core Financial Data Save Failed',
            message=f'Failed to save core financial data: {str(e)}',
            details={
                'council_slug': council_slug,
                'year_label': year_label,
                'field_count': len(field_data) if field_data else 0,
                'error_type': type(e).__name__
            }
        )
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

## Benefits of This Approach

### Reliability
- ✅ **Predictable PDF Imports**: Direct field mapping, no category resolution
- ✅ **Atomic Data Operations**: All-or-nothing saves prevent partial updates
- ✅ **Type Safety**: Fixed schema with proper field types and constraints
- ✅ **Data Integrity**: Foreign key constraints and unique constraints enforced

### Performance  
- ✅ **Fast Queries**: No dynamic field resolution, direct column access
- ✅ **Efficient Indexing**: Proper database indexes on fixed schema
- ✅ **Cached Calculations**: Calculated field values cached with invalidation
- ✅ **Reduced Complexity**: Fewer abstraction layers, cleaner code paths

### Flexibility
- ✅ **Unlimited Analysis**: Users can create any calculated field they need
- ✅ **Formula Sharing**: Public calculated fields for common analysis patterns
- ✅ **Counter Integration**: Both core and calculated fields can power counters
- ✅ **Migration Path**: Gradual migration from existing flexible system

### Maintainability
- ✅ **Clear Separation**: Core reliability vs analytical flexibility
- ✅ **Reduced Technical Debt**: Replace complex dynamic system with clean architecture
- ✅ **Better Testing**: Fixed schema easier to test and validate
- ✅ **Documentation**: Clear data model structure and relationships

## Migration Timeline

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create CoreFinancialFigure model and migration
- [ ] Implement data migration from existing FinancialFigure  
- [ ] Create mapping utilities and validation scripts
- [ ] Update PDF extractor for direct core figure mapping

### Phase 2: Calculated Fields (Weeks 3-4)  
- [ ] Create CalculatedField and CalculatedFieldValue models
- [ ] Implement formula validation and computation engine
- [ ] Build formula builder UI components
- [ ] Create core calculated fields (total-debt, ratios, etc.)

### Phase 3: Integration (Week 5)
- [ ] Update Counter system to support both field types
- [ ] Enhance CounterAgent for unified value resolution  
- [ ] Update frontend council detail pages
- [ ] Create counter migration scripts

### Phase 4: Production (Week 6)
- [ ] Implement atomic save API for core financial data
- [ ] Update PDF import workflow to use CoreFinancialFigure
- [ ] Add comprehensive error handling and Event Viewer integration
- [ ] Performance testing and optimization

### Phase 5: Migration & Cleanup (Week 7)
- [ ] Migrate all existing counters to new system
- [ ] Import historical calculated field definitions
- [ ] Remove deprecated FinancialFigure code (after validation)
- [ ] Update documentation and user guides

## Risk Mitigation

### Data Loss Prevention
- Keep existing models during migration period
- Comprehensive validation scripts at each phase
- Rollback procedures for each migration step
- Event Viewer monitoring for all data operations

### Performance Monitoring
- Database query analysis before/after migration
- Counter calculation performance benchmarks  
- Memory usage monitoring for calculated field computations
- API response time tracking

### User Experience
- Gradual rollout with feature flags
- User testing of formula builder before full release
- Clear migration communication to users
- Support documentation for new calculated fields

## Success Metrics

### Reliability Metrics
- **PDF Import Success Rate**: Target >95% (currently ~70%)
- **Data Consistency**: Zero cases of "wrong figure saved"
- **Error Rate**: <1% of financial data operations fail

### Performance Metrics  
- **Page Load Times**: Council detail pages <2 seconds
- **API Response**: Financial data APIs <500ms
- **Database Efficiency**: <50 queries per council detail page

### User Adoption
- **Calculated Fields Created**: Target 50+ user-defined fields within 3 months
- **User Satisfaction**: >90% positive feedback on new system
- **Support Tickets**: <50% reduction in data-related support requests

## Next Steps

1. **Create Phase 1 Implementation Branch**: `feature/core-financial-schema`
2. **Design CoreFinancialFigure Model**: Complete field definitions and validation
3. **Plan Data Migration Strategy**: Script to move existing FinancialFigure data
4. **Update PDF Extractor**: Direct mapping to CoreFinancialFigure
5. **Begin Implementation**: Start with model creation and basic migration scripts

This redesign will solve the immediate Leeds import issues while building a foundation for more reliable and flexible financial data management long-term.
