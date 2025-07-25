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
        char_field = DataField.objects.create(name="HQ", slug="council_hq_post_code", category="characteristic")
        DataIssue.objects.create(council=self.council, field=char_field, issue_type="missing")

        url = reverse("data_issues_table") + "?type=missing&category=characteristic"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertIn("HQ", resp.json()["html"])

    def test_page_size_parameter(self):
        url = reverse("data_issues_table") + "?type=missing&page_size=10"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertIn("Page 1 of 6", resp.json()["html"])

    def test_sort_by_field(self):
        field_a = DataField.objects.create(name="Alpha", slug="alpha")
        DataIssue.objects.create(council=self.council, field=field_a, year=self.year, issue_type="missing")
        url = reverse("data_issues_table") + "?type=missing&order=field&dir=asc"
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        html = resp.json()["html"]
        self.assertLess(html.index("Alpha"), html.index("Stuff0"))

    def test_refresh_parameter_triggers_rebuild(self):
        old_field = DataField.objects.create(name="Old", slug="old")
        DataIssue.objects.create(council=self.council, field=old_field, issue_type="missing")
        DataField.objects.create(name="New", slug="new")
        old_id = old_field.id
        old_field.delete()
        url = reverse("data_issues_table") + "?type=missing&refresh=1"
        self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        from council_finance.models import DataIssue as DI, DataField as DF
        new_field = DF.objects.get(slug="new")
        self.assertTrue(DI.objects.filter(field=new_field).exists())
        self.assertFalse(DI.objects.filter(field_id=old_id).exists())
