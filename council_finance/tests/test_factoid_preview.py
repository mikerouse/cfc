from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    CounterDefinition,
)


class FactoidPreviewTests(TestCase):
    """Verify the preview endpoint renders factoid text."""

    def setUp(self):
        # Minimal data for a percent change factoid
        self.user = get_user_model().objects.create_user(
            username="staff", email="s@example.com", password="pass", is_staff=True
        )
        self.client.login(username="staff", password="pass")

        self.council = Council.objects.create(name="A", slug="a")
        self.field = DataField.objects.create(name="Debt", slug="debt")
        self.prev_year = FinancialYear.objects.create(label="2024")
        self.curr_year = FinancialYear.objects.create(label="2025")
        FigureSubmission.objects.create(
            council=self.council, year=self.prev_year, field=self.field, value="100"
        )
        FigureSubmission.objects.create(
            council=self.council, year=self.curr_year, field=self.field, value="110"
        )
        self.counter = CounterDefinition.objects.create(name="Debt", slug="debt", formula="debt")
        self.factoid_text = "{value} change"

    def test_preview_with_counter_id(self):
        """Counter ID values should be accepted by the preview view."""
        url = reverse("preview_factoid")
        resp = self.client.get(
            url,
            {
                "counter": self.counter.pk,
                "council": self.council.slug,
                "year": self.curr_year.label,
                "type": "percent_change",
                "text": self.factoid_text,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("10.0%", resp.json().get("text", ""))

    def test_no_previous_data_error(self):
        """An error should be returned when prior year data is missing."""
        url = reverse("preview_factoid")
        resp = self.client.get(
            url,
            {
                "counter": self.counter.slug,
                "council": self.council.slug,
                "year": self.prev_year.label,
                "type": "percent_change",
                "text": self.factoid_text,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "No previous data to compare")

    def test_no_current_data_error(self):
        year_next = FinancialYear.objects.create(label="2026")
        url = reverse("preview_factoid")
        resp = self.client.get(
            url,
            {
                "counter": self.counter.slug,
                "council": self.council.slug,
                "year": year_next.label,
                "type": "percent_change",
                "text": self.factoid_text,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "No data for the selected year")
