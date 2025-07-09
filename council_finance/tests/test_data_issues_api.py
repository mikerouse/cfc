from django.test import TestCase
from django.urls import reverse
from council_finance.models import Council, DataField, FinancialYear, DataIssue


class DataIssuesApiTests(TestCase):
    def setUp(self):
        self.year = FinancialYear.objects.create(label="2025")
        self.council = Council.objects.create(name="Test Council", slug="test")
        for i in range(55):
            field = DataField.objects.create(name=f"Stuff{i}", slug=f"stuff{i}")
            DataIssue.objects.create(
                council=self.council,
                field=field,
                year=self.year,
                issue_type="missing",
            )

    def test_fetch_first_page(self):
        url = reverse("data_issues_table") + "?type=missing"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Test Council", resp.json()["html"])

    def test_pagination_second_page(self):
        url = reverse("data_issues_table") + "?type=missing&page=2"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Page 2", resp.json()["html"])

    def test_invalid_type_returns_error(self):
        url = reverse("data_issues_table") + "?type=bad"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 400)

    def test_category_filter(self):
        """Filtering by category should only return matching issues."""
        char_field = DataField.objects.create(name="HQ", slug="council_location", category="characteristic")
        DataIssue.objects.create(council=self.council, field=char_field, issue_type="missing")

        url = reverse("data_issues_table") + "?type=missing&category=characteristic"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertIn("HQ", resp.json()["html"])
