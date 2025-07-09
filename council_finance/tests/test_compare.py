from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import Council, CouncilList, DataField, FinancialYear, FigureSubmission

class CompareTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Town", slug="town")
        self.other = Council.objects.create(name="City", slug="city")
        self.user = get_user_model().objects.create_user(
            username="bob", email="bob@example.com", password="secret"
        )
        # Ensure the population field and a sample year exist
        self.pop_field, _ = DataField.objects.get_or_create(
            slug="population", defaults={"name": "Population", "content_type": "integer"}
        )
        self.pop_field.content_type = "integer"
        self.pop_field.save()
        self.year, _ = FinancialYear.objects.get_or_create(label="2024/25")
        FigureSubmission.objects.create(council=self.council, year=self.year, field=self.pop_field, value="1000")
        FigureSubmission.objects.create(council=self.other, year=self.year, field=self.pop_field, value="2000")

    def test_add_to_compare_session(self):
        self.client.post(reverse("add_to_compare", args=["town"]))
        session = self.client.session
        self.assertIn("town", session.get("compare_basket", []))

    def test_save_basket_as_list(self):
        self.client.post(reverse("add_to_compare", args=["town"]))
        self.client.login(username="bob", password="secret")
        self.client.post(reverse("compare_basket"), {"save_list": "1", "name": "Mine"})
        self.assertTrue(CouncilList.objects.filter(name="Mine", user=self.user).exists())

    def test_population_summary_calculated(self):
        self.client.post(reverse("add_to_compare", args=["town"]))
        self.client.post(reverse("add_to_compare", args=["city"]))
        response = self.client.get(reverse("compare_basket"))
        rows = response.context["rows"]
        pop = next(r for r in rows if r["field"].slug == "population")
        self.assertEqual(pop["summary"]["total"], "3,000")
        self.assertEqual(pop["summary"]["highest"], "City")

