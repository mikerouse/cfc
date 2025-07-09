from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class GodModeAccessTests(TestCase):
    """Ensure the God Mode link and view are accessible to superadmins."""

    def setUp(self):
        # Create a superuser who should bypass the tier restriction
        self.superuser = get_user_model().objects.create_superuser(
            username="boss", email="boss@example.com", password="secret"
        )

    def test_superuser_sees_link(self):
        """The secondary nav should include God Mode for superusers."""
        self.client.login(username="boss", password="secret")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, reverse("god_mode"))

    def test_superuser_can_access_view(self):
        """The God Mode page itself should load for superusers."""
        self.client.login(username="boss", password="secret")
        resp = self.client.get(reverse("god_mode"))
        self.assertEqual(resp.status_code, 200)

    def test_reconcile_button_updates_population(self):
        """POSTing the reconcile button should refresh cached populations."""
        self.client.login(username="boss", password="secret")

        from council_finance.models import Council, DataField, FinancialYear, FigureSubmission

        field, _ = DataField.objects.get_or_create(
            slug="population", defaults={"name": "Population", "content_type": "integer"}
        )
        year = FinancialYear.objects.create(label="2024/25")
        council = Council.objects.create(name="City Council", slug="city")
        FigureSubmission.objects.create(council=council, year=year, field=field, value="123")
        council.latest_population = None
        council.save(update_fields=["latest_population"])

        self.client.post(reverse("god_mode"), {"reconcile_population": "1"})
        council.refresh_from_db()
        self.assertEqual(council.latest_population, 123)

    def test_assess_button_clears_characteristic_duplicates(self):
        """Running the assess button should remove year-specific issues for
        characteristic fields."""

        self.client.login(username="boss", password="secret")

        from council_finance.models import (
            Council,
            DataField,
            FinancialYear,
            DataIssue,
        )

        field = DataField.objects.create(name="Location", slug="council_hq_post_code")
        council = Council.objects.create(name="Aberdeen City Council", slug="aberdeen")
        year = FinancialYear.objects.create(label="2024/25")

        # Simulate stale issues that include a year-specific entry
        DataIssue.objects.create(council=council, field=field, year=year, issue_type="missing")
        DataIssue.objects.create(council=council, field=field, issue_type="missing")

        # Trigger the button which internally calls ``assess_data_issues``
        self.client.post(reverse("god_mode"), {"assess_issues": "1"})

        issues = DataIssue.objects.filter(council=council, field=field)
        self.assertEqual(issues.count(), 1)
        self.assertIsNone(issues.first().year_id)
