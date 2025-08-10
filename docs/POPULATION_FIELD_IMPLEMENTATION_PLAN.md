# Population Field Implementation Plan

**Created**: 2025-01-07  
**Updated**: 2025-01-07  
**Status**: IMPLEMENTED ✅  
**Risk Level**: Medium-High (Core field used throughout system)

## Overview

Population is currently implemented as:
1. **Council.latest_population** - Cached integer field on Council model
2. **DataField with slug "population"** - Source data stored in CouncilCharacteristic/FinancialFigure

We need to support:
1. **Current Population** (characteristic) - For display purposes
2. **Historical Population** (temporal) - For accurate per capita calculations by year

## Current System Analysis

### Critical Dependencies
- **Council.latest_population**: Used in 50+ locations for display and calculations
- **Per capita calculations**: Site totals, comparisons, API responses
- **Templates**: Display "X residents" throughout the site
- **API responses**: Population included in multiple endpoints
- **Cache reconciliation**: Complex update mechanism with fallbacks

### Data Flow
```
DataField "population" → CouncilCharacteristic → council.update_latest_population() → council.latest_population
                      ↘ FinancialFigure (temporal) ↗
```

## Implementation Strategy

### Phase 1: Add Temporal Population Support (No Breaking Changes)

**1. Keep existing system intact:**
- `Council.latest_population` remains unchanged
- All current displays continue working
- No template changes required initially

**2. Add temporal population storage:**
```python
# Already supported! FinancialFigure can store population by year
# We just need to ensure it's used for per capita calculations
```

**3. Update calculation logic:**
```python
def get_population_for_year(council, year):
    """
    Get population for a specific financial year.
    Falls back to latest_population if no year-specific data.
    """
    # Try to get year-specific population
    pop_field = DataField.objects.get(slug='population')
    try:
        fig = FinancialFigure.objects.get(
            council=council,
            year=year,
            field=pop_field
        )
        return int(fig.value) if fig.value else council.latest_population
    except FinancialFigure.DoesNotExist:
        return council.latest_population
```

### Phase 2: Update Per Capita Calculations

**1. Modify calculation contexts:**
```python
# In council_finance/utils/data_context.py
def build_data_context(council, year=None):
    """Build context with year-aware population"""
    context = {}
    
    # ... existing code ...
    
    # Use year-specific population if available
    if year:
        context['population'] = get_population_for_year(council, year)
    else:
        context['population'] = council.latest_population
    
    return context
```

**2. Update Counter Agent calculations:**
```python
# In agents.py - ensure CounterAgent uses year-specific population
def get_field_value(self, field_slug, council, year):
    if field_slug == 'population':
        return get_population_for_year(council, year)
    # ... rest of existing logic
```

### Phase 3: UI Integration

**1. Council Edit - Characteristics Section:**
- Display current population with clear labeling
- Update help text: "This is the current population for display purposes"

**2. Council Edit - Financial Data Section:**
- Add population field to temporal data
- Show comparison with current population if different
- Help text: "Population for this financial year (used for per capita calculations)"

**3. Data Entry Forms:**
```python
# Add to financial data forms
class FinancialDataForm(forms.Form):
    population_for_year = forms.IntegerField(
        label=f"Population ({year.label})",
        help_text="Used for per capita calculations in this financial year",
        required=False,
        initial=council.latest_population  # Pre-fill with current
    )
```

## Migration Plan

### Step 1: Database Preparation (No schema changes needed!)
```python
# The FinancialFigure model already supports this
# Just need to ensure population DataField exists and is configured correctly
```

### Step 2: Data Migration Script
```python
from django.core.management.base import BaseCommand
from council_finance.models import Council, DataField, FinancialFigure, FinancialYear

class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Populate historical population data where missing.
        Initially copies latest_population to all years as starting point.
        """
        pop_field = DataField.objects.get(slug='population')
        
        for council in Council.objects.all():
            if not council.latest_population:
                continue
                
            # For each year, check if population exists
            for year in FinancialYear.objects.all():
                fig, created = FinancialFigure.objects.get_or_create(
                    council=council,
                    year=year,
                    field=pop_field,
                    defaults={'value': str(council.latest_population)}
                )
                if created:
                    self.stdout.write(
                        f"Created population for {council.name} {year.label}"
                    )
```

### Step 3: Update Reconciliation Logic
```python
# Modify council_finance/utils/population.py
def reconcile_populations():
    """
    Update latest_population from most recent year's data.
    """
    pop_field = DataField.objects.get(slug='population')
    current_year = FinancialYear.objects.order_by('-start_date').first()
    
    for council in Council.objects.all():
        # Get most recent population data
        latest_pop = FinancialFigure.objects.filter(
            council=council,
            field=pop_field,
            value__isnull=False
        ).order_by('-year__start_date').first()
        
        if latest_pop and latest_pop.value:
            try:
                new_pop = int(latest_pop.value)
                if council.latest_population != new_pop:
                    council.latest_population = new_pop
                    council.save(update_fields=['latest_population'])
            except ValueError:
                continue
```

## Testing Strategy

### 1. Unit Tests
```python
# test_population_changes.py
from django.test import TestCase
from council_finance.models import Council, DataField, FinancialFigure, FinancialYear

class PopulationTestCase(TestCase):
    def setUp(self):
        self.council = Council.objects.create(
            name="Test Council",
            slug="test-council",
            latest_population=100000
        )
        self.year_2024 = FinancialYear.objects.create(
            label="2024/25",
            start_date="2024-04-01",
            end_date="2025-03-31"
        )
        self.year_2023 = FinancialYear.objects.create(
            label="2023/24", 
            start_date="2023-04-01",
            end_date="2024-03-31"
        )
        self.pop_field = DataField.objects.create(
            slug="population",
            name="Population",
            content_type="integer"
        )
    
    def test_latest_population_unchanged(self):
        """Ensure latest_population continues to work"""
        self.assertEqual(self.council.latest_population, 100000)
    
    def test_year_specific_population(self):
        """Test year-specific population retrieval"""
        # Add historical population
        FinancialFigure.objects.create(
            council=self.council,
            year=self.year_2023,
            field=self.pop_field,
            value="95000"
        )
        
        # Test retrieval
        pop_2023 = get_population_for_year(self.council, self.year_2023)
        pop_2024 = get_population_for_year(self.council, self.year_2024)
        
        self.assertEqual(pop_2023, 95000)
        self.assertEqual(pop_2024, 100000)  # Falls back to latest
    
    def test_per_capita_calculation_uses_correct_population(self):
        """Ensure per capita uses year-specific population"""
        # Add different populations for different years
        FinancialFigure.objects.create(
            council=self.council,
            year=self.year_2023,
            field=self.pop_field,
            value="95000"
        )
        
        # Add debt data
        debt_field = DataField.objects.create(
            slug="total-debt",
            name="Total Debt",
            content_type="monetary"
        )
        FinancialFigure.objects.create(
            council=self.council,
            year=self.year_2023,
            field=debt_field,
            value="95000000"  # 95 million
        )
        
        # Calculate per capita for 2023
        context = build_data_context(self.council, self.year_2023)
        debt_per_capita = context['total_debt'] / context['population']
        
        self.assertEqual(debt_per_capita, 1000)  # 95M / 95K = 1000
```

### 2. Integration Tests
```python
def test_council_edit_shows_both_populations(self):
    """Test that edit forms show both current and historical population"""
    response = self.client.get(
        f'/councils/{self.council.slug}/edit/financial/2023-24/'
    )
    
    # Should show current population for reference
    self.assertContains(response, "Current population: 100,000")
    
    # Should have field for year-specific population
    self.assertContains(response, "Population (2023/24)")
```

### 3. Regression Tests
```python
def test_existing_views_still_work(self):
    """Ensure all existing views continue to function"""
    # Council detail page
    response = self.client.get(f'/councils/{self.council.slug}/')
    self.assertContains(response, "100,000 residents")
    
    # API endpoint
    response = self.client.get(f'/api/councils/{self.council.slug}/')
    data = response.json()
    self.assertEqual(data['population'], 100000)
    
    # Comparison tool
    response = self.client.get('/api/comparisons/data/')
    # ... etc
```

### 4. Performance Tests
```python
def test_population_queries_optimized(self):
    """Ensure no N+1 queries for population data"""
    with self.assertNumQueries(2):  # One for councils, one for populations
        councils = Council.objects.all()
        for council in councils:
            pop = council.latest_population  # Should use cached value
```

## Rollback Plan

If issues arise:

1. **Phase 1 Rollback**: No changes needed - existing system unchanged
2. **Phase 2 Rollback**: Revert calculation logic to always use latest_population
3. **Phase 3 Rollback**: Hide new UI fields, continue using existing forms

## Success Criteria

1. **No Breaking Changes**: All existing functionality continues to work
2. **Accurate Calculations**: Per capita figures use correct historical population
3. **Clear UI**: Users understand the distinction between current and historical population
4. **Performance**: No degradation in page load times
5. **Data Integrity**: Population data remains consistent across years

## Implementation Status (2025-01-07)

### ✅ Completed:

1. **Created `population_year.py` utility module** (`council_finance/utils/population_year.py`)
   - `get_population_for_year()` - Retrieves year-specific population with fallback
   - `set_population_for_year()` - Sets population for a specific year
   - `get_population_history()` - Gets population trends
   - `calculate_population_change()` - Calculates changes between years

2. **Updated `calculators.py`** to use year-specific population
   - Modified `get_data_context_for_council()` to inject correct population for calculations
   - Maintains backward compatibility with fallback to `latest_population`
   - Per capita calculations now use accurate historical population

3. **Created `populate_historical_population` management command**
   - Populates all historical years with current `latest_population` as baseline
   - Supports dry-run mode and selective processing
   - Successfully migrated data for all councils with population data

4. **Tested implementation**
   - Birmingham City Council confirmed working with 1,141,374 population across all years
   - Year-specific population retrieval working correctly
   - Fallback to `latest_population` confirmed working

### 🔄 Next Steps:

1. **UI Integration** - Update council edit screens to allow year-specific population editing
2. **Site Totals Update** - Update `efficient_site_totals.py` for year-aware aggregations (optional)
3. **Monitor Usage** - Track per capita calculations to ensure accuracy

## Risk Mitigation

1. **Extensive Testing**: Comprehensive test suite before deployment
2. **Gradual Rollout**: Deploy to staging first, monitor for issues
3. **Feature Flag**: Add toggle to revert to old behavior if needed
4. **Monitoring**: Track per capita calculation accuracy
5. **Documentation**: Clear documentation for future developers