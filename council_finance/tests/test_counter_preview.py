from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import Council, FinancialYear, FigureSubmission


class CounterPreviewTest(TestCase):
    """Ensure the preview endpoint reports missing values."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff", email="s@example.com", password="pass", is_staff=True
        )
        self.client.login(username="staff", password="pass")

    def test_preview_with_blank_value(self):
        council = Council.objects.create(name="Test", slug="test")
        year = FinancialYear.objects.create(label="2025")
        # Store an empty string and flag the value as missing.
        FigureSubmission.objects.create(
            council=council,
            year=year,
            field_name="total_debt",
            value="",
            needs_populating=True,
        )
        url = reverse("preview_counter_value")
        resp = self.client.get(
            url,
            {
                "council": "test",
                "year": "2025",
                "formula": "total_debt",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Counter failed", resp.json()["error"])
