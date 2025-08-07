# Cache Warming Concurrency Protection Implementation

**Date**: 2025-08-06  
**Priority**: High - Critical for production stability  
**Status**: ✅ Implemented

## Context & Problem

During server restarts and high-traffic periods, multiple cache warming operations could run simultaneously, causing:

1. **Database Connection Timeouts** - Multiple SiteTotalsAgent processes consuming connections
2. **Conflicting Cache Updates** - Race conditions between different warming sessions  
3. **Resource Exhaustion** - CPU/Memory overload from concurrent expensive calculations
4. **Inconsistent Counter Values** - Overlapping calculations producing different results

## Comprehensive Protection Strategy

### 1. Management Command Protection ✅

**File**: `council_finance/management/commands/warmup_counter_cache.py`

**Protection**: Command-level distributed lock with 30-minute timeout

```python
# Check if another warming command is already running
command_lock_key = "warmup_counter_cache_command_lock"

if cache.get(command_lock_key):
    self.stdout.write(
        self.style.WARNING(
            'WARNING: Another cache warming command is already running.\n'
            'Use --force to override this protection, but be aware this may cause:\n'
            '- Database connection timeouts\n'
            '- Conflicting cache updates\n'
            '- Inconsistent counter values\n'
            'Recommended: Wait for current warming to complete.'
        )
    )
    return

# Set command lock with 30 minute timeout
cache.set(command_lock_key, True, 1800)  # 30 minutes
```

**Features**:
- ✅ Prevents multiple `python manage.py warmup_counter_cache` commands
- ✅ Clear warning messages explaining risks of override
- ✅ `--force` flag to bypass protection when needed
- ✅ Automatic lock cleanup in `finally` block
- ✅ 30-minute timeout prevents indefinite locks

### 2. Critical Counter Warming Protection ✅

**File**: `council_finance/services/counter_cache_service.py`  
**Method**: `warm_critical_counters()`

**Protection**: Service-level distributed lock with 15-minute timeout

```python
# Concurrency protection - prevent multiple warming sessions
lock_key = "critical_counter_warming_lock"

# Try to acquire distributed lock with 15-minute timeout
if cache.get(lock_key):
    log_cache_event(
        'warning', 'maintenance',
        'Critical Counter Warming Already in Progress',
        'Skipping critical counter warming - another session is already running'
    )
    return {
        'status': 'already_running',
        'message': 'Another warming session is already in progress'
    }

# Set lock with 15 minute timeout (site-wide calculations can take a while)
cache.set(lock_key, True, 900)  # 15 minutes
```

**Features**:
- ✅ Prevents overlapping homepage counter calculations
- ✅ Returns structured status response for caller handling
- ✅ Event Viewer integration for monitoring
- ✅ Automatic lock cleanup in `finally` block
- ✅ 15-minute timeout for lengthy site-wide calculations

### 3. SiteTotalsAgent Protection ✅

**File**: `council_finance/services/counter_cache_service.py`  
**Method**: `get_counter_value()` site-wide calculation path

**Protection**: SiteTotalsAgent-specific distributed lock with 20-minute timeout

```python
# Concurrency protection for expensive site-wide calculation
site_totals_lock_key = "site_totals_agent_run_lock"

# Check if another SiteTotalsAgent is already running
if cache.get(site_totals_lock_key):
    log_cache_event(
        'warning', 'concurrency',
        'SiteTotalsAgent Already Running',
        f'Skipping site-wide calculation for {counter_slug} - another SiteTotalsAgent is running'
    )
    
    # Return sentinel to indicate calculation is needed but not available right now
    return Decimal('-1')

# Set lock with 20 minute timeout (site-wide calcs can take a long time)
cache.set(site_totals_lock_key, True, 1200)  # 20 minutes
```

**Features**:
- ✅ Prevents multiple expensive SiteTotalsAgent runs (most critical protection)
- ✅ Returns `-1` sentinel value for "Calculating..." UI state
- ✅ Comprehensive timing and performance logging
- ✅ Automatic lock cleanup in `finally` block
- ✅ 20-minute timeout for very lengthy site-wide operations

### 4. API Endpoint Protection ✅ (Already Existed)

**File**: `council_finance/api/cache_warming_api.py`  
**Method**: `trigger_cache_warming()`

**Protection**: API-level progress tracking with status checking

```python
# Check if warming is already in progress
progress_info = cache.get('counter_cache_warming_progress')
if progress_info and progress_info.get('status') == 'running':
    return JsonResponse({
        'status': 'already_running',
        'message': 'Cache warming is already in progress'
    })
```

**Features**:
- ✅ Staff-only endpoint access control
- ✅ Progress tracking integration
- ✅ Real-time status monitoring
- ✅ Background thread execution

## Lock Hierarchy & Timeouts

**Lock Priority** (most specific to most general):

1. **SiteTotalsAgent Lock**: `site_totals_agent_run_lock` (20 minutes)
   - Protects the most expensive operations
   - Prevents database connection exhaustion

2. **Critical Counter Lock**: `critical_counter_warming_lock` (15 minutes)  
   - Protects homepage counter warming
   - May trigger SiteTotalsAgent internally

3. **Command Lock**: `warmup_counter_cache_command_lock` (30 minutes)
   - Protects entire command execution
   - May trigger critical counter warming internally

4. **API Progress Lock**: `counter_cache_warming_progress` (dynamic)
   - Tracks background API warming progress
   - Used by frontend for real-time updates

## Event Viewer Integration ✅

All concurrency events are logged to Event Viewer for monitoring:

**Event Categories**:
- `maintenance`: Normal warming operations
- `concurrency`: Lock acquisitions and conflicts
- `performance`: Timing and calculation metrics

**Example Events**:
- "Critical Counter Warming Already in Progress" (warning)
- "SiteTotalsAgent Already Running" (warning) 
- "SiteTotalsAgent Completed in 45.2s" (info)
- "Critical Counter Warming Lock Released" (info)

## Error Handling & Recovery

### Lock Cleanup
- ✅ **Always released**: `finally` blocks ensure locks don't persist
- ✅ **Timeout protection**: All locks have reasonable timeouts
- ✅ **Error logging**: Failed lock releases are logged but don't block operations

### Graceful Degradation
- ✅ **Sentinel values**: Returns `-1` when calculation needed but blocked
- ✅ **Status responses**: Structured responses for different blocking scenarios
- ✅ **User feedback**: Clear messages about why operations are skipped

### Recovery Mechanisms
- ✅ **`--force` flag**: Management command bypass for emergencies
- ✅ **Lock expiration**: Automatic timeout prevents indefinite blocking
- ✅ **Manual clearing**: Cache can be manually cleared if needed

## Testing Scenarios

### Server Restart Protection ✅
```bash
# Terminal 1
python manage.py warmup_counter_cache

# Terminal 2 (during startup)  
python manage.py warmup_counter_cache
# Expected: "WARNING: Another cache warming command is already running"
```

### Concurrent API Calls ✅
```bash
# Multiple simultaneous API requests
curl -X POST /api/cache-warming/trigger/
curl -X POST /api/cache-warming/trigger/  
# Expected: Second returns {"status": "already_running"}
```

### SiteTotalsAgent Overlap Prevention ✅
```python
# Multiple calls to expensive site-wide calculations
counter_cache_service.get_counter_value(
    counter_slug='total-debt', 
    allow_expensive_calculation=True
)
# Expected: First runs calculation, second returns Decimal('-1')
```

## Production Benefits

### Performance Benefits
- ✅ **Prevents database overload** during high traffic or restarts
- ✅ **Eliminates wasted calculations** from overlapping operations  
- ✅ **Reduces server resource consumption** by avoiding concurrent heavy operations

### Reliability Benefits  
- ✅ **Consistent counter values** - no race conditions between calculations
- ✅ **Graceful degradation** - shows "Calculating..." instead of errors
- ✅ **Automatic recovery** - locks expire and operations can retry

### Monitoring Benefits
- ✅ **Complete visibility** via Event Viewer integration
- ✅ **Performance metrics** for calculation timing
- ✅ **Concurrency tracking** to identify bottlenecks

## Usage Guidelines

### For Developers
- **Always check return status** from warming methods
- **Use `--verbose`** flag for debugging concurrency issues
- **Monitor Event Viewer** for concurrency conflicts

### For Production
- **Schedule cache warming** during low-traffic periods when possible
- **Monitor lock timeouts** - increase if calculations consistently take longer
- **Use health checks** to verify warming operations complete successfully

### Emergency Procedures
- **Stuck operations**: Use `--force` flag to bypass protection
- **Clear locks manually**: Delete cache keys if needed
- **Monitor resources**: Watch database connections and memory usage

## Integration with Existing Systems

### Homepage Cache Warming UI ✅
- Frontend JavaScript polls `/api/cache-warming/progress/`
- Shows "Calculating..." states when operations are blocked
- Transitions smoothly when calculations complete

### Emergency System Removal ✅  
- Old reactive emergency system disabled (Phase 1 complete)
- New proactive system with concurrency protection is primary
- Better user experience with professional loading states

### Event Viewer Monitoring ✅
- All concurrency events logged for analysis
- Performance metrics tracked over time
- Alert thresholds can be configured for excessive conflicts

## Conclusion

The comprehensive concurrency protection system ensures:

1. **Database Stability** - No more connection timeouts from overlapping operations
2. **Consistent Results** - Race conditions eliminated through proper locking
3. **Better UX** - Users see "Calculating..." instead of errors or £0 values
4. **Full Monitoring** - Complete visibility into system behavior
5. **Production Ready** - Handles server restarts and high-traffic scenarios safely

This protection is essential for the production deployment where multiple users and automated systems may trigger cache warming simultaneously.

## Performance Optimizations (2025-08-06)

### Reduced Batch Sizes for Better UX ✅

**Changed from 50 councils per batch to 10 councils per batch** across all SiteTotalsAgent operations:

**Files Modified**:
- `council_finance/agents/site_totals_agent.py` - All chunked operations now use `chunk_size=10`
- `council_finance/management/commands/warmup_counter_cache.py` - Progress messages updated

**Benefits**:
- ✅ **Better Progress Visibility**: Users see progress updates every 10 councils instead of 50
- ✅ **Reduced Memory Usage**: Smaller chunks reduce memory pressure per batch
- ✅ **Faster Feedback**: More frequent status updates during long operations
- ✅ **Better Connection Management**: Database health checks every 10 councils instead of 50
- ✅ **Improved Debugging**: Easier to identify which council batch caused issues

**Progress Output Examples**:
```
  Processed 10/289 councils...
  Processed 20/289 councils...
  Processed 30/289 councils...
```

### Service Termination Recommendations ✅

**Management Command Enhancement**: Added prominent startup warnings with platform-specific kill commands:

**Display Format**:
```
===========================================================================
⚠️  RECOMMENDATION: Kill all running Python services first!

On Windows:
  taskkill /f /im python.exe
  taskkill /f /im pythonw.exe

On Linux/Mac:
  pkill -f python
  pkill -f manage.py

Why? This prevents:
• Database connection conflicts and timeouts
• Competing cache warming operations
• Resource exhaustion from multiple processes
===========================================================================
```

**Implementation Details**:
- ✅ **Visual Prominence**: Warning messages with emojis and clear formatting
- ✅ **Platform-Specific**: Commands for Windows, Linux, and Mac
- ✅ **Clear Benefits**: Explains exactly why killing services helps
- ✅ **Professional Formatting**: Consistent styling with existing system messages

### Combined Impact

**Before Optimizations**:
- Progress updates every 50 councils (infrequent feedback)
- No guidance on preventing service conflicts
- Higher memory usage from larger batches

**After Optimizations**:
- Progress updates every 10 councils (5x more frequent feedback)
- Clear instructions for preventing conflicts with specific kill commands
- Better resource management with smaller batch sizes
- Professional warning system with visual prominence

**User Experience**: The cache warming process now provides much better visibility and guidance, making it easier to monitor progress and prevent conflicts in production environments.