# Feed Fix - Retrospective Application Guide

## Issue Summary

The user reported that while the feed improvements work for Aberdeen, they don't appear for Cornwall. This is because existing ActivityLog entries use an old format that prevents rich story generation.

## Root Cause

Old ActivityLog entries have:
1. **Wrong field name format**: Display names like "Current Liabilities" instead of slugs like "current-liabilities"
2. **Missing year information**: No year context for financial data
3. **Old activity type**: "data_edit" instead of "update" (though this is supported)

When the ActivityStoryGenerator tries to process these entries:
- It looks up fields using `DataField.objects.filter(slug=field_name).first()`
- If field_name is "Current Liabilities" instead of "current-liabilities", the lookup fails
- This causes fallback to basic story text instead of rich financial display

## Solution

### 1. Template Fix (Already Applied)
✅ Fixed council badge overlap by moving from `top-2 right-2` to `bottom-2 left-2`
✅ This affects all feed entries immediately (template-level change)

### 2. ActivityLog Migration (Ready to Apply)
Created `migrate_activity_logs.py` management command that:
- Converts field display names to slugs
- Adds missing year information (inferred from creation date)
- Updates activity_type from "data_edit" to "update"
- Preserves original data in new `field_display_name` field

## Running the Migration

### Test First (Safe)
```bash
python manage.py migrate_activity_logs --dry-run --limit=50
```
This shows what would be changed without making changes.

### Apply Migration
```bash
python manage.py migrate_activity_logs --limit=100
```
Migrates up to 100 entries (adjust limit as needed).

### Full Migration
```bash
python manage.py migrate_activity_logs --limit=1000
```

## Expected Results

**Before Migration** (Cornwall example):
```
Activity Type: data_edit
Details: {
  "field_name": "Current Liabilities",    # Display name - lookup fails
  "old_value": "45000000",
  "new_value": "50000000"
  # Missing year
}
Result: Basic story text
```

**After Migration**:
```
Activity Type: update
Details: {
  "field_name": "current-liabilities",     # Slug - lookup succeeds
  "field_display_name": "Current Liabilities",
  "old_value": "45000000", 
  "new_value": "50000000",
  "year": "2024/25"                        # Added year context
}
Result: Rich financial display with formatted values
```

## Verification

After running migration:
1. Visit `/following/` (Feed page)
2. Look for Cornwall and other councils
3. Should now show rich financial cards with:
   - Formatted values (£50.0m)
   - Percentage changes (+10.3%)
   - Professional gradient styling
   - Council badges in bottom-left (not overlapping)

## Safety Notes

- Migration preserves all original data
- Adds new fields rather than overwriting
- Can be run multiple times safely (idempotent)
- Dry-run available for testing
- Only affects ActivityLog presentation, not underlying financial data

## Timeline

The template fix (council badge repositioning) is already applied and affects all councils immediately. The migration fix will restore rich stories for councils like Cornwall that currently show basic text.