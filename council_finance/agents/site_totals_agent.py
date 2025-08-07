"""Agent responsible for caching totals used on the home page."""

import logging
from django.core.cache import cache
from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    SiteCounter,
    GroupCounter,
)
from council_finance.year_utils import previous_year_label
from council_finance.utils.db_utils import DatabaseConnectionMonitor, chunked_database_operation, safe_database_operation, ensure_connection
from .counter_agent import CounterAgent

logger = logging.getLogger(__name__)

class SiteTotalsAgent(AgentBase):
    """Compute and cache totals for promoted counters."""

    name = "SiteTotalsAgent"

    def run(self, max_duration_minutes=15, **kwargs):
        """Aggregate counter values across councils and store in the cache."""
        import time
        
        start_time = time.time()
        max_duration_seconds = max_duration_minutes * 60
        
        def check_timeout():
            elapsed = time.time() - start_time
            if elapsed > max_duration_seconds:
                print(f"⚠️  TIMEOUT: SiteTotalsAgent exceeded {max_duration_minutes} minutes ({elapsed:.1f}s), stopping execution")
                raise TimeoutError(f"SiteTotalsAgent timeout after {elapsed:.2f} seconds")
            return elapsed
        
        with DatabaseConnectionMonitor("SiteTotalsAgent"):
            # Use the existing CounterAgent to compute individual council figures.
            agent = CounterAgent()
            
            # A list of all available years allows counters that span multiple
            # years to be aggregated without additional queries later.
            def get_years():
                return list(FinancialYear.objects.order_by("-label"))
            
            all_years = safe_database_operation(get_years)
            if not all_years:
                logger.error("Could not retrieve financial years, aborting")
                return

        # Import the counter cache service for faster lookups
        from council_finance.services.counter_cache_service import counter_cache_service
        
        for sc in SiteCounter.objects.all():
            # Sum the value of ``sc.counter`` across either a specific year or
            # every year when none is selected.
            value = 0.0
            years = [sc.year] if sc.year else all_years
            
            total_councils = Council.objects.count()
            print(f"Calculating {sc.name} for {total_councils} councils...")
            council_count = 0
            
            # Process councils in chunks to avoid connection timeouts
            councils_queryset = Council.objects.all()
            
            for council_chunk in chunked_database_operation(councils_queryset, chunk_size=10):
                for council in council_chunk:
                    for yr in years:
                        try:
                            # Use the cached counter service instead of agent.run() for performance
                            cached_value = counter_cache_service.get_counter_value(
                                counter_slug=sc.counter.slug,
                                council_slug=council.slug,
                                year_label=yr.label,
                                allow_expensive_calculation=False  # Don't trigger recursive calculations
                            )
                            if cached_value and cached_value > 0:
                                value += float(cached_value)
                        except Exception as e:
                            # Fallback to original method if cache service fails
                            data = agent.run(council_slug=council.slug, year_label=yr.label).get(sc.counter.slug)
                            if data and data.get("value") is not None:
                                try:
                                    value += float(data["value"])
                                except (TypeError, ValueError):
                                    pass
                
                council_count += len(council_chunk)
                if council_count % 10 == 0:
                    elapsed = check_timeout()  # Will raise TimeoutError if exceeded
                    print(f"  Processed {council_count}/{total_councils} councils... ({elapsed:.1f}s elapsed)")
                    
                    # Check connection health periodically
                    ensure_connection()
            year_label = sc.year.label if sc.year else "all"
            # Cache for 24 hours instead of forever to avoid stale data
            cache.set(f"counter_total:{sc.slug}:{year_label}", value, 86400)
            if sc.year:
                # Record the previous year's total so percentage change factoids
                # can be generated without additional database work.
                prev_label = previous_year_label(sc.year.label)
                if prev_label:
                    def get_prev_year():
                        return FinancialYear.objects.filter(label=prev_label).first()
                    
                    prev_year = safe_database_operation(get_prev_year)
                    if prev_year:
                        prev_value = 0.0
                        print(f"Calculating {sc.name} previous year ({prev_label})...")
                        
                        # Process previous year councils in chunks too
                        prev_councils_queryset = Council.objects.all()
                        prev_council_count = 0
                        
                        for prev_council_chunk in chunked_database_operation(prev_councils_queryset, chunk_size=10):
                            for council in prev_council_chunk:
                                try:
                                    # Use cached service for previous year too
                                    cached_value = counter_cache_service.get_counter_value(
                                        counter_slug=sc.counter.slug,
                                        council_slug=council.slug,
                                        year_label=prev_year.label,
                                        allow_expensive_calculation=False
                                    )
                                    if cached_value and cached_value > 0:
                                        prev_value += float(cached_value)
                                except Exception as e:
                                    # Fallback
                                    data = agent.run(council_slug=council.slug, year_label=prev_year.label).get(sc.counter.slug)
                                    if data and data.get("value") is not None:
                                        try:
                                            prev_value += float(data["value"])
                                        except (TypeError, ValueError):
                                            pass
                            
                            prev_council_count += len(prev_council_chunk)
                            if prev_council_count % 10 == 0:
                                elapsed = check_timeout()  # Will raise TimeoutError if exceeded
                                print(f"  Previous year: Processed {prev_council_count}/{total_councils} councils... ({elapsed:.1f}s elapsed)")
                                
                                # Check connection health periodically
                                ensure_connection()
                        
                        cache.set(f"counter_total:{sc.slug}:{year_label}:prev", prev_value, 86400)

        # Process group counters with connection monitoring
        def get_group_counters():
            return list(GroupCounter.objects.all())
        
        group_counters = safe_database_operation(get_group_counters) or []
        
        for gc in group_counters:
            with DatabaseConnectionMonitor(f"GroupCounter_{gc.name}"):
                # Resolve the set of councils this group counter applies to.
                def get_group_councils():
                    councils = Council.objects.all()
                    if gc.councils.exists():
                        councils = gc.councils.all()
                    if gc.council_list_id:
                        councils = councils & gc.council_list.councils.all()
                    if gc.council_types.exists():
                        councils = councils.filter(council_type__in=gc.council_types.all())
                    return councils
                
                councils_queryset = safe_database_operation(get_group_councils)
                if not councils_queryset:
                    continue
                    
                total_group_councils = councils_queryset.count()
                value = 0.0
                years = [gc.year] if gc.year else all_years
                print(f"Calculating group counter {gc.name} for {total_group_councils} councils...")
                
                group_council_count = 0
                
                # Process group councils in chunks
                for group_council_chunk in chunked_database_operation(councils_queryset, chunk_size=10):
                    for council in group_council_chunk:
                        for yr in years:
                            try:
                                # Use cached service for group counters too
                                cached_value = counter_cache_service.get_counter_value(
                                    counter_slug=gc.counter.slug,
                                    council_slug=council.slug,
                                    year_label=yr.label,
                                    allow_expensive_calculation=False
                                )
                                if cached_value and cached_value > 0:
                                    value += float(cached_value)
                            except Exception as e:
                                # Fallback
                                data = agent.run(council_slug=council.slug, year_label=yr.label).get(gc.counter.slug)
                                if data and data.get("value") is not None:
                                    try:
                                        value += float(data["value"])
                                    except (TypeError, ValueError):
                                        pass
                    
                    group_council_count += len(group_council_chunk)
                    if group_council_count % 10 == 0:
                        elapsed = check_timeout()  # Will raise TimeoutError if exceeded
                        print(f"  Group {gc.name}: Processed {group_council_count}/{total_group_councils} councils... ({elapsed:.1f}s elapsed)")
                        
                        # Check connection health periodically
                        ensure_connection()
                year_label = gc.year.label if gc.year else "all"
                # Cache for 24 hours instead of forever to avoid stale data
                cache.set(f"counter_total:{gc.slug}:{year_label}", value, 86400)
                
                if gc.year:
                    # And again store the previous year so the home page can
                    # illustrate change over time.
                    prev_label = previous_year_label(gc.year.label)
                    if prev_label:
                        def get_group_prev_year():
                            return FinancialYear.objects.filter(label=prev_label).first()
                        
                        prev_year = safe_database_operation(get_group_prev_year)
                        if prev_year:
                            prev_value = 0.0
                            print(f"Calculating group counter {gc.name} previous year ({prev_label})...")
                            
                            prev_group_council_count = 0
                            
                            # Process previous year for group councils in chunks
                            for prev_group_council_chunk in chunked_database_operation(councils_queryset, chunk_size=10):
                                for council in prev_group_council_chunk:
                                    try:
                                        # Use cached service for previous year too
                                        cached_value = counter_cache_service.get_counter_value(
                                            counter_slug=gc.counter.slug,
                                            council_slug=council.slug,
                                            year_label=prev_year.label,
                                            allow_expensive_calculation=False
                                        )
                                        if cached_value and cached_value > 0:
                                            prev_value += float(cached_value)
                                    except Exception as e:
                                        # Fallback
                                        data = agent.run(council_slug=council.slug, year_label=prev_year.label).get(gc.counter.slug)
                                        if data and data.get("value") is not None:
                                            try:
                                                prev_value += float(data["value"])
                                            except (TypeError, ValueError):
                                                pass
                                
                                prev_group_council_count += len(prev_group_council_chunk)
                                if prev_group_council_count % 10 == 0:
                                    elapsed = check_timeout()  # Will raise TimeoutError if exceeded
                                    print(f"  Group {gc.name} prev year: Processed {prev_group_council_count}/{total_group_councils} councils... ({elapsed:.1f}s elapsed)")
                                    
                                    # Check connection health periodically
                                    ensure_connection()
                            
                            cache.set(f"counter_total:{gc.slug}:{year_label}:prev", prev_value, 86400)
