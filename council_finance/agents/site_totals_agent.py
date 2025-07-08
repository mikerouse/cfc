"""Agent responsible for caching totals used on the home page."""

from django.core.cache import cache
from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    SiteCounter,
    GroupCounter,
)
from council_finance.factoids import previous_year_label
from .counter_agent import CounterAgent

class SiteTotalsAgent(AgentBase):
    """Compute and cache totals for promoted counters."""

    name = "SiteTotalsAgent"

    def run(self, **kwargs):
        """Aggregate counter values across councils and store in the cache."""
        # Use the existing CounterAgent to compute individual council figures.
        agent = CounterAgent()
        # A list of all available years allows counters that span multiple
        # years to be aggregated without additional queries later.
        all_years = list(FinancialYear.objects.order_by("-label"))

        for sc in SiteCounter.objects.all():
            # Sum the value of ``sc.counter`` across either a specific year or
            # every year when none is selected.
            value = 0.0
            years = [sc.year] if sc.year else all_years
            for council in Council.objects.all():
                for yr in years:
                    data = agent.run(council_slug=council.slug, year_label=yr.label).get(sc.counter.slug)
                    if data and data.get("value") is not None:
                        try:
                            value += float(data["value"])
                        except (TypeError, ValueError):
                            pass
            year_label = sc.year.label if sc.year else "all"
            cache.set(f"counter_total:{sc.slug}:{year_label}", value, None)
            if sc.year:
                # Record the previous year's total so percentage change factoids
                # can be generated without additional database work.
                prev_label = previous_year_label(sc.year.label)
                if prev_label:
                    prev_year = FinancialYear.objects.filter(label=prev_label).first()
                    if prev_year:
                        prev_value = 0.0
                        for council in Council.objects.all():
                            data = agent.run(council_slug=council.slug, year_label=prev_year.label).get(sc.counter.slug)
                            if data and data.get("value") is not None:
                                try:
                                    prev_value += float(data["value"])
                                except (TypeError, ValueError):
                                    pass
                        cache.set(f"counter_total:{sc.slug}:{year_label}:prev", prev_value, None)

        for gc in GroupCounter.objects.all():
            # Resolve the set of councils this group counter applies to.
            councils = Council.objects.all()
            if gc.councils.exists():
                councils = gc.councils.all()
            if gc.council_list_id:
                councils = councils & gc.council_list.councils.all()
            if gc.council_types.exists():
                councils = councils.filter(council_type__in=gc.council_types.all())

            value = 0.0
            years = [gc.year] if gc.year else all_years
            for council in councils:
                for yr in years:
                    data = agent.run(council_slug=council.slug, year_label=yr.label).get(gc.counter.slug)
                    if data and data.get("value") is not None:
                        try:
                            value += float(data["value"])
                        except (TypeError, ValueError):
                            pass
            year_label = gc.year.label if gc.year else "all"
            cache.set(f"counter_total:{gc.slug}:{year_label}", value, None)
            if gc.year:
                # And again store the previous year so the home page can
                # illustrate change over time.
                prev_label = previous_year_label(gc.year.label)
                if prev_label:
                    prev_year = FinancialYear.objects.filter(label=prev_label).first()
                    if prev_year:
                        prev_value = 0.0
                        for council in councils:
                            data = agent.run(council_slug=council.slug, year_label=prev_year.label).get(gc.counter.slug)
                            if data and data.get("value") is not None:
                                try:
                                    prev_value += float(data["value"])
                                except (TypeError, ValueError):
                                    pass
                        cache.set(f"counter_total:{gc.slug}:{year_label}:prev", prev_value, None)
