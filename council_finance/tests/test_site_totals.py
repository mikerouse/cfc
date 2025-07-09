from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from council_finance.models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    CounterDefinition,
    SiteCounter,
)


class SiteTotalsCacheTest(TestCase):
    def setUp(self):
        self.year = FinancialYear.objects.create(label="2024")
        self.council = Council.objects.create(name="Demo", slug="demo")
        self.field = DataField.objects.create(name="Total Debt", slug="total_debt")
        FigureSubmission.objects.create(
            council=self.council, year=self.year, field=self.field, value="50"
        )
        self.counter = CounterDefinition.objects.create(
            name="Debt", slug="debt", formula="total_debt", precision=0
        )
        self.site_counter = SiteCounter.objects.create(
            name="All Debt",
            slug="all-debt",
            counter=self.counter,
            year=self.year,
            promote_homepage=True,
        )

    def test_home_recomputes_zero_cache(self):
        key = f"counter_total:{self.site_counter.slug}:{self.year.label}"
        cache.set(key, 0)
        resp = self.client.get(reverse("home"))
        promoted = resp.context["promoted_counters"][0]
        self.assertEqual(promoted["slug"], self.site_counter.slug)
        self.assertGreater(promoted["raw"], 0)

