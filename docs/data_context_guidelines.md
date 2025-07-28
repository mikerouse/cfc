# Data Context and Field Naming Guidelines

This document outlines best practices for maintaining data consistency and preventing issues like the `characteristics`/`characteristic` key mismatch we encountered.

## Data Context Structure

### Standard Schema

All data context dictionaries returned by `get_data_context_for_council()` and similar functions must follow this schema:

```python
{
    'council_name': str,        # Council display name
    'council_slug': str,        # Council URL slug
    'year_label': str | None,   # Financial year label (if applicable)
    'characteristic': dict,     # Council characteristics (SINGULAR)
    'financial': dict,          # Financial figures by field
    'calculated': dict,         # Calculated field values
}
```

### ⚠️ Critical: Use 'characteristic' (singular)

**ALWAYS use `'characteristic'` (singular), never `'characteristics'` (plural)**

```python
# ✅ CORRECT
context['characteristic']['population'] = "100000"

# ❌ WRONG - will break figure_map creation
context['characteristics']['population'] = "100000"
```

### Field Name Consistency

Field references must be consistent between slugs and variable names:

- **Slugs**: Use hyphens (`total-debt`, `council-tax-income`)
- **Variable names**: Use underscores (`total_debt`, `council_tax_income`)
- **Conversion**: Always use `FieldNamingValidator.slug_to_variable_name()`

```python
# ✅ CORRECT conversion
from council_finance.utils.field_naming import FieldNamingValidator

slug = "non-ring-fenced-grants"
variable_name = FieldNamingValidator.slug_to_variable_name(slug)
# variable_name = "non_ring_fenced_grants"
```

## Adding New Fields and Characteristics

### 1. Field Creation Checklist

When adding new data fields:

- [ ] Use lowercase slugs with hyphens
- [ ] Validate slug with `FieldNamingValidator.validate_field_slug()`
- [ ] Ensure slug doesn't contain reserved words
- [ ] Test both slug and variable name formats work in formulas
- [ ] Add to appropriate category (`characteristic`, `financial`, `calculated`)

### 2. Formula Development

When creating formulas that reference fields:

- [ ] Use `FormulaFieldExtractor.extract_field_references()` to validate
- [ ] Test with both hyphenated and underscore field names
- [ ] Use `FormulaEvaluator` instead of AST parsing for hyphenated names
- [ ] Verify all referenced fields exist in target data context

### 3. Data Context Functions

When creating functions that return data contexts:

- [ ] Use `@validate_data_context_decorator` for automatic validation
- [ ] Follow the standard schema exactly
- [ ] Use `'characteristic'` (singular) for council characteristics
- [ ] Include debug logging with `log_data_context_usage()`
- [ ] Test with the integration test suite

## Testing Requirements

### 1. Data Context Tests

All new data context functions must include tests:

```python
def test_my_data_context_function(self):
    context = my_data_context_function(council, year)
    
    # Validate schema
    errors = DataContextValidator.validate_data_context(context, "test")
    self.assertEqual(errors, [])
    
    # Check key structure
    self.assertIn('characteristic', context)  # singular!
    self.assertNotIn('characteristics', context)  # no plural!
```

### 2. Field Naming Tests

Test field name conversions:

```python
def test_field_naming(self):
    slug = "my-new-field"
    var_name = FieldNamingValidator.slug_to_variable_name(slug)
    self.assertEqual(var_name, "my_new_field")
    
    # Test round-trip conversion
    back_to_slug = FieldNamingValidator.variable_name_to_slug(var_name)
    self.assertEqual(back_to_slug, slug)
```

### 3. Formula Validation Tests

Test formulas with new fields:

```python
def test_formula_with_new_field(self):
    from council_finance.views.admin import preview_counter_value
    
    # Test hyphenated field in formula
    response = preview_counter_value(request_with_formula)
    self.assertEqual(response.status_code, 200)
```

## Error Prevention Measures

### 1. Runtime Monitoring

Set up automated monitoring:

```bash
# Run daily data quality checks
python manage.py monitor_data_quality --sample-size=20 --send-alerts
```

### 2. Development Validation

Use validation decorators:

```python
from council_finance.utils.data_context_validator import validate_data_context_decorator

@validate_data_context_decorator
def my_context_function(council, year):
    # Function automatically validates return value
    return context
```

### 3. Pre-commit Hooks

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: test-data-context
      name: Test Data Context Consistency
      entry: python manage.py test council_finance.tests.test_data_context_consistency
      language: system
      pass_filenames: false
```

## Common Pitfalls

### 1. Key Naming Inconsistency
```python
# ❌ WRONG - mixing singular and plural
context['characteristic'] = {}
context['characteristics'] = {}  # Don't do this!

# ✅ CORRECT - consistent singular
context['characteristic'] = {}
```

### 2. Field Name Format Mixing
```python
# ❌ WRONG - inconsistent formats
context['financial']['total-debt'] = value  # hyphenated
variables['total_debt'] = value              # underscore

# ✅ CORRECT - consistent underscore for variables
field_name = field.slug.replace('-', '_')
context['financial'][field_name] = value
variables[field_name] = value
```

### 3. Missing Validation
```python
# ❌ WRONG - no validation
def get_context():
    return {'some': 'data'}

# ✅ CORRECT - with validation
@validate_data_context_decorator
def get_context():
    return {
        'council_name': council.name,
        'characteristic': {},
        'financial': {},
        'calculated': {}
    }
```

## Debugging Data Issues

### 1. Enable Debug Mode

Add `?debug=true` to preview requests for detailed context info:

```javascript
// In JavaScript
const url = new URL('/preview/');
url.searchParams.append('debug', 'true');
```

### 2. Check Data Context Structure

```python
from council_finance.calculators import get_data_context_for_council
from council_finance.utils.data_context_validator import DataContextValidator

context = get_data_context_for_council(council, year)
errors = DataContextValidator.validate_data_context(context)
print("Validation errors:", errors)
print("Available fields:", DataContextValidator.get_all_field_keys(context))
```

### 3. Monitor Data Quality

```bash
# Check for consistency issues
python manage.py monitor_data_quality --verbose

# Run comprehensive tests
python manage.py test council_finance.tests.test_data_context_consistency
```

## Migration Guidelines

When updating existing code to follow these guidelines:

1. **Audit existing functions** that return data contexts
2. **Search for `'characteristics'`** (plural) and replace with `'characteristic'`
3. **Update tests** to validate new schema
4. **Add monitoring** to catch future regressions
5. **Document changes** in commit messages

## Summary

The key lessons from the `characteristics`/`characteristic` bug:

1. **Consistency is critical** - small naming differences cause silent failures
2. **Validation prevents bugs** - automated checks catch issues early  
3. **Testing is essential** - integration tests prevent regressions
4. **Monitoring catches issues** - runtime validation alerts to problems
5. **Documentation guides development** - clear guidelines prevent mistakes

Following these guidelines will help maintain a robust, consistent data system as we continue adding new fields and characteristics.
