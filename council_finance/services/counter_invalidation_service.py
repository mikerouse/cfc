"""
Counter Cache Invalidation Service - Smart cache invalidation with rate limiting.

Handles intelligent cache invalidation when underlying data changes, with rate limiting 
to prevent excessive stale marking during bulk data entry sessions.

Features:
- Rate limiting: Max 5 stale marks per hour per counter result
- Bulk invalidation detection and batching
- Event Viewer integration for monitoring
- Smart targeting: Only invalidates affected counters
- Session-aware batching for user edit sessions
"""

from typing import List, Dict, Set, Optional, Any
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
from django.contrib.sessions.models import Session

from council_finance.models import (
    CounterResult,
    FinancialFigure,
    CouncilCharacteristic,
    Council,
    FinancialYear,
    CounterDefinition
)

# Event Viewer integration
try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False


def log_invalidation_event(level, category, title, message, details=None):
    """Log cache invalidation events to Event Viewer for monitoring"""
    if not EVENT_VIEWER_AVAILABLE:
        return
    
    try:
        event_details = {
            'module': 'counter_invalidation_service',
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            event_details.update(details)
        
        SystemEvent.objects.create(
            source='counter_invalidation_service',
            level=level,
            category=category,
            title=title,
            message=message,
            details=event_details
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log invalidation Event Viewer event: {e}")


class CounterInvalidationService:
    """
    Intelligent cache invalidation service with rate limiting and batching.
    
    Prevents excessive cache invalidation during user edit sessions by:
    1. Rate limiting stale marks per counter result
    2. Batching related changes together
    3. Detecting user edit sessions and delaying invalidation
    4. Comprehensive monitoring via Event Viewer
    """
    
    # Rate limiting settings
    RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour
    MAX_STALE_MARKS_PER_WINDOW = 5  # Max stale marks per result per hour
    BATCH_DELAY_SECONDS = 30  # Wait 30s before invalidating to batch changes
    SESSION_INVALIDATION_THRESHOLD = 3  # If 3+ changes in session, batch them
    
    def __init__(self):
        # Track pending invalidations for batching
        self._pending_invalidations = {}  # council_slug -> {counters, timestamp, changes}
        self._session_changes = {}  # session_key -> change_count
    
    def invalidate_counter_results(self, 
                                  council: Council, 
                                  year: Optional[FinancialYear] = None,
                                  reason: str = "data_changed",
                                  user_session_key: Optional[str] = None,
                                  force: bool = False) -> Dict[str, Any]:
        """
        Invalidate counter results for a council/year with smart rate limiting.
        
        Args:
            council: Council whose data changed
            year: Specific year that changed (None for all years)
            reason: Why invalidation is needed
            user_session_key: User session for batching detection
            force: Skip rate limiting (for admin actions)
            
        Returns:
            Dict with invalidation results and statistics
        """
        start_time = timezone.now()
        results = {
            'invalidated_count': 0,
            'rate_limited_count': 0,
            'batched_count': 0,
            'redis_keys_cleared': 0,
            'affected_counters': [],
            'rate_limited_counters': [],
            'session_batched': False
        }
        
        # Session-aware batching for user edit sessions
        if user_session_key and not force:
            session_changes = self._session_changes.get(user_session_key, 0) + 1
            self._session_changes[user_session_key] = session_changes
            
            # If user is making multiple changes, batch them
            if session_changes >= self.SESSION_INVALIDATION_THRESHOLD:
                return self._batch_session_invalidation(
                    council, year, reason, user_session_key, results
                )
        
        # Find all counter results that need invalidation
        affected_results = self._find_affected_results(council, year)
        
        log_invalidation_event(
            'info', 'cache_invalidation',
            'Counter Cache Invalidation Started',
            f'Starting invalidation for {council.name} ({len(affected_results)} results affected)',
            details={
                'council_slug': council.slug,
                'council_name': council.name,
                'year_label': year.label if year else 'all_years',
                'invalidation_reason': reason,
                'affected_results_count': len(affected_results),
                'user_session_key': user_session_key[:8] + '...' if user_session_key else None,
                'forced': force
            }
        )
        
        # Process each affected result
        for result in affected_results:
            invalidation_start = timezone.now()
            
            # Try to mark as stale (with rate limiting)
            was_invalidated = result.mark_stale(reason=reason, force=force)
            
            if was_invalidated:
                results['invalidated_count'] += 1
                
                # Clear Redis cache keys
                redis_keys_cleared = self._clear_redis_cache(result)
                results['redis_keys_cleared'] += redis_keys_cleared
                
                results['affected_counters'].append({
                    'counter_slug': result.counter.slug,
                    'counter_name': result.counter.name,
                    'council_slug': result.council.slug if result.council else None,
                    'council_name': result.council.name if result.council else 'Site-wide',
                    'year_label': result.year.label if result.year else 'All Years',
                    'previous_value': float(result.value),
                    'stale_mark_count': result.stale_mark_count,
                    'invalidation_time_ms': (timezone.now() - invalidation_start).total_seconds() * 1000
                })
                
            else:
                results['rate_limited_count'] += 1
                results['rate_limited_counters'].append({
                    'counter_slug': result.counter.slug,
                    'counter_name': result.counter.name,
                    'council_name': result.council.name if result.council else 'Site-wide',
                    'stale_mark_count': result.stale_mark_count,
                    'rate_limit_reason': f'Already marked stale {result.stale_mark_count} times in last hour'
                })
        
        # Trigger site-wide invalidation if this affects totals
        if results['invalidated_count'] > 0:
            self._invalidate_sitewide_totals(council, year, reason, force)
        
        total_time = (timezone.now() - start_time).total_seconds()
        
        # Log comprehensive invalidation results
        log_level = 'info' if results['invalidated_count'] > 0 else 'warning'
        log_invalidation_event(
            log_level, 'cache_invalidation',
            'Counter Cache Invalidation Completed',
            f'Invalidated {results["invalidated_count"]}/{len(affected_results)} results for {council.name} in {total_time:.2f}s',
            details={
                **results,
                'council_slug': council.slug,
                'council_name': council.name,
                'year_label': year.label if year else 'all_years',
                'total_time_seconds': total_time,
                'invalidation_reason': reason
            }
        )
        
        # Alert if high rate limiting
        if results['rate_limited_count'] > results['invalidated_count']:
            log_invalidation_event(
                'warning', 'performance',
                'High Counter Invalidation Rate Limiting',
                f'Rate limited {results["rate_limited_count"]} counter invalidations for {council.name} - possible bulk edit session',
                details={
                    'council_slug': council.slug,
                    'council_name': council.name,
                    'rate_limited_count': results['rate_limited_count'],
                    'invalidated_count': results['invalidated_count'],
                    'user_session_key': user_session_key[:8] + '...' if user_session_key else None,
                    'recommendation': 'Consider using batch invalidation for bulk operations'
                }
            )
        
        return results
    
    def _find_affected_results(self, council: Council, year: Optional[FinancialYear] = None) -> List[CounterResult]:
        """Find all counter results affected by data changes"""
        affected_results = []
        
        # Individual council results
        council_results = CounterResult.objects.filter(council=council)
        if year:
            council_results = council_results.filter(year=year)
        affected_results.extend(council_results)
        
        # Site-wide results (these aggregate this council's data)
        sitewide_results = CounterResult.objects.filter(council=None)
        if year:
            sitewide_results = sitewide_results.filter(year=year)
        affected_results.extend(sitewide_results)
        
        return affected_results
    
    def _clear_redis_cache(self, result: CounterResult) -> int:
        """Clear Redis cache keys for a counter result"""
        keys_cleared = 0
        
        # Build possible cache keys
        year_key = result.year.label if result.year else "all"
        cache_keys = []
        
        if result.council:
            # Individual council cache keys
            cache_keys.append(f"counter_values:{result.council.slug}:{year_key}")
        else:
            # Site-wide cache keys
            cache_keys.append(f"counter_total:{result.counter.slug}:{year_key}")
            cache_keys.append(f"counter_total:{result.counter.slug}:{year_key}:prev")
        
        # Clear each key
        for key in cache_keys:
            if cache.get(key) is not None:
                cache.delete(key)
                keys_cleared += 1
        
        return keys_cleared
    
    def _invalidate_sitewide_totals(self, council: Council, year: Optional[FinancialYear], 
                                   reason: str, force: bool):
        """Invalidate site-wide totals that aggregate this council's data"""
        sitewide_results = CounterResult.objects.filter(council=None)
        if year:
            sitewide_results = sitewide_results.filter(year=year)
        
        sitewide_invalidated = 0
        for result in sitewide_results:
            if result.mark_stale(reason=f"sitewide_aggregation_{reason}", force=force):
                sitewide_invalidated += 1
                self._clear_redis_cache(result)
        
        if sitewide_invalidated > 0:
            log_invalidation_event(
                'info', 'cache_invalidation',
                'Site-wide Counter Totals Invalidated',
                f'Invalidated {sitewide_invalidated} site-wide totals due to {council.name} data changes',
                details={
                    'council_slug': council.slug,
                    'council_name': council.name,
                    'year_label': year.label if year else 'all_years',
                    'sitewide_invalidated_count': sitewide_invalidated,
                    'reason': reason
                }
            )
    
    def _batch_session_invalidation(self, council: Council, year: Optional[FinancialYear],
                                   reason: str, session_key: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batched invalidation for user edit sessions"""
        session_id = session_key[:8] + '...'
        
        # Store for delayed processing
        batch_key = f"{council.slug}_{year.label if year else 'all'}"
        self._pending_invalidations[batch_key] = {
            'council': council,
            'year': year,
            'reason': reason,
            'session_key': session_key,
            'timestamp': timezone.now(),
            'change_count': self._session_changes[session_key]
        }
        
        results['session_batched'] = True
        results['batched_count'] = self._session_changes[session_key]
        
        log_invalidation_event(
            'info', 'cache_invalidation',
            'Counter Invalidation Batched for User Session',
            f'Batching invalidation for {council.name} - {self._session_changes[session_key]} changes in session',
            details={
                'council_slug': council.slug,
                'council_name': council.name,
                'year_label': year.label if year else 'all_years',
                'session_id': session_id,
                'change_count': self._session_changes[session_key],
                'batch_delay_seconds': self.BATCH_DELAY_SECONDS,
                'batch_key': batch_key
            }
        )
        
        # Schedule delayed invalidation (in a real app, use Celery/background task)
        # For now, we'll process immediately but log it as batched
        from django.utils import timezone
        import threading
        
        def delayed_invalidation():
            import time
            time.sleep(self.BATCH_DELAY_SECONDS)
            self._process_batched_invalidation(batch_key)
        
        # Start background thread for delayed processing
        thread = threading.Thread(target=delayed_invalidation)
        thread.daemon = True
        thread.start()
        
        return results
    
    def _process_batched_invalidation(self, batch_key: str):
        """Process a batched invalidation after delay"""
        if batch_key not in self._pending_invalidations:
            return
        
        batch_data = self._pending_invalidations.pop(batch_key)
        council = batch_data['council']
        year = batch_data['year']
        reason = batch_data['reason']
        session_key = batch_data['session_key']
        change_count = batch_data['change_count']
        
        # Process invalidation with force=True to bypass rate limiting
        results = self.invalidate_counter_results(
            council=council,
            year=year,
            reason=f"batched_{reason}",
            force=True  # Skip rate limiting for batched operations
        )
        
        # Clear session tracking
        if session_key in self._session_changes:
            del self._session_changes[session_key]
        
        log_invalidation_event(
            'info', 'cache_invalidation',
            'Batched Counter Invalidation Processed',
            f'Processed batched invalidation for {council.name} after {change_count} changes',
            details={
                'council_slug': council.slug,
                'council_name': council.name,
                'year_label': year.label if year else 'all_years',
                'original_change_count': change_count,
                'batch_delay_seconds': self.BATCH_DELAY_SECONDS,
                'batch_key': batch_key,
                'final_results': results
            }
        )
    
    def get_invalidation_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get comprehensive invalidation statistics for monitoring"""
        since = timezone.now() - timezone.timedelta(hours=hours_back)
        
        # Get Event Viewer data about invalidations
        stats = {
            'pending_batches': len(self._pending_invalidations),
            'active_sessions': len(self._session_changes),
            'rate_limited_results': CounterResult.objects.filter(
                stale_mark_count__gte=self.MAX_STALE_MARKS_PER_WINDOW
            ).count(),
            'frequently_invalidated_results': list(
                CounterResult.objects.filter(
                    stale_mark_count__gte=3
                ).order_by('-stale_mark_count')[:10].values(
                    'counter__name', 'council__name', 'year__label', 
                    'stale_mark_count', 'stale_marked_at'
                )
            ),
            'session_changes_summary': dict(self._session_changes),
            'pending_batches_summary': {
                batch_key: {
                    'council_name': data['council'].name,
                    'change_count': data['change_count'],
                    'pending_seconds': (timezone.now() - data['timestamp']).total_seconds()
                }
                for batch_key, data in self._pending_invalidations.items()
            }
        }
        
        # Add Event Viewer statistics if available
        if EVENT_VIEWER_AVAILABLE:
            try:
                from event_viewer.models import SystemEvent
                
                invalidation_events = SystemEvent.objects.filter(
                    source='counter_invalidation_service',
                    timestamp__gte=since
                )
                
                stats['event_viewer_stats'] = {
                    'total_events': invalidation_events.count(),
                    'by_level': {
                        level: invalidation_events.filter(level=level).count()
                        for level in ['info', 'warning', 'error']
                    },
                    'by_category': {
                        'cache_invalidation': invalidation_events.filter(category='cache_invalidation').count(),
                        'performance': invalidation_events.filter(category='performance').count(),
                    }
                }
                
            except Exception:
                stats['event_viewer_stats'] = {'error': 'Could not retrieve Event Viewer stats'}
        
        return stats


# Global service instance
counter_invalidation_service = CounterInvalidationService()


# Signal handlers for automatic invalidation
@receiver(post_save, sender=FinancialFigure)
def invalidate_on_financial_figure_change(sender, instance, created, **kwargs):
    """Invalidate counter caches when financial figures change"""
    # Get user session if available (Django request context)
    session_key = None
    try:
        # Try to get session from current request context
        from threading import local
        if hasattr(local(), 'request') and hasattr(local().request, 'session'):
            session_key = local().request.session.session_key
    except:
        pass
    
    reason = "financial_figure_created" if created else "financial_figure_updated"
    
    counter_invalidation_service.invalidate_counter_results(
        council=instance.council,
        year=instance.year,
        reason=reason,
        user_session_key=session_key
    )


@receiver(post_save, sender=CouncilCharacteristic)
def invalidate_on_characteristic_change(sender, instance, created, **kwargs):
    """Invalidate counter caches when council characteristics change"""
    # Get user session if available
    session_key = None
    try:
        from threading import local
        if hasattr(local(), 'request') and hasattr(local().request, 'session'):
            session_key = local().request.session.session_key
    except:
        pass
    
    reason = "characteristic_created" if created else "characteristic_updated"
    
    counter_invalidation_service.invalidate_counter_results(
        council=instance.council,
        year=None,  # Characteristics apply to all years
        reason=reason,
        user_session_key=session_key
    )


@receiver(post_delete, sender=FinancialFigure)
def invalidate_on_financial_figure_delete(sender, instance, **kwargs):
    """Invalidate counter caches when financial figures are deleted"""
    counter_invalidation_service.invalidate_counter_results(
        council=instance.council,
        year=instance.year,
        reason="financial_figure_deleted",
        force=True  # Deletions should always invalidate
    )


@receiver(post_delete, sender=CouncilCharacteristic)
def invalidate_on_characteristic_delete(sender, instance, **kwargs):
    """Invalidate counter caches when council characteristics are deleted"""
    counter_invalidation_service.invalidate_counter_results(
        council=instance.council,
        year=None,
        reason="characteristic_deleted",
        force=True  # Deletions should always invalidate
    )