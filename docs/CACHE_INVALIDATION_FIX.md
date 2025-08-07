# Counter Cache Invalidation Fix - Implementation Summary

## Problem
When users edit council financial figures through the edit interface, the counter values displayed on the council detail page are not immediately updated. Users have to refresh the page and wait for the cache to expire (10 minutes) to see the updated figures.

## Root Cause
The council detail page caches counter calculations for 10 minutes using cache keys like:
```
counter_values:{council_slug}:{year_label}
```

When financial figures are updated via the edit APIs, this cache is not invalidated, so the display continues to show the old cached values.

## Solution
Added cache invalidation to all API endpoints that save or update financial figures and council characteristics:

### 1. Temporal Data API (`council_edit_api.py` - `save_temporal_data_api`)
- **Location**: Lines 422-425 (after transaction completion)
- **Action**: Invalidates cache for the specific council and year when financial figures are updated
- **Code**: 
```python
cache_key_current = f"counter_values:{council.slug}:{year.label}"
cache.delete(cache_key_current)
```

### 2. Characteristics API (`council_edit_api.py` - `save_council_characteristic_api`)
- **Location**: Lines 150-157 (after transaction completion)
- **Action**: Invalidates cache for all years when characteristics are updated (since characteristics can affect calculations across all years)
- **Code**:
```python
for year in FinancialYear.objects.all():
    cache_key = f"counter_values:{council.slug}:{year.label}"
    cache.delete(cache_key)
```

### 3. Bulk Figure Save API (`general.py` - `council_detail` function)
- **Location**: Lines 958-975 (after save loop completion)
- **Action**: Invalidates cache when bulk figure changes are saved, with special handling for characteristics
- **Code**:
```python
if saved_count > 0:
    cache_key = f"counter_values:{council.slug}:{year.label}"
    cache.delete(cache_key)
    
    # Also handle characteristics changes
    if characteristic_changes:
        for year_obj in FinancialYear.objects.all():
            cache_key_all = f"counter_values:{council.slug}:{year_obj.label}"
            cache.delete(cache_key_all)
```

## Cache Key Consistency
All cache keys use the same format as the existing caching system:
```
counter_values:{council_slug}:{year_label}
```

This matches the cache keys used in the counter display code in `general.py`.

## Transaction Safety
Cache invalidation is performed **after** database transactions are committed to ensure:
1. Database changes are persisted before cache is cleared
2. No race conditions between database writes and cache invalidation
3. Cache is only invalidated for successful saves

## Impact
- ✅ **Immediate UI updates**: Counters now reflect changes immediately after saving
- ✅ **No performance impact**: Cache invalidation is minimal overhead
- ✅ **Backward compatible**: Existing functionality unchanged
- ✅ **Consistent behavior**: All edit endpoints now behave the same way

## Testing
The fix handles all identified edit endpoints:
1. Individual financial figure updates (React edit interface)
2. Council characteristic updates
3. Bulk figure saves (legacy edit interface)

Users will now see counter updates immediately after saving any financial data, eliminating the need to refresh the page or wait for cache expiration.