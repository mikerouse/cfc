# Emergency Counter Recovery System Removal Plan

**Date**: 2025-08-06  
**Status**: Ready for Implementation  
**Priority**: Medium  

## Context & Analysis

The existing emergency counter recovery system has become **obsolete** due to the implementation of the new proactive cache warming system with "Calculating..." states. The old system was reactive (fix £0 after users see it) while the new system is proactive (prevent £0 from appearing).

### Current Emergency System Components

1. **JavaScript Monitor**: `static/js/homepage-counter-guardian.js` (319 lines)
   - Monitors every 2 seconds for £0 counters
   - Triggers emergency API when detected
   - Shows user notifications and reloads page

2. **Backend API**: `emergency_cache_warming()` in `council_finance/views/api.py` (lines 488-750+)
   - Rate limiting and security measures
   - Runs expensive `SiteTotalsAgent().run()` synchronously
   - Email alerts and Event Viewer logging
   - Comprehensive error handling

3. **URL Endpoint**: `/api/emergency-cache-warming/` in `urls.py` (line 125)

4. **Homepage Integration**: Script tag in `home.html` template

### New Cache Warming System (Replacement)

The new system provides superior functionality:
- **Proactive**: Shows "Calculating..." instead of £0 when cache is cold
- **Rich UX**: Animated spinners, progress bars, smooth transitions
- **Efficient**: 3-tier caching with sentinel values (-1)
- **Real-time**: Live progress updates via `/api/cache-warming/progress/`
- **Connection Resilient**: Database timeout handling
- **Background Processing**: Never blocks page loads

## Removal Plan

### Phase 1: Disable Emergency System ✅ **COMPLETED** (2025-08-06)

**Objective**: Stop emergency system from running while keeping code for rollback

**Steps**:
1. ✅ **Comment out script tag** in homepage template
   - File: `council_finance/templates/council_finance/home.html`
   - Changed: `<script src="{% static 'js/homepage-counter-guardian.js' %}"></script>`
   - To: `<!-- <script src="{% static 'js/homepage-counter-guardian.js' %}"></script> -->`
   - Added comprehensive deprecation comment explaining the change

2. ✅ **Add deprecation comment** to API function
   - File: `council_finance/views/api.py`
   - Added deprecation comment above `emergency_cache_warming()` function:
   ```python
   # DEPRECATED: This emergency system is obsolete due to new proactive cache warming
   # with "Calculating..." states. Scheduled for removal after monitoring period.
   def emergency_cache_warming(request):
   ```

3. **Monitor new system performance** for 1-2 weeks (Starting Now)
   - Check Event Viewer for cache warming events: `/system-events/`
   - Monitor homepage load times and user experience
   - Verify no £0 counters appear to users
   - Test cache warming command: `python manage.py warmup_counter_cache`
   - **Monitoring Period**: August 6-20, 2025

### Phase 2: Remove Emergency System (After 1-2 weeks - Medium Risk)

**Objective**: Completely remove obsolete code after confirming new system works

**Files to Remove/Modify**:

1. **Remove JavaScript File**:
   ```bash
   rm static/js/homepage-counter-guardian.js
   ```

2. **Remove API Function**:
   - File: `council_finance/views/api.py`
   - Remove: `emergency_cache_warming()` function (lines 488-750+)
   - Remove: Related imports if no longer used

3. **Remove URL Pattern**:
   - File: `council_finance/urls.py`
   - Remove: `path("api/emergency-cache-warming/", api_views.emergency_cache_warming, name="emergency_cache_warming"),`

4. **Remove Template Reference**:
   - File: `council_finance/templates/council_finance/home.html`
   - Remove: Commented script tag from Phase 1

### Phase 3: Update Documentation (Final - Low Risk)

**Objective**: Update system documentation to reflect changes

1. **Update CLAUDE.md**: Remove references to emergency system
2. **Update any system docs**: Mention removal in changelog
3. **Add Event Viewer monitoring**: Document new cache warming events

## Benefits of Removal

### User Experience Improvements
- ✅ **No more jarring £0 → notification → reload cycle**
- ✅ **Smooth calculating animations instead of error recovery**
- ✅ **Real-time progress updates during cache warming**
- ✅ **Professional loading states prevent user confusion**

### Performance Improvements
- ✅ **Eliminates 2-second monitoring intervals**
- ✅ **Removes expensive emergency SiteTotalsAgent runs**
- ✅ **Reduces API calls and server load**
- ✅ **Prevents multiple competing cache systems**

### Architectural Benefits
- ✅ **Single cache warming system (instead of two)**
- ✅ **Proactive vs reactive approach**
- ✅ **Better error handling and connection resilience**
- ✅ **Cleaner codebase with less complexity**

## Risk Assessment

### Low Risk
- **Phase 1**: Disabling is easily reversible
- **New system proven**: Already handles calculating states correctly
- **Fallback available**: Can re-enable if needed

### Mitigation Strategies
- **Monitoring period**: 1-2 weeks before permanent removal
- **Event Viewer tracking**: Monitor cache warming success rates
- **Quick rollback**: Uncomment script tag if issues arise
- **Manual warming**: `python manage.py warmup_counter_cache` always available

## Success Criteria

### Immediate (Phase 1) ✅ **COMPLETED**
- [x] Emergency script disabled on homepage
- [x] No JavaScript console errors (emergency script no longer loads)
- [x] Homepage still loads normally (new cache warming system handles calculating states)
- [x] New calculating states work correctly (proactive system prevents £0 display)

### After 1-2 weeks (Phase 2 readiness)
- [ ] No £0 counters observed by users
- [ ] Cache warming system working reliably
- [ ] Homepage performance maintained or improved
- [ ] Event Viewer shows successful cache operations
- [ ] No emergency API calls in logs

### Final (Phase 3)
- [ ] Emergency system code completely removed
- [ ] Documentation updated
- [ ] System architecture simplified
- [ ] User experience improved

## Implementation Commands

### Phase 1 (Disable):
```bash
# Edit template to comment out script
# File: council_finance/templates/council_finance/home.html
# Change: <script src="{% static 'js/homepage-counter-guardian.js' %}"></script>
# To: <!-- <script src="{% static 'js/homepage-counter-guardian.js' %}"></script> -->
```

### Phase 2 (Remove):
```bash
# Remove JavaScript file
rm static/js/homepage-counter-guardian.js

# Edit views/api.py to remove emergency_cache_warming function
# Edit urls.py to remove URL pattern
# Edit home.html to remove commented script tag
```

### Testing Commands:
```bash
# Test new cache warming system
python manage.py warmup_counter_cache --verbose

# Check system health
python manage.py shell -c "
from council_finance.services.counter_cache_service import counter_cache_service
from council_finance.models import SiteCounter

for sc in SiteCounter.objects.filter(promote_homepage=True):
    year_label = sc.year.label if sc.year else None
    try:
        value = counter_cache_service.get_counter_value(
            counter_slug=sc.counter.slug,
            year_label=year_label,
            use_stale_if_needed=False,
            allow_expensive_calculation=False
        )
        print(f'{sc.name}: {\"Calculating\" if value == -1 else f\"£{value:,.2f}\"}')
    except Exception as e:
        print(f'{sc.name}: Error - {e}')
"

# Monitor Event Viewer for cache events
# Visit: /system-events/ and filter by source: counter_cache_service
```

## Conclusion

The emergency counter recovery system can be safely removed as it has been superseded by a superior proactive cache warming system. The new approach prevents the problem rather than reacting to it, providing a much better user experience while reducing server load and architectural complexity.

**Recommendation**: Proceed with Phase 1 immediately, monitor for 1-2 weeks, then complete removal in Phase 2.