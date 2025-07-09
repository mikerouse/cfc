from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import Council, DataField, FinancialYear


class EditInterfaceTest(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="EditTown", slug="edit-town")
        self.year = FinancialYear.objects.create(label="2025")
        self.field = DataField.objects.create(name="Total Debt", slug="total_debt")
        self.user = get_user_model().objects.create_user(username="staff", password="pw", is_staff=True)
        self.client.login(username="staff", password="pw")

    def test_edit_table_includes_blank_row(self):
        url = reverse("edit_figures_table", args=["edit-town"])
        resp = self.client.get(
            url,
            {"year": "2025"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Total Debt")
        self.assertContains(resp, f"name=\"field\" value=\"{self.field.slug}\"")

