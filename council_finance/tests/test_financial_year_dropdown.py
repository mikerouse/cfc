from django.test import TestCase
from django.urls import reverse

from council_finance.models import Council, FinancialYear, SiteSetting
from council_finance.views import current_financial_year_label


class FinancialYearDropdownTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Test", slug="test")

    def test_default_year_from_setting(self):
        fy1 = FinancialYear.objects.create(label="2022/23")
        FinancialYear.objects.create(label="2023/24")
        SiteSetting.objects.update_or_create(
            key="default_financial_year", defaults={"value": "2022/23"}
        )

        resp = self.client.get(reverse("council_detail", args=["test"]))
        self.assertEqual(resp.context["selected_year"].label, fy1.label)

    def test_current_year_label_display(self):
        label = current_financial_year_label()
        fy = FinancialYear.objects.create(label=label)
        resp = self.client.get(reverse("council_detail", args=["test"]))
        year = next(y for y in resp.context["years"] if y.label == label)
        self.assertEqual(year.display, "Current Year to Date")
