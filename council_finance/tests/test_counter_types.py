from django.test import TestCase
from django.urls import reverse
from council_finance.models import Council, CouncilType, DataField, FinancialYear, FigureSubmission, CounterDefinition

class CounterCouncilTypeTest(TestCase):
    def setUp(self):
        self.ct_district = CouncilType.objects.create(name="District")
        self.ct_county = CouncilType.objects.create(name="County")
        self.council = Council.objects.create(name="D", slug="d", council_type=self.ct_district)
        self.year = FinancialYear.objects.create(label="2024")
        self.field = DataField.objects.create(name="Total", slug="total")
        FigureSubmission.objects.create(council=self.council, year=self.year, field=self.field, value="1")
        self.counter = CounterDefinition.objects.create(name="Total", slug="totalc", formula="total")
        self.counter.council_types.add(self.ct_district)

    def test_counter_hidden_for_other_type(self):
        other = Council.objects.create(name="C", slug="c", council_type=self.ct_county)
        FigureSubmission.objects.create(council=other, year=self.year, field=self.field, value="1")
        url = reverse("council_detail", args=["c"])
        resp = self.client.get(url)
        slugs = [item["counter"].slug for item in resp.context["counters"]]
        self.assertNotIn("totalc", slugs)

    def test_counter_present_for_correct_type(self):
        url = reverse("council_counters", args=["d"])
        resp = self.client.get(url, {"year": "2024"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("totalc", resp.json()["counters"])
