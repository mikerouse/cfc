# Financial Data Storage Formats

**CRITICAL**: This document explains how financial data is stored and formatted in the system. **READ THIS** before adding new financial fields or modifying counter logic.

## Current Data Storage Inconsistency

Due to historical development, financial data is stored in **two different formats**:

### 1. Legacy Financial Statement Fields (Stored in Millions)
These fields from balance sheets and income statements were stored as millions:
- `business-rates-income`: 208.49 (represents £208.49 million)
- `non-ring-fenced-government-grants-income`: 260.85 (represents £260.85 million)

### 2. Modern Financial Fields (Stored in Pounds)  
These fields are stored as actual pound amounts:
- `current-liabilities`: 644130000.00 (represents £644,130,000)
- `council-tax-income`: 143678000.00 (represents £143,678,000)
- `usable-reserves`: 153607000.00 (represents £153,607,000)

## Smart Detection System

The `CounterDefinition.format_value()` method handles this inconsistency with **context-aware detection**:

```python
# Only these confirmed fields get millions-to-pounds conversion
financial_statement_fields = {
    'business-rates-income',
    'non-ring-fenced-government-grants-income', 
    # Add others here only when confirmed
}

if uses_millions_data and abs(value) < 1000:
    actual_value_in_pounds = value * 1_000_000  # Convert millions to pounds
else:
    actual_value_in_pounds = value  # Use as-is (already pounds)
```

## 🚨 CRITICAL: Adding New Financial Fields

### DO NOT rely on magnitude detection
**NEVER** assume that values < 1000 = millions. This breaks for legitimate small amounts:
- Office supplies: £38.25 ❌ would become £38,250,000
- Parking fees: £150.00 ❌ would become £150,000,000

### FOR NEW FIELDS: Use Pounds Only
```python
# ✅ CORRECT: Store in pounds
FinancialFigure.objects.create(
    field=office_supplies_field,
    value=38.25,  # £38.25
    council=council,
    year=year
)

# ❌ WRONG: Don't use millions for new fields
# value=0.038  # This would be confusing and inconsistent
```

### IF adding a legacy import that uses millions:
1. **Document the field** in the `financial_statement_fields` set in `counter.py`
2. **Convert to pounds** in the import process, don't rely on format detection
3. **Add tests** to verify the conversion works correctly

## Migration Plan

### Long-term Goal: Pounds-Only Storage
We plan to eliminate the dual-format system:

1. **Phase 1**: Convert remaining millions-stored fields to pounds
2. **Phase 2**: Remove the smart detection logic  
3. **Phase 3**: All new fields use pounds consistently

### Data Migration Template
```python
# Example migration for converting millions to pounds
def convert_millions_to_pounds(field_slug):
    figures = FinancialFigure.objects.filter(field__slug=field_slug)
    for figure in figures:
        if figure.value and figure.value < 1000:  # Likely in millions
            figure.value = figure.value * 1_000_000
            figure.save()
```

## Counter Formatting Logic

### Current System
```python
# CounterDefinition.format_value() handles:
# 1. Context detection (which fields use millions)
# 2. Conversion to pounds
# 3. Friendly formatting (£1m, £1.5b, etc.)

def format_value(self, value):
    # Smart detection only for confirmed financial statement fields
    if uses_millions_data and abs(value) < 1000:
        actual_value = value * 1_000_000
    else:
        actual_value = value  # Already in pounds
        
    # Apply friendly formatting
    if self.friendly_format:
        if actual_value >= 1_000_000:
            return f"£{actual_value / 1_000_000:.1f}m"
        # ... etc
```

### Future System (Post-Migration)
```python
# Once all data is in pounds, this becomes simple:
def format_value(self, value):
    if self.friendly_format:
        if value >= 1_000_000:
            return f"£{value / 1_000_000:.1f}m"
        # ... etc
```

## Testing New Financial Fields

### Required Tests
```python
def test_new_field_formatting():
    # Test that small amounts stay small
    field = FinancialFigure.objects.create(
        field=office_supplies_field,
        value=38.25,  # £38.25
    )
    
    counter = CounterDefinition.objects.create(
        formula='(office-supplies)',
        friendly_format=True
    )
    
    # Should format as £38.25, NOT £38.3m
    assert counter.format_value(38.25) == "£38.25"
    assert "38.3m" not in counter.format_value(38.25)
```

## Key Rules for Developers

### ✅ DO:
- Store all new financial data in pounds
- Add comprehensive tests for formatting logic
- Document any legacy fields that need millions conversion
- Use the `financial_statement_fields` set for confirmed millions-stored fields

### ❌ DON'T:
- Assume magnitude-based detection will work for your field
- Store new data in millions format
- Modify the detection logic without updating this documentation
- Add fields to `financial_statement_fields` unless confirmed they're stored in millions

## Questions?

If you're unsure about a field's format:
1. Check the raw database values
2. Look for existing counter definitions using that field
3. Test with known values to verify the expected output
4. Update this documentation with your findings

**When in doubt, assume pounds and test thoroughly.**