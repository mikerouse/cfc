from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import (
    Council,
    DataField,
    FinancialYear,
    Contribution,
    DataChangeLog,
)


class ChangeLogViewTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Town", slug="town")
        self.user = get_user_model().objects.create_user(
            username="alice", email="a@example.com", password="pw"
        )
        self.field, _ = DataField.objects.get_or_create(
            slug="council_website", defaults={"name": "Website"}
        )
        self.year = FinancialYear.objects.create(label="2024")
        # Create more than one page of log entries
        for i in range(25):
            contrib = Contribution.objects.create(
                user=self.user,
                council=self.council,
                field=self.field,
                year=self.year,
                value=f"http://new{i}.com",
                status="approved",
            )
            DataChangeLog.objects.create(
                contribution=contrib,
                council=self.council,
                field=self.field,
                year=self.year,
                old_value=f"http://old{i}.com",
                new_value=f"http://new{i}.com",
                approved_by=self.user,
            )

    def test_detail_page_links_to_log(self):
        resp = self.client.get(reverse("council_detail", args=["town"]))
        self.assertContains(resp, reverse("council_change_log", args=["town"]))

    def test_log_page_displays_entries(self):
        resp = self.client.get(reverse("council_change_log", args=["town"]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Page 1 of 2")
        self.assertContains(resp, self.user.username)
        self.assertContains(resp, "http://new24.com")

