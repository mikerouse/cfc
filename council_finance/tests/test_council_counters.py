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
        )
        CouncilCounter.objects.create(council=self.council, counter=self.counter)

    def test_endpoint_returns_counter_value(self):
        url = reverse("council_counters", args=["test"])
        resp = self.client.get(url, {"year": "2024"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["counters"]["debt"]
        self.assertEqual(data["value"], 100.0)
        self.assertEqual(data["formatted"], "100")
