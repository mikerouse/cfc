"""Optimized agent for calculating site-wide counter totals efficiently."""

from django.core.cache import cache
from django.db.models import Sum, Q
from decimal import Decimal
import time
import logging

from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    SiteCounter,
    GroupCounter,
    FinancialFigure,
    DataField,
    CounterDefinition
)
from council_finance.year_utils import previous_year_label

logger = logging.getLogger(__name__)


class SiteTotalsAgentOptimized(AgentBase):
    """Efficiently compute and cache totals for promoted counters using direct database queries."""
    
    name = "SiteTotalsAgentOptimized"
    
    def run(self, **kwargs):
        """Aggregate counter values across councils using efficient database queries."""
        start_time = time.time()
        all_years = list(FinancialYear.objects.order_by("-label"))
        
        # Process site counters
        for sc in SiteCounter.objects.all():
            counter_start = time.time()
            
            # Get the counter definition to understand what we're calculating
            counter_def = sc.counter
            
            # Calculate value based on counter formula
            value = self._calculate_counter_total(counter_def, sc.year, all_years)
            
            year_label = sc.year.label if sc.year else "all"
            cache_key = f"counter_total:{sc.slug}:{year_label}"
            cache.set(cache_key, float(value), 86400)  # Cache for 24 hours
            
            logger.info(f"Calculated {sc.name}: {value:,.2f} in {time.time() - counter_start:.2f}s")
            
            # Calculate previous year value if needed
            if sc.year:
                prev_label = previous_year_label(sc.year.label)
                if prev_label:
                    prev_year = FinancialYear.objects.filter(label=prev_label).first()
                    if prev_year:
                        prev_value = self._calculate_counter_total(counter_def, prev_year, all_years)
                        cache.set(f"{cache_key}:prev", float(prev_value), 86400)
                        logger.info(f"Calculated {sc.name} (prev): {prev_value:,.2f}")
        
        # Process group counters
        for gc in GroupCounter.objects.all():
            counter_start = time.time()
            
            # Resolve the set of councils this group counter applies to
            councils_q = Q()
            if gc.councils.exists():
                councils_q &= Q(id__in=gc.councils.values_list('id', flat=True))
            if gc.council_list_id:
                councils_q &= Q(id__in=gc.council_list.councils.values_list('id', flat=True))
            if gc.council_types.exists():
                councils_q &= Q(council_type__in=gc.council_types.all())
            
            # If no filters, include all councils
            if not councils_q:
                councils_q = Q()
            
            counter_def = gc.counter
            value = self._calculate_counter_total(counter_def, gc.year, all_years, councils_q)
            
            year_label = gc.year.label if gc.year else "all"
            cache_key = f"counter_total:{gc.slug}:{year_label}"
            cache.set(cache_key, float(value), 86400)
            
            logger.info(f"Calculated {gc.name}: {value:,.2f} in {time.time() - counter_start:.2f}s")
            
            # Previous year for group counters
            if gc.year:
                prev_label = previous_year_label(gc.year.label)
                if prev_label:
                    prev_year = FinancialYear.objects.filter(label=prev_label).first()
                    if prev_year:
                        prev_value = self._calculate_counter_total(counter_def, prev_year, all_years, councils_q)
                        cache.set(f"{cache_key}:prev", float(prev_value), 86400)
        
        total_time = time.time() - start_time
        logger.info(f"SiteTotalsAgentOptimized completed in {total_time:.2f}s")
    
    def _calculate_counter_total(self, counter_def, year, all_years, councils_q=None):
        """Calculate total for a specific counter across councils using efficient queries."""
        
        # Parse the counter formula to determine what fields we need
        # For now, handle simple field references like "(total-debt)"
        formula = counter_def.formula
        
        if formula.startswith('(') and formula.endswith(')'):
            # Simple field reference
            field_slug = formula[1:-1]
            
            # Build the query
            query = FinancialFigure.objects.filter(field__slug=field_slug)
            
            # Apply council filter if provided
            if councils_q is not None:
                query = query.filter(council__in=Council.objects.filter(councils_q))
            
            # Apply year filter
            if year:
                query = query.filter(year=year)
            else:
                # All years
                query = query.filter(year__in=all_years)
            
            # Use database aggregation for efficiency
            result = query.aggregate(total=Sum('value'))
            return Decimal(str(result['total'] or 0))
        
        else:
            # Complex formula - for now, return 0
            # TODO: Implement formula parsing and calculation
            logger.warning(f"Complex formula not yet supported: {formula}")
            return Decimal('0')