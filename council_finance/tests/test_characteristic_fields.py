from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from django.core.management import call_command

from council_finance.models import (
    DataField,
    Council,
    FinancialYear,
    DataIssue,
)

class CharacteristicFieldTests(TestCase):
    def test_protected_slug_sets_category(self):
        """Any known characteristic slug should default to the characteristic
        category when created."""

        for slug in ["council_website", "elected_members"]:
            field, _ = DataField.objects.get_or_create(
                slug=slug, defaults={"name": slug.replace("_", " ").title()}
            )
            self.assertEqual(field.category, "characteristic")

class CharacteristicTabTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", email="a@example.com", password="pw"
        )
        DataField.objects.create(name="Headquarters", slug="council_location")

    def test_tab_visible_in_manager(self):
        self.client.login(username="admin", password="pw")
        resp = self.client.get(reverse("field_list"))
        self.assertContains(resp, "Characteristics")


class YearlessCharacteristicTests(TestCase):
    """Verify missing-data checks treat characteristics as yearless."""

    def test_missing_issue_created_once(self):
        year1 = FinancialYear.objects.create(label="2023/24")
        year2 = FinancialYear.objects.create(label="2024/25")
        council = Council.objects.create(name="Solo", slug="solo")
        field = DataField.objects.create(name="HQ", slug="council_location")

        # Trigger data quality assessment without any submissions present.
        call_command("assess_data_issues")

        issues = DataIssue.objects.filter(council=council, field=field)
        self.assertEqual(issues.count(), 1)
        self.assertIsNone(issues.first().year_id)
