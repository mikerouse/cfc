from django.test import TestCase
from django.urls import reverse

from council_finance.models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    CounterDefinition,
    CouncilCounter,
)


class CouncilCountersTest(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Test", slug="test")
        self.year = FinancialYear.objects.create(label="2024")
        self.field = DataField.objects.create(slug="total_debt", name="Total Debt")
        FigureSubmission.objects.create(
            council=self.council,
            year=self.year,
            field=self.field,
            value="100",
        )
        self.counter = CounterDefinition.objects.create(
            name="Debt",
            slug="debt",
            formula="total_debt",
            precision=0,
            show_currency=False,
            show_by_default=False,
        )
        CouncilCounter.objects.create(council=self.council, counter=self.counter)

    def test_endpoint_returns_counter_value(self):
        url = reverse("council_counters", args=["test"])
        resp = self.client.get(url, {"year": "2024"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["counters"]["debt"]
        self.assertEqual(data["value"], 100.0)
        self.assertEqual(data["formatted"], "100")

    def test_show_by_default_counter_included(self):
        other = CounterDefinition.objects.create(
            name="Debt2",
            slug="debt2",
            formula="total_debt",
            precision=0,
            show_currency=False,
            show_by_default=True,
        )
        url = reverse("council_counters", args=["test"])
        resp = self.client.get(url, {"year": "2024"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("debt2", resp.json()["counters"])

    def test_disabled_override_excludes_counter(self):
        other = CounterDefinition.objects.create(
            name="Debt3",
            slug="debt3",
            formula="total_debt",
            precision=0,
            show_currency=False,
            show_by_default=True,
        )
        CouncilCounter.objects.create(
            council=self.council,
            counter=other,
            enabled=False,
        )
        url = reverse("council_counters", args=["test"])
        resp = self.client.get(url, {"year": "2024"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("debt3", resp.json()["counters"])

    def test_detail_page_respects_show_by_default(self):
        other = CounterDefinition.objects.create(
            name="Detail",
            slug="detail",
            formula="total_debt",
            precision=0,
            show_currency=False,
        )
        resp = self.client.get(reverse("council_detail", args=["test"]))
        slugs = [item["counter"].slug for item in resp.context["counters"]]
        self.assertIn("detail", slugs)

    def test_endpoint_includes_format_fields(self):
        url = reverse("council_counters", args=["test"])
        resp = self.client.get(url, {"year": "2024"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["counters"]["debt"]
        self.assertIn("precision", data)
        self.assertIn("show_currency", data)
        self.assertIn("friendly_format", data)
