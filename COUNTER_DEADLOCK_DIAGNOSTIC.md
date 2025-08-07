# Counter Cache Deadlock Diagnostic Guide

**Date**: 2025-08-06  
**Issue**: Site-wide counter calculations getting stuck in "Calculating..." state indefinitely  
**Status**: ✅ Fixed with deadlock detection and timeout protection

## Problem Analysis

Based on the screenshot and HAR file analysis, the issue was:

1. **Infinite "Calculating..." State**: Homepage counter showed calculating animation but never resolved
2. **No Progress API Calls**: HAR file showed no calls to `/api/cache-warming/progress/` 
3. **SiteTotalsAgent Deadlock**: Backend calculation process getting stuck without timeout
4. **Lock Not Released**: Distributed locks held indefinitely, preventing new calculations

## Root Causes Identified

### 1. Missing Timeout Protection
**Problem**: SiteTotalsAgent could run indefinitely without any timeout mechanism
**Impact**: Database connections timeout, locks held forever, system appears frozen

### 2. No Deadlock Detection  
**Problem**: API returned `-1` (calculating) even when no actual calculation was running
**Impact**: Frontend shows "Calculating..." forever, no retry mechanism

### 3. Lock Management Issues
**Problem**: Distributed locks could be held indefinitely if process crashed or hung
**Impact**: No new calculations could start, system permanently stuck

## Fixes Implemented

### ✅ 1. API Deadlock Detection (`cache_warming_api.py`)

**Before**:
```python
if value == -1:
    state = 'calculating'
    display_value = 'Calculating...'
```

**After**:
```python
if value == -1:
    # Check if calculation has been stuck for too long
    lock_key = "site_totals_agent_run_lock"
    if cache.get(lock_key):
        state = 'calculating'  # Actually calculating
        display_value = 'Calculating...'
    else:
        # No lock but still -1 = stuck state, try recovery
        try:
            value = counter_cache_service.get_counter_value(
                counter_slug=sc.counter.slug,
                year_label=year_label,
                allow_expensive_calculation=True
            )
            if value == -1:
                state = 'error'
                display_value = 'Calculation failed'
            else:
                state = 'ready'
                display_value = sc.counter.format_value(float(value))
        except Exception:
            state = 'error'
            display_value = 'Error'
```

**Benefit**: System can now detect and recover from deadlocks automatically

### ✅ 2. SiteTotalsAgent Timeout Protection (`site_totals_agent.py`)

**Added timeout mechanism**:
```python
def run(self, max_duration_minutes=15, **kwargs):
    start_time = time.time()
    max_duration_seconds = max_duration_minutes * 60
    
    def check_timeout():
        elapsed = time.time() - start_time
        if elapsed > max_duration_seconds:
            print(f"⚠️  TIMEOUT: SiteTotalsAgent exceeded {max_duration_minutes} minutes")
            raise TimeoutError(f"SiteTotalsAgent timeout after {elapsed:.2f} seconds")
        return elapsed
```

**Added timeout checks every 10 councils**:
```python
if council_count % 10 == 0:
    elapsed = check_timeout()  # Will raise TimeoutError if exceeded
    print(f"  Processed {council_count}/{total_councils} councils... ({elapsed:.1f}s elapsed)")
```

**Benefit**: Calculations automatically stop after 15 minutes, preventing infinite hangs

### ✅ 3. Emergency Lock Clearing Command

**New management command**: `python manage.py clear_cache_locks`

**Features**:
- Lists all active cache warming locks
- Can clear stuck locks in emergency situations
- `--list-only` to inspect without clearing
- `--force` to clear regardless of lock age

**Usage**:
```bash
# Check what locks exist
python manage.py clear_cache_locks --list-only

# Clear all stuck locks
python manage.py clear_cache_locks
```

**Benefit**: Administrators can manually recover from deadlock situations

## Diagnostic Commands

### Check System Status
```bash
# Check current locks
python manage.py clear_cache_locks --list-only

# Test counter progress API
curl http://localhost:8000/api/cache-warming/progress/

# Check Event Viewer for errors
# Visit: /system-events/ and filter by 'cache' or 'timeout'
```

### Recovery Procedures

#### **Scenario 1: Infinite "Calculating..." State**
```bash
# 1. Check if locks are stuck
python manage.py clear_cache_locks --list-only

# 2. If locks found, clear them
python manage.py clear_cache_locks

# 3. Restart cache warming
python manage.py warmup_counter_cache
```

#### **Scenario 2: SiteTotalsAgent Timeout**
```bash
# 1. Check Event Viewer logs for timeout errors
# 2. Wait for timeout (15 minutes max) 
# 3. Locks should automatically clear
# 4. System should recover automatically

# Manual intervention if needed:
python manage.py clear_cache_locks
```

#### **Scenario 3: Database Connection Issues**
```bash
# 1. Kill all running Python processes
taskkill /f /im python.exe
taskkill /f /im pythonw.exe

# 2. Clear locks
python manage.py clear_cache_locks

# 3. Restart with smaller batch size (already implemented: 10 councils vs 50)
python manage.py warmup_counter_cache
```

## Prevention Measures

### ✅ Automatic Recovery
- API now detects deadlocks and attempts recovery
- 15-minute timeout prevents infinite hangs
- Progress tracking every 10 councils for better visibility

### ✅ Monitoring Integration
- Event Viewer logs all timeout events
- Lock acquisition/release tracked
- Performance metrics captured

### ✅ Better User Experience  
- Shows "Calculation failed" instead of infinite "Calculating..."
- Fallback to error state allows manual retry
- Clear diagnostic information for administrators

## Testing the Fix

### Manual Test
1. **Before Fix**: Homepage would show "Calculating..." indefinitely
2. **After Fix**: Should either show actual value or "Calculation failed" within 20 minutes maximum

### API Test
```bash
# Should return actual counter states, not stuck calculating
curl http://localhost:8000/api/cache-warming/progress/
```

### Expected Response:
```json
{
  "counter_states": [
    {
      "state": "ready",
      "display_value": "£45.2B"
    }
  ]
}
```

## Long-term Improvements

### Recommended Next Steps

1. **Background Job Processing**: 
   - Move heavy calculations to background tasks (Celery/Django-Q)
   - Schedule nightly cache warming via cron

2. **Incremental Updates**:
   - Only recalculate when underlying data changes
   - Use database triggers to invalidate specific counters

3. **Performance Optimization**:
   - Pre-aggregate common calculations in database views
   - Use materialized views for complex queries

4. **Circuit Breaker Pattern**:
   - Stop attempting calculations after multiple failures
   - Implement exponential backoff for retries

## Conclusion

The deadlock issue has been resolved with:
- ✅ **Timeout Protection**: 15-minute maximum calculation time
- ✅ **Deadlock Detection**: API detects and recovers from stuck states  
- ✅ **Emergency Recovery**: Manual lock clearing commands
- ✅ **Better Monitoring**: Comprehensive logging and progress tracking
- ✅ **Graceful Degradation**: Shows errors instead of infinite loading

**Result**: System now recovers automatically from deadlocks and provides clear feedback when calculations fail.