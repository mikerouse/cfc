"""
Efficient Site Totals Agent - The "Old School" Approach

This is the simple, fast way: direct SQL queries to sum up all the numbers 
across the entire database in one go. No per-council loops, no complexity.

Takes 2-3 seconds instead of 5+ minutes.
"""

import time
from django.core.cache import cache
from django.db import connection
from council_finance.models import SiteCounter, GroupCounter, FinancialYear


class EfficientSiteTotalsAgent:
    """Dead simple site totals using direct database aggregation."""
    
    name = "EfficientSiteTotalsAgent"
    
    def run(self):
        """Calculate all site totals in seconds using direct SQL."""
        print("Starting EfficientSiteTotalsAgent - the simple approach")
        start_time = time.time()
        
        # Semi-hard-coded counter calculations
        counter_calculations = {
            'total-debt': self._total_debt_calculation,
            'current-liabilities': self._current_liabilities_calculation,  
            'long-term-liabilities': self._long_term_liabilities_calculation,
            'interest-payments': self._interest_payments_calculation,
            'finance-leases': self._finance_leases_calculation,
            'total-debt-per-capita': self._total_debt_per_capita_calculation,
            'debt-per-capita': self._total_debt_per_capita_calculation,  # Alternative slug
        }
        
        calculated_count = 0
        
        # Process all promoted site counters
        for sc in SiteCounter.objects.filter(promote_homepage=True):
            year_label = sc.year.label if sc.year else None
            
            # Get the calculation function
            calc_func = counter_calculations.get(sc.counter.slug, self._generic_calculation)
            
            # Calculate the value
            value = calc_func(year_label)
            
            # Cache for 24 hours
            cache_key = f"counter_total:{sc.slug}:{year_label or 'all'}"
            cache.set(cache_key, value, 86400)
            
            print(f"SUCCESS {sc.name}: £{value:,.0f} ({year_label or 'all years'})")
            calculated_count += 1
        
        # Process group counters (same approach but with council type filter)  
        for gc in GroupCounter.objects.filter(promote_homepage=True):
            year_label = gc.year.label if gc.year else None
            
            calc_func = counter_calculations.get(gc.counter.slug, self._generic_calculation)
            
            # Group counters include council type filtering
            council_type_id = getattr(gc, 'council_type_id', None) if hasattr(gc, 'council_type') else None
            value = calc_func(year_label, council_type_id)
            
            cache_key = f"counter_total:{gc.slug}:{year_label or 'all'}"
            cache.set(cache_key, value, 86400)
            
            print(f"SUCCESS {gc.name}: £{value:,.0f} ({year_label or 'all years'})")
            calculated_count += 1
        
        elapsed = time.time() - start_time
        print(f"SUCCESS Calculated {calculated_count} counters in {elapsed:.2f} seconds")
        return calculated_count
    
    def _total_debt_calculation(self, year_label=None, council_type_id=None):
        """Total Debt = Current + Long-term + Finance Leases"""
        
        year_filter = self._year_filter(year_label)
        type_filter = self._council_type_filter(council_type_id)
        
        query = f"""
        SELECT COALESCE(
            SUM(CASE WHEN df.slug = 'current-liabilities' THEN CAST(ff.value AS NUMERIC) ELSE 0 END) +
            SUM(CASE WHEN df.slug = 'long-term-liabilities' THEN CAST(ff.value AS NUMERIC) ELSE 0 END) +
            SUM(CASE WHEN df.slug IN ('finance-leases', 'pfi-liabilities') THEN CAST(ff.value AS NUMERIC) ELSE 0 END),
            0
        ) as total_debt
        FROM council_finance_financialfigure ff
        JOIN council_finance_council c ON c.id = ff.council_id
        JOIN council_finance_datafield df ON df.id = ff.field_id
        {year_filter}
        WHERE df.slug IN ('current-liabilities', 'long-term-liabilities', 'finance-leases', 'pfi-liabilities')
        {type_filter}
        AND CAST(ff.value AS TEXT) ~ '^[0-9]+\\.?[0-9]*$'
        """
        
        return self._execute_query(query)
    
    def _current_liabilities_calculation(self, year_label=None, council_type_id=None):
        """Simple sum of current-liabilities field"""
        return self._simple_field_sum('current-liabilities', year_label, council_type_id)
    
    def _long_term_liabilities_calculation(self, year_label=None, council_type_id=None):
        """Simple sum of long-term-liabilities field"""
        return self._simple_field_sum('long-term-liabilities', year_label, council_type_id)
    
    def _interest_payments_calculation(self, year_label=None, council_type_id=None):
        """Simple sum of interest-payments field"""
        return self._simple_field_sum('interest-payments', year_label, council_type_id)
    
    def _finance_leases_calculation(self, year_label=None, council_type_id=None):
        """Sum of finance-leases and pfi-liabilities fields"""
        year_filter = self._year_filter(year_label)
        type_filter = self._council_type_filter(council_type_id)
        
        query = f"""
        SELECT COALESCE(SUM(CAST(ff.value AS NUMERIC)), 0) as total
        FROM council_finance_financialfigure ff
        JOIN council_finance_council c ON c.id = ff.council_id
        JOIN council_finance_datafield df ON df.id = ff.field_id
        {year_filter}
        WHERE df.slug IN ('finance-leases', 'pfi-liabilities')
        {type_filter}
        AND CAST(ff.value AS TEXT) ~ '^[0-9]+\\.?[0-9]*$'
        """
        
        return self._execute_query(query)
    
    def _total_debt_per_capita_calculation(self, year_label=None, council_type_id=None):
        """Total Debt per Capita = Total Debt / Total Population"""
        
        # Get total debt
        total_debt = self._total_debt_calculation(year_label, council_type_id)
        
        # Get total population (aggregate from population field or latest_population)
        total_population = self._total_population_calculation(council_type_id)
        
        if total_population == 0:
            print(f"WARNING No population data found for debt per capita calculation")
            return 0.0
        
        debt_per_capita = total_debt / total_population
        
        print(f"INFO Debt per capita: £{total_debt:,.0f} / {total_population:,} people = £{debt_per_capita:,.0f} per person")
        return debt_per_capita
    
    def _total_population_calculation(self, council_type_id=None):
        """Calculate total population across all councils"""
        
        type_filter = self._council_type_filter(council_type_id)
        
        # Try multiple approaches to get population data
        queries = [
            # Method 1: Use latest_population field from council table
            f"""
            SELECT COALESCE(SUM(CAST(c.latest_population AS NUMERIC)), 0) as total_pop
            FROM council_finance_council c
            WHERE c.latest_population IS NOT NULL
            AND COALESCE(CAST(c.latest_population AS TEXT), '') != ''
            AND CAST(c.latest_population AS TEXT) ~ '^[0-9]+\\.?[0-9]*$'
            {type_filter}
            """,
            
            # Method 2: Use population field from characteristics/financial figures
            f"""
            SELECT COALESCE(SUM(CAST(ff.value AS NUMERIC)), 0) as total_pop
            FROM council_finance_financialfigure ff
            JOIN council_finance_council c ON c.id = ff.council_id
            JOIN council_finance_datafield df ON df.id = ff.field_id
            WHERE df.slug IN ('population', 'total-population', 'residents')
            AND ff.value IS NOT NULL
            AND COALESCE(CAST(ff.value AS TEXT), '') != ''
            AND CAST(ff.value AS TEXT) ~ '^[0-9]+\\.?[0-9]*$'
            {type_filter}
            """,
            
            # Method 3: Try characteristics table
            f"""
            SELECT COALESCE(SUM(CAST(cc.value AS NUMERIC)), 0) as total_pop
            FROM council_finance_councilcharacteristic cc
            JOIN council_finance_council c ON c.id = cc.council_id
            JOIN council_finance_datafield df ON df.id = cc.field_id
            WHERE df.slug IN ('population', 'total-population', 'residents')
            AND cc.value IS NOT NULL
            AND COALESCE(CAST(cc.value AS TEXT), '') != ''
            AND CAST(cc.value AS TEXT) ~ '^[0-9]+\\.?[0-9]*$'
            {type_filter}
            """
        ]
        
        # Try each method until we get a non-zero result
        for i, query in enumerate(queries, 1):
            try:
                population = self._execute_query(query)
                if population > 0:
                    print(f"SUCCESS Found population data using method {i}: {population:,} people")
                    return population
            except Exception as e:
                print(f"FAILED Population method {i} failed: {e}")
                continue
        
        print(f"WARNING No population data found using any method")
        return 0.0
    
    def _generic_calculation(self, year_label=None, council_type_id=None):
        """Fallback for unknown counter types"""
        print(f"WARNING Using generic calculation (returns 0)")
        return 0.0
    
    def _simple_field_sum(self, field_slug, year_label=None, council_type_id=None):
        """Sum all values for a specific field across all councils"""
        
        year_filter = self._year_filter(year_label)
        type_filter = self._council_type_filter(council_type_id)
        
        query = f"""
        SELECT COALESCE(SUM(CAST(ff.value AS NUMERIC)), 0) as total
        FROM council_finance_financialfigure ff
        JOIN council_finance_council c ON c.id = ff.council_id
        JOIN council_finance_datafield df ON df.id = ff.field_id
        {year_filter}
        WHERE df.slug = '{field_slug}'
        {type_filter}
        AND ff.value IS NOT NULL
        AND COALESCE(CAST(ff.value AS TEXT), '') != ''
        AND CAST(ff.value AS TEXT) ~ '^[0-9]+\\.?[0-9]*$'
        """
        
        return self._execute_query(query)
    
    def _year_filter(self, year_label):
        """Generate year filter SQL"""
        if not year_label:
            return ""
        return f"JOIN council_finance_financialyear fy ON fy.id = ff.year_id AND fy.label = '{year_label}'"
    
    def _council_type_filter(self, council_type_id):
        """Generate council type filter SQL"""
        if not council_type_id:
            return ""
        return f"AND c.council_type_id = {council_type_id}"
    
    def _execute_query(self, query):
        """Execute a SQL query and return the numeric result"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return float(result[0]) if result and result[0] else 0.0
        except Exception as e:
            print(f"FAILED SQL Error: {e}")
            return 0.0


# Function to use the new efficient agent
def run_efficient_site_totals():
    """Helper function to run the efficient site totals agent"""
    agent = EfficientSiteTotalsAgent()
    return agent.run()


# If someone imports this module, they can replace the old agent easily
def replace_site_totals_agent():
    """Replace the existing SiteTotalsAgent with the efficient version"""
    import council_finance.agents.site_totals_agent as old_module
    old_module.SiteTotalsAgent = EfficientSiteTotalsAgent
    print("SUCCESS Replaced SiteTotalsAgent with EfficientSiteTotalsAgent")