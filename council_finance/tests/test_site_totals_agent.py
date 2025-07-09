from django.test import TestCase
from django.core.cache import cache
from council_finance.models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    CounterDefinition,
    SiteCounter,
    GroupCounter,
)

from council_finance.agents.site_totals_agent import SiteTotalsAgent


class SiteTotalsAgentTest(TestCase):
    """Verify totals are cached for both site and group counters."""

    def setUp(self):
        self.year = FinancialYear.objects.create(label="2024")
        self.c1 = Council.objects.create(name="A", slug="a")
        self.c2 = Council.objects.create(name="B", slug="b")
        self.field = DataField.objects.create(name="Debt", slug="total_debt")
        FigureSubmission.objects.create(council=self.c1, year=self.year, field=self.field, value="50")
        FigureSubmission.objects.create(council=self.c2, year=self.year, field=self.field, value="70")
        self.counter = CounterDefinition.objects.create(name="Debt", slug="debt", formula="total_debt", precision=0)
        self.site_counter = SiteCounter.objects.create(name="Site Debt", slug="site-debt", counter=self.counter, year=self.year)
        self.group_counter = GroupCounter.objects.create(name="Group Debt", slug="group-debt", counter=self.counter, year=self.year)
        self.group_counter.councils.add(self.c1)
        cache.clear()
        self.agent = SiteTotalsAgent()

    def test_cache_populated_with_totals(self):
        """Running the agent stores totals for both counter types."""
        self.agent.run()
        site_key = f"counter_total:{self.site_counter.slug}:{self.year.label}"
        group_key = f"counter_total:{self.group_counter.slug}:{self.year.label}"
        self.assertEqual(cache.get(site_key), 120.0)
        self.assertEqual(cache.get(group_key), 50.0)
