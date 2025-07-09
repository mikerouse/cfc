from django.test import TestCase
from django.urls import reverse
import django
django.setup()

from council_finance.models import Council, FinancialYear, DataField, FigureSubmission


class HomeViewTest(TestCase):
    def setUp(self):
        field = DataField.objects.create(name="Total Debt", slug="total_debt")
        year = FinancialYear.objects.create(label="2024")
        self.council = Council.objects.create(name="Worthing Borough Council", slug="worthing")
        FigureSubmission.objects.create(council=self.council, year=year, field=field, value="1")

    def test_home_page_renders(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Ensure the template context includes the debt total
        self.assertIn('total_debt', response.context)

    def test_search_returns_results(self):
        response = self.client.get(reverse('home'), {'q': 'Worthing'})
        self.assertContains(response, 'Worthing Borough Council')
