from django.test import TestCase
from django.urls import reverse

from council_finance.models import Council, FinancialYear, DataField, CounterDefinition


class ShareLinkTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Test", slug="test")
        self.year = FinancialYear.objects.create(label="2024")
        field = DataField.objects.create(slug="total_debt", name="Total Debt")
        CounterDefinition.objects.create(
            name="Debt",
            slug="debt",
            formula="total_debt",
            precision=0,
            show_currency=False,
        )

    def test_generate_link_returns_url(self):
        url = reverse("generate_share_link", args=["test"])
        resp = self.client.get(
            url,
            {
                "year": "2024",
                "counters": "debt",
                "precision": "1",
                "thousands": "true",
                "friendly": "true",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("?share=", resp.json()["url"])

    def test_link_restores_settings(self):
        url = reverse("generate_share_link", args=["test"])
        resp = self.client.get(url, {"year": "2024", "counters": "debt"})
        link = resp.json()["url"]
        resp2 = self.client.get(link)
        self.assertEqual(resp2.context["share_data"]["counters"], ["debt"])
        self.assertEqual(resp2.context["share_data"]["year"], "2024")
