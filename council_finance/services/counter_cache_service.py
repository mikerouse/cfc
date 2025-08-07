"""
Counter Cache Service - Hybrid 3-tier caching system for counter results.

Provides fast counter value retrieval with database persistence and smart invalidation:
1. Redis cache (fastest, volatile)
2. Database cache (persistent, survives restarts) 
3. Live calculation (slowest, last resort)

Features:
- Persistent storage across server restarts
- Smart cache invalidation when data changes
- Rate limiting to prevent excessive recalculation  
- Comprehensive Event Viewer integration
- Background warming for critical counters
"""

import time
from decimal import Decimal
from typing import Optional, Dict, Any, List


class CounterCalculatingError(Exception):
    """Raised when counter value is being calculated and not yet available."""
    def __init__(self, counter_slug, message="Counter calculation in progress"):
        self.counter_slug = counter_slug
        super().__init__(message)
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from django.db import models
from council_finance.models import (
    CounterResult, 
    CounterDefinition, 
    Council, 
    FinancialYear,
    SiteCounter
)
from council_finance.agents.counter_agent import CounterAgent
from council_finance.agents.site_totals_agent import SiteTotalsAgent
try:
    from council_finance.agents.site_totals_agent_optimized import SiteTotalsAgentOptimized
    USE_OPTIMIZED_AGENT = True
except ImportError:
    USE_OPTIMIZED_AGENT = False

# Event Viewer integration
try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False


def log_cache_event(level, category, title, message, details=None):
    """Log cache service events to Event Viewer for monitoring"""
    if not EVENT_VIEWER_AVAILABLE:
        return
    
    try:
        event_details = {
            'module': 'counter_cache_service',
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            event_details.update(details)
        
        SystemEvent.objects.create(
            source='counter_cache_service',
            level=level,
            category=category,
            title=title,
            message=message,
            details=event_details
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log cache service Event Viewer event: {e}")


class CounterCacheService:
    """
    Hybrid 3-tier caching service for counter results.
    
    Tier 1: Redis cache (0.01s lookup)
    Tier 2: Database cache (0.1s lookup) 
    Tier 3: Live calculation (0.5-5s per counter)
    """
    
    # Cache TTL settings
    REDIS_TTL = 3600  # 1 hour
    DATABASE_TTL_DAYS = 30  # Results stay fresh for 30 days
    RATE_LIMIT_WINDOW = 3600  # 1 hour rate limit window
    MAX_STALE_MARKS_PER_HOUR = 5  # Max times a result can be marked stale per hour
    
    def __init__(self):
        self.counter_agent = CounterAgent()
        # Always use the efficient agent for fast performance
        from council_finance.agents.efficient_site_totals import EfficientSiteTotalsAgent
        self.site_totals_agent = EfficientSiteTotalsAgent()
    
    def get_counter_value(self, 
                         counter_slug: str, 
                         council_slug: Optional[str] = None, 
                         year_label: Optional[str] = None,
                         use_stale_if_needed: bool = True,
                         allow_expensive_calculation: bool = False) -> Decimal:
        """
        Get counter value using 3-tier caching strategy.
        
        Args:
            counter_slug: Slug of counter to retrieve
            council_slug: Council slug (None for site-wide totals)
            year_label: Financial year label (None for all years)
            use_stale_if_needed: Whether to return stale data if fresh calculation fails
            
        Returns:
            Decimal: Counter value (0.00 if not found/error)
        """
        start_time = time.time()
        cache_tier_used = None
        
        try:
            # Build cache key
            year_key = year_label or "all"
            if council_slug:
                redis_key = f"counter_values:{council_slug}:{year_key}"
                lookup_type = "council"
            else:
                redis_key = f"counter_total:{counter_slug}:{year_key}"
                lookup_type = "sitewide"
            
            
            # Tier 1: Check Redis cache (fastest)
            redis_value = cache.get(redis_key)
            if redis_value is not None:
                cache_tier_used = "redis"
                lookup_time = (time.time() - start_time) * 1000
                
                # Record cache hit if we have a database result
                self._record_database_cache_hit(counter_slug, council_slug, year_label)
                
                log_cache_event(
                    'debug', 'performance',
                    'Counter Cache Hit (Redis)',
                    f'Fast Redis lookup for {counter_slug}: £{redis_value:,.2f}',
                    details={
                        'counter_slug': counter_slug,
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'cache_tier': 'redis',
                        'lookup_time_ms': round(lookup_time, 2),
                        'lookup_type': lookup_type,
                        'value': float(redis_value)
                    }
                )
                
                return Decimal(str(redis_value))
            
            # Tier 2: Check Database cache (persistent)
            db_result = self._get_database_result(counter_slug, council_slug, year_label)
            if db_result and not db_result.is_stale:
                cache_tier_used = "database"
                value = db_result.value
                
                # Store in Redis for next time
                cache.set(redis_key, float(value), self.REDIS_TTL)
                db_result.record_cache_hit()
                
                lookup_time = (time.time() - start_time) * 1000
                
                log_cache_event(
                    'info', 'performance',
                    'Counter Cache Hit (Database)',
                    f'Database lookup for {counter_slug}: £{value:,.2f}',
                    details={
                        'counter_slug': counter_slug,
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'cache_tier': 'database',
                        'lookup_time_ms': round(lookup_time, 2),
                        'lookup_type': lookup_type,
                        'value': float(value),
                        'result_age_hours': (timezone.now() - db_result.calculated_at).total_seconds() / 3600
                    }
                )
                
                return value
            
            # Tier 3: Live calculation (expensive)
            cache_tier_used = "calculation"
            value = self._calculate_fresh_value(counter_slug, council_slug, year_label, 
                                               allow_expensive=allow_expensive_calculation)
            
            if value is not None:
                # Store in both Redis and Database
                cache.set(redis_key, float(value), self.REDIS_TTL)
                self._store_database_result(counter_slug, council_slug, year_label, value, 
                                          calculation_time=time.time() - start_time)
                
                lookup_time = (time.time() - start_time) * 1000
                
                log_cache_event(
                    'info', 'calculation',
                    'Counter Value Calculated Fresh',
                    f'Fresh calculation for {counter_slug}: £{value:,.2f}',
                    details={
                        'counter_slug': counter_slug,
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'cache_tier': 'calculation',
                        'lookup_time_ms': round(lookup_time, 2),
                        'calculation_time_seconds': round(time.time() - start_time, 3),
                        'lookup_type': lookup_type,
                        'value': float(value)
                    }
                )
                
                return value
            
            # Fallback: Use stale data if available and permitted
            if use_stale_if_needed and db_result and db_result.is_stale:
                cache_tier_used = "stale_fallback"
                value = db_result.value
                
                lookup_time = (time.time() - start_time) * 1000
                
                log_cache_event(
                    'warning', 'performance',
                    'Counter Using Stale Data',
                    f'Serving stale data for {counter_slug}: £{value:,.2f} (stale for {(timezone.now() - db_result.stale_marked_at).total_seconds() / 3600:.1f}h)',
                    details={
                        'counter_slug': counter_slug,
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'cache_tier': 'stale_fallback',
                        'lookup_time_ms': round(lookup_time, 2),
                        'lookup_type': lookup_type,
                        'value': float(value),
                        'stale_duration_hours': (timezone.now() - db_result.stale_marked_at).total_seconds() / 3600
                    }
                )
                
                return value
            
            # Complete failure - return 0
            log_cache_event(
                'error', 'data_integrity',
                'Counter Value Lookup Failed',
                f'All cache tiers failed for {counter_slug}, returning 0',
                details={
                    'counter_slug': counter_slug,
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'lookup_time_ms': round((time.time() - start_time) * 1000, 2),
                    'lookup_type': lookup_type,
                    'fallback_value': 0
                }
            )
            
            return Decimal('0.00')
            
        except CounterCalculatingError:
            # Re-raise CounterCalculatingError so views can handle it
            # Don't catch this as a generic exception
            raise
            
        except Exception as e:
            lookup_time = (time.time() - start_time) * 1000
            
            log_cache_event(
                'error', 'system_error',
                'Counter Cache Service Exception',
                f'Exception in counter lookup for {counter_slug}: {str(e)}',
                details={
                    'counter_slug': counter_slug,
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'cache_tier': cache_tier_used,
                    'lookup_time_ms': round(lookup_time, 2),
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'lookup_type': lookup_type
                }
            )
            
            return Decimal('0.00')
    
    def _get_database_result(self, counter_slug: str, council_slug: Optional[str], 
                           year_label: Optional[str]) -> Optional[CounterResult]:
        """Get counter result from database cache"""
        try:
            counter = CounterDefinition.objects.get(slug=counter_slug)
            council = Council.objects.get(slug=council_slug) if council_slug else None
            year = FinancialYear.objects.get(label=year_label) if year_label else None
            
            return CounterResult.objects.filter(
                counter=counter,
                council=council,
                year=year
            ).first()
            
        except (CounterDefinition.DoesNotExist, Council.DoesNotExist, FinancialYear.DoesNotExist):
            return None
    
    def _record_database_cache_hit(self, counter_slug: str, council_slug: Optional[str], 
                                  year_label: Optional[str]):
        """Record cache hit statistics in database"""
        db_result = self._get_database_result(counter_slug, council_slug, year_label)
        if db_result:
            db_result.record_cache_hit()
    
    def _calculate_fresh_value(self, counter_slug: str, council_slug: Optional[str], 
                             year_label: Optional[str], allow_expensive: bool = False) -> Optional[Decimal]:
        """Calculate counter value fresh using appropriate agent"""
        try:
            if council_slug:
                # Individual council calculation
                values = self.counter_agent.run(council_slug=council_slug, year_label=year_label)
                counter_data = values.get(counter_slug)
                if counter_data and counter_data.get("value") is not None:
                    return Decimal(str(counter_data["value"]))
            else:
                # Site-wide calculation - only run if explicitly allowed
                if not allow_expensive:
                    log_cache_event(
                        'warning', 'performance',
                        'Site-Wide Calculation Skipped - Cache Cold',
                        f'Skipping expensive site-wide calculation for {counter_slug} to prevent page timeout',
                        details={
                            'counter_slug': counter_slug,
                            'year_label': year_label,
                            'operation': 'site_totals_agent_skipped',
                            'recommendation': 'Run "python manage.py warmup_counter_cache" to populate cache'
                        }
                    )
                    
                    # Return special sentinel value to indicate calculation needed
                    # This allows the frontend to show "Calculating..." instead of £0
                    # Using -1 as sentinel since counter values are never negative
                    return Decimal('-1')
                
                # Only run expensive calculation when explicitly allowed (e.g., during cache warming)
                log_cache_event(
                    'warning', 'performance',
                    'Expensive Site-Wide Calculation Started',
                    f'Running site-wide calculation for {counter_slug} (this may take 2+ minutes)',
                    details={
                        'counter_slug': counter_slug,
                        'year_label': year_label,
                        'operation': 'site_totals_agent_run',
                        'allowed_by': 'explicit_flag'
                    }
                )
                
                # Concurrency protection for expensive site-wide calculation
                site_totals_lock_key = "site_totals_agent_run_lock"
                
                # Check if another SiteTotalsAgent is already running
                if cache.get(site_totals_lock_key):
                    log_cache_event(
                        'warning', 'concurrency',
                        'SiteTotalsAgent Already Running',
                        f'Skipping site-wide calculation for {counter_slug} - another SiteTotalsAgent is running',
                        details={
                            'counter_slug': counter_slug,
                            'year_label': year_label,
                            'reason': 'concurrent_protection'
                        }
                    )
                    
                    # Return sentinel to indicate calculation is needed but not available right now
                    return Decimal('-1')
                
                # Set lock with 20 minute timeout (site-wide calcs can take a long time)
                cache.set(site_totals_lock_key, True, 1200)  # 20 minutes
                
                try:
                    # Run the expensive site totals calculation
                    calculation_start = time.time()
                    self.site_totals_agent.run()
                    calculation_duration = time.time() - calculation_start
                    
                    log_cache_event(
                        'info', 'performance',
                        'SiteTotalsAgent Completed',
                        f'Site-wide calculation completed in {calculation_duration:.2f}s',
                        details={
                            'counter_slug': counter_slug,
                            'year_label': year_label,
                            'calculation_time_seconds': calculation_duration
                        }
                    )
                    
                finally:
                    # Always release the SiteTotalsAgent lock
                    try:
                        cache.delete(site_totals_lock_key)
                    except Exception as lock_error:
                        log_cache_event(
                            'warning', 'concurrency',
                            'Failed to Release SiteTotalsAgent Lock',
                            f'Could not release site totals agent lock: {str(lock_error)}'
                        )
                
                # Get the cached result
                cache_key = f"counter_total:{counter_slug}:{year_label or 'all'}"
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    return Decimal(str(cached_value))
            
            return None
            
        except Exception as e:
            log_cache_event(
                'error', 'calculation',
                'Counter Calculation Failed',
                f'Failed to calculate {counter_slug}: {str(e)}',
                details={
                    'counter_slug': counter_slug,
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            return None
    
    def _store_database_result(self, counter_slug: str, council_slug: Optional[str], 
                              year_label: Optional[str], value: Decimal, 
                              calculation_time: float):
        """Store counter result in database cache"""
        try:
            counter = CounterDefinition.objects.get(slug=counter_slug)
            council = Council.objects.get(slug=council_slug) if council_slug else None
            year = FinancialYear.objects.get(label=year_label) if year_label else None
            
            # Calculate data hash for change detection
            data_hash = CounterResult.calculate_data_hash(counter, council, year)
            
            # Store or update result
            result, created = CounterResult.objects.update_or_create(
                counter=counter,
                council=council,
                year=year,
                defaults={
                    'value': value,
                    'is_stale': False,
                    'data_hash': data_hash,
                    'calculation_time_seconds': calculation_time,
                    'stale_marked_at': None,
                    'stale_mark_count': 0,
                    'last_accessed': timezone.now()
                }
            )
            
            return result
            
        except (CounterDefinition.DoesNotExist, Council.DoesNotExist, FinancialYear.DoesNotExist) as e:
            log_cache_event(
                'error', 'data_integrity',
                'Failed to Store Counter Result',
                f'Could not store result for {counter_slug}: {str(e)}',
                details={
                    'counter_slug': counter_slug,
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'value': float(value),
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            return None
    
    def warm_critical_counters(self) -> Dict[str, Any]:
        """
        Warm cache for critical counters (homepage promoted counters).
        
        Prevents concurrent warming sessions to avoid database overload and
        conflicting cache updates during server restarts.
        
        Returns:
            Dict with warming results and statistics
        """
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
                'counters_warmed': 0,
                'counters_failed': 0,
                'total_time_seconds': 0,
                'warmed_counters': [],
                'failed_counters': [],
                'status': 'already_running',
                'message': 'Another warming session is already in progress'
            }
        
        # Set lock with 15 minute timeout (site-wide calculations can take a while)
        cache.set(lock_key, True, 900)  # 15 minutes
        
        start_time = time.time()
        results = {
            'counters_warmed': 0,
            'counters_failed': 0,
            'total_time_seconds': 0,
            'warmed_counters': [],
            'failed_counters': [],
            'status': 'completed'
        }
        
        log_cache_event(
            'info', 'maintenance',
            'Critical Counter Cache Warming Started',
            'Starting background warming of critical counters (lock acquired)'
        )
        
        try:
            # Get promoted homepage counters
            promoted_counters = SiteCounter.objects.filter(promote_homepage=True)
            
            for sc in promoted_counters:
                counter_start = time.time()
                year_label = sc.year.label if sc.year else None
                
                try:
                    # Check if needs warming (stale or missing)
                    db_result = self._get_database_result(sc.counter.slug, None, year_label)
                    
                    if not db_result or db_result.is_stale:
                        # Warm this counter
                        value = self.get_counter_value(
                            counter_slug=sc.counter.slug,
                            year_label=year_label,
                            use_stale_if_needed=False,
                            allow_expensive_calculation=True  # Allow expensive site-wide calculations
                        )
                        
                        counter_time = time.time() - counter_start
                        results['counters_warmed'] += 1
                        results['warmed_counters'].append({
                            'counter_slug': sc.counter.slug,
                            'counter_name': sc.counter.name,
                            'year_label': year_label,
                            'value': float(value),
                            'time_seconds': round(counter_time, 2)
                        })
                        
                        log_cache_event(
                            'info', 'maintenance',
                            'Counter Cache Warmed',
                            f'Warmed {sc.counter.name}: £{value:,.2f} ({counter_time:.2f}s)',
                            details={
                                'counter_slug': sc.counter.slug,
                                'year_label': year_label,
                                'value': float(value),
                                'warming_time_seconds': counter_time
                            }
                        )
                    else:
                        # Already fresh, skip
                        counter_time = time.time() - counter_start
                        results['warmed_counters'].append({
                            'counter_slug': sc.counter.slug,
                            'counter_name': sc.counter.name,
                            'year_label': year_label,
                            'value': float(db_result.value),
                            'time_seconds': round(counter_time, 2),
                            'skipped': 'already_fresh'
                        })
                
                except Exception as e:
                    counter_time = time.time() - counter_start
                    results['counters_failed'] += 1
                    results['failed_counters'].append({
                        'counter_slug': sc.counter.slug,
                        'counter_name': sc.counter.name,
                        'year_label': year_label,
                        'error': str(e),
                        'time_seconds': round(counter_time, 2)
                    })
                    
                    log_cache_event(
                        'error', 'maintenance',
                        'Counter Cache Warming Failed',
                        f'Failed to warm {sc.counter.name}: {str(e)}',
                        details={
                            'counter_slug': sc.counter.slug,
                            'year_label': year_label,
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'warming_time_seconds': counter_time
                        }
                    )
            
            results['total_time_seconds'] = round(time.time() - start_time, 2)
            
            log_cache_event(
                'info', 'maintenance',
                'Critical Counter Cache Warming Completed',
                f'Warmed {results["counters_warmed"]} counters in {results["total_time_seconds"]}s',
                details=results
            )
            
            return results
            
        except Exception as e:
            results['total_time_seconds'] = round(time.time() - start_time, 2)
            results['status'] = 'failed'
            
            log_cache_event(
                'error', 'maintenance',
                'Counter Cache Warming Exception',
                f'Critical counter warming failed: {str(e)}',
                details={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'partial_results': results
                }
            )
            
            return results
        
        finally:
            # Always release the lock, even if an exception occurred
            try:
                cache.delete(lock_key)
                log_cache_event(
                    'info', 'maintenance',
                    'Critical Counter Warming Lock Released',
                    'Released concurrency lock for critical counter warming'
                )
            except Exception as e:
                # Don't let lock cleanup failure affect the main operation
                log_cache_event(
                    'warning', 'maintenance',
                    'Failed to Release Warming Lock',
                    f'Could not release critical counter warming lock: {str(e)}'
                )
    
    def get_cache_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics"""
        since = timezone.now() - timezone.timedelta(hours=hours_back)
        
        stats = {
            'total_results': CounterResult.objects.count(),
            'fresh_results': CounterResult.objects.filter(is_stale=False).count(),
            'stale_results': CounterResult.objects.filter(is_stale=True).count(),
            'recently_calculated': CounterResult.objects.filter(calculated_at__gte=since).count(),
            'total_cache_hits': CounterResult.objects.aggregate(
                total=models.Sum('cache_hits')
            )['total'] or 0,
            'rate_limited_results': CounterResult.objects.filter(stale_mark_count__gte=self.MAX_STALE_MARKS_PER_HOUR).count(),
            'stale_marking_stats': CounterResult.get_stale_marking_stats(hours_back),
            'performance_breakdown': {
                'fastest_calculations': list(CounterResult.objects.filter(
                    calculation_time_seconds__isnull=False
                ).order_by('calculation_time_seconds')[:5].values(
                    'counter__name', 'council__name', 'year__label', 'calculation_time_seconds'
                )),
                'slowest_calculations': list(CounterResult.objects.filter(
                    calculation_time_seconds__isnull=False
                ).order_by('-calculation_time_seconds')[:5].values(
                    'counter__name', 'council__name', 'year__label', 'calculation_time_seconds'
                ))
            }
        }
        
        return stats


# Global service instance
counter_cache_service = CounterCacheService()