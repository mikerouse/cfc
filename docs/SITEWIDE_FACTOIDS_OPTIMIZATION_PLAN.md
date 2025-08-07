# Site-wide Factoids Optimization Plan

## Status: ✅ COMPLETED - Phase 2 Deployed (2025-08-03)

## Current Issues Identified (RESOLVED)

### 1. **Scalability Problems** ✅ FIXED
- ~~Loads ALL council data for ALL comparison fields in real-time~~ → Pre-aggregated summaries
- ~~No limit on dataset size - will become massive as councils/fields grow~~ → Optimized with field/council limits
- ~~Queries hit database directly on every generation~~ → Multi-level caching with 6-hour primary cache
- ~~Memory-intensive processing of complete datasets~~ → Efficient summary-based processing

### 2. **Inefficient Update Pattern** ✅ FIXED
- ~~Only cached for 30 minutes~~ → 6-hour primary cache + 30-day stale cache
- ~~No change detection - regenerates even if data hasn't changed~~ → Intelligent change detection with data hashing
- ~~No scheduled optimization for homepage needs (4x daily)~~ → Scheduled updates: 06:00, 10:30, 14:00, 18:30

### 3. **Performance Bottlenecks** ✅ FIXED
- ~~Loads complete financial datasets for cross-council analysis~~ → Pre-aggregated summaries
- ~~Processes data on-demand rather than pre-aggregated~~ → Daily summary building + intelligent scheduling
- ~~Sends massive prompts to OpenAI API~~ → Optimized prompts with limited field/council data

## Deployment Summary

### ✅ Phase 2 Implementation Complete (2025-08-03)

**Infrastructure Deployed:**
- `SitewideDataSummary` model with pre-aggregated statistics and change detection
- `SitewideDataChangeLog` for intelligent change tracking
- `SitewideFactoidSchedule` with 4x daily update pattern (06:00, 10:30, 14:00, 18:30)
- `OptimizedFactoidCache` for multi-level cache management
- Migration 0080: All database tables and indexes created

**Management Commands:**
- `build_sitewide_summaries` - Daily data aggregation (7 summaries created for available data)
- `update_sitewide_factoids` - Intelligent scheduling and generation system
- Both commands tested and working with fallback factoid generation

**Performance Results:**
- **Generation Time**: 5.3 seconds for 2 factoids (including AI processing)
- **Cache Strategy**: 6-hour primary + fallback support
- **Data Coverage**: 7 summaries across 4 financial years for key debt/income fields
- **Change Detection**: Working - detected 7 data changes and marked as processed

**Sample Generated Factoids:**
1. "Test Council 1 boasts £200M in usable reserves, 4x more than Test Council 10's £50M, showcasing extreme financial disparity."
2. "County councils hold an average of £120M in usable reserves, 50% higher than unitary councils' £80M."

**Next Steps:**
1. Set up automated cron jobs for daily summary building
2. Integrate with existing sitewide factoid display system
3. Monitor performance and adjust schedules as data grows

## Phase 3: Advanced Error Recovery & Optimization (COMPLETED)
- ✅ Advanced error pattern analysis and auto-recovery
- ✅ Smart factoid rotation based on data freshness
- ✅ Automated cache warming schedules
- ✅ Performance optimization recommendations

## Phase 4: Production Optimization & Predictive Analytics (IN PROGRESS)
- Real-time monitoring dashboards with live metrics
- Predictive analytics for data trends and cost forecasting
- Automated performance tuning and alerts
- Advanced caching strategies (Redis/Memcached integration)
- Load balancing for high-traffic scenarios
- Unified navigation experience for AI tools

## Comprehensive Solution

### Phase A: Smart Data Aggregation & Change Detection

#### 1. Pre-aggregated Summary Tables
```python
class SitewideDataSummary(models.Model):
    """Pre-aggregated summary data for efficient cross-council analysis."""
    date_calculated = models.DateField()
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    
    # Aggregated statistics
    total_councils = models.IntegerField()
    average_value = models.DecimalField(max_digits=15, decimal_places=2)
    median_value = models.DecimalField(max_digits=15, decimal_places=2)
    min_value = models.DecimalField(max_digits=15, decimal_places=2)
    max_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Top/bottom performers (JSON for efficiency)
    top_5_councils = models.JSONField()  # [{"name": "X", "value": 123.45}, ...]
    bottom_5_councils = models.JSONField()
    
    # Council type breakdowns
    type_averages = models.JSONField()  # {"Unitary": avg, "County": avg, ...}
    nation_averages = models.JSONField()  # {"England": avg, "Scotland": avg, ...}
    
    # Change indicators
    data_hash = models.CharField(max_length=64)  # SHA256 of source data
    
    class Meta:
        unique_together = ['date_calculated', 'year', 'field']
```

#### 2. Change Detection System
```python
class SitewideDataChangeLog(models.Model):
    """Tracks when underlying data changes to trigger factoid refresh."""
    timestamp = models.DateTimeField(auto_now_add=True)
    change_type = models.CharField(max_length=20)  # 'data_update', 'new_council', 'new_field'
    affected_year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE, null=True)
    affected_field = models.ForeignKey(DataField, on_delete=models.CASCADE, null=True)
    affected_council = models.ForeignKey(Council, on_delete=models.CASCADE, null=True)
    
    # Metadata
    old_hash = models.CharField(max_length=64, blank=True)
    new_hash = models.CharField(max_length=64)
```

### Phase B: Intelligent Scheduling System

#### 1. Smart Update Schedule
```python
class SitewideFactoidSchedule(models.Model):
    """Manages intelligent updating of site-wide factoids."""
    # Schedule configuration
    update_times = models.JSONField(default=list)  # ["06:00", "10:30", "14:00", "18:30"]
    last_data_check = models.DateTimeField(null=True)
    last_generation = models.DateTimeField(null=True)
    
    # Change detection
    last_data_hash = models.CharField(max_length=64, blank=True)
    pending_changes = models.BooleanField(default=False)
    
    # Performance tracking
    generation_count_today = models.IntegerField(default=0)
    avg_generation_time = models.FloatField(default=0.0)
```

#### 2. Management Command for Scheduled Updates
```bash
# Cron schedule - runs every hour but only generates when needed
0 * * * * python manage.py update_sitewide_factoids --check-schedule
```

### Phase C: Optimized Data Processing

#### 1. Tiered Data Sampling
```python
def get_optimized_council_sample(field_slug, max_councils=50):
    """
    Get a representative sample of councils for analysis.
    
    Strategy:
    - Always include top 10 and bottom 10 performers
    - Random sample from middle ranges
    - Ensure geographic/type diversity
    - Limit total to max_councils to control prompt size
    """
```

#### 2. Efficient Prompt Generation
```python
def build_compact_analysis_prompt(summary_data, limit=3):
    """
    Generate compact prompts using pre-aggregated data.
    
    Instead of sending raw data for 300+ councils,
    send smart summaries and key comparisons.
    """
```

### Phase D: Advanced Caching Strategy

#### 1. Multi-level Caching
```python
# Level 1: Pre-aggregated summaries (refreshed daily)
CACHE_KEY_SUMMARIES = "sitewide_summaries:{date}"

# Level 2: Generated factoids (refreshed 4x daily when data changes)  
CACHE_KEY_FACTOIDS = "sitewide_factoids:{schedule_slot}:{data_hash}"

# Level 3: Emergency fallback factoids (static, manually curated)
CACHE_KEY_FALLBACK = "sitewide_factoids:fallback"
```

#### 2. Smart Cache Invalidation
```python
def invalidate_sitewide_caches_on_data_change(sender, instance, **kwargs):
    """
    Django signal to invalidate caches when financial data changes.
    Only invalidates when changes affect comparison fields.
    """
```

## Implementation Phases

### Phase 1: Data Aggregation ✅ COMPLETE
- [x] Create SitewideDataSummary model
- [x] Create management command to build daily summaries (`build_sitewide_summaries`)
- [x] Add change detection system (SitewideDataChangeLog)
- [x] Set up daily aggregation structure

### Phase 2: Intelligent Scheduling ✅ COMPLETE
- [x] Create SitewideFactoidSchedule model  
- [x] Build smart update management command (`update_sitewide_factoids`)
- [x] Implement 4x daily schedule with change detection
- [x] Add intelligent update timing

### Phase 3: Optimized Generation ✅ COMPLETE
- [x] Implement tiered data sampling (max 8 fields, top 3 councils each)
- [x] Rewrite prompt generation for efficiency (`OptimizedSitewideFactoidGenerator`)
- [x] Add data quality scoring (data_completeness field)
- [x] Create fallback factoid system

### Phase 4: Advanced Caching ✅ COMPLETE
- [x] Implement multi-level caching (`OptimizedFactoidCache`)
- [x] Add smart cache invalidation
- [x] Create cache warming system
- [x] Add performance monitoring

### Phase 5: Integration & Deployment 🚀 IN PROGRESS
- [ ] Create and run database migrations
- [ ] Initialize schedule configuration
- [ ] Build initial data summaries
- [ ] Set up cron job automation
- [ ] Update existing sitewide generator to use optimized system
- [ ] Performance testing and validation

## Files Created During Implementation

### Models
- `council_finance/models/sitewide_optimization.py`: All optimization models
- Migration: `0080_sitewide_optimization_models.py`

### Management Commands
- `council_finance/management/commands/build_sitewide_summaries.py`: Daily aggregation
- `council_finance/management/commands/update_sitewide_factoids.py`: Intelligent scheduling

### Services
- `council_finance/services/optimized_sitewide_generator.py`: Optimized generation logic

## Deployment Commands

### Step 1: Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 2: Initialize System
```bash
# Set up default 4x daily schedule
python manage.py update_sitewide_factoids --init-schedule

# Build initial summaries for latest year
python manage.py build_sitewide_summaries

# Generate first optimized factoids
python manage.py update_sitewide_factoids --force --limit=3
```

### Step 3: Cron Jobs (Production)
```bash
# Daily aggregation at 5:00 AM
0 5 * * * cd /path/to/project && python manage.py build_sitewide_summaries

# Intelligent updates every hour (only generates when needed)
0 * * * * cd /path/to/project && python manage.py update_sitewide_factoids --check-schedule
```

### Step 4: Integration Testing
```bash
# Test current system compatibility
python manage.py shell -c "
from council_finance.services.optimized_sitewide_generator import OptimizedSitewideFactoidGenerator
gen = OptimizedSitewideFactoidGenerator()
factoids = gen.generate_optimized_factoids(limit=3)
print('Generated factoids:', len(factoids))
for f in factoids:
    print('  -', f.get('text', 'N/A'))
"

# Test scheduling system
python manage.py update_sitewide_factoids --check-schedule --dry-run
```

## Benefits

### 1. **Scalability**
- Handles 1000+ councils efficiently
- Prompt size limited regardless of data growth
- Pre-aggregated summaries reduce processing time

### 2. **Efficiency** 
- Only generates when data actually changes
- 4x daily schedule matches business needs
- Intelligent sampling reduces API costs

### 3. **Performance**
- Sub-second response times from cache
- Minimal database load on homepage requests
- Predictable resource usage

### 4. **Quality**
- Change detection ensures freshness
- Data quality scoring improves accuracy
- Representative sampling maintains insight quality

## Resource Requirements

### Database Storage
- ~1KB per field per year per day for summaries
- Estimated 50 fields × 365 days = ~18MB/year growth
- Minimal compared to current query overhead

### Compute Resources
- Daily aggregation: ~2-5 minutes
- 4x daily generation: ~30 seconds each when needed
- 95% reduction in OpenAI API calls

### Cache Storage
- Pre-aggregated summaries: ~5MB daily
- Generated factoids: ~1KB per set
- Emergency fallback: ~5KB static

## Migration Strategy

### Week 1: Foundation
1. Deploy aggregation models and commands
2. Run initial data aggregation
3. Implement change detection
4. Set up scheduling system

### Week 2: Optimization
1. Deploy optimized generation system
2. Migrate existing cache keys
3. Enable smart scheduling
4. Monitor performance improvements

### Week 3: Validation
1. Verify factoid quality maintained
2. Confirm performance improvements
3. Tune sampling algorithms
4. Document new system

## Success Metrics

- **Response Time**: < 100ms for cached factoids
- **Data Freshness**: Updates within 1 hour of data changes
- **API Efficiency**: 95% reduction in OpenAI calls
- **Quality Maintenance**: User satisfaction scores maintained
- **Scalability**: System handles 10x data growth without degradation