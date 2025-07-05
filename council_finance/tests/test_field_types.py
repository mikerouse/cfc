from django.test import TestCase
from django.urls import reverse
from council_finance.models import Council, CouncilType, DataField, FinancialYear, FigureSubmission

class FieldCouncilTypeTest(TestCase):
    def setUp(self):
        self.ct_county, _ = CouncilType.objects.get_or_create(name="County")
        self.ct_unitary, _ = CouncilType.objects.get_or_create(name="Unitary")
        self.field = DataField.objects.create(name="Uncollected", slug="uncollected_tax")
        self.field.council_types.add(self.ct_unitary)
        self.council = Council.objects.create(name="A", slug="a", council_type=self.ct_county)
        self.year = FinancialYear.objects.create(label="2024")
        FigureSubmission.objects.create(council=self.council, year=self.year, field=self.field, value="1")

    def test_figure_excluded_for_wrong_type(self):
        url = reverse("council_detail", args=["a"])
        resp = self.client.get(url)
        # field should not appear in figures queryset
        figures = resp.context["figures"]
        slugs = {f.field.slug for f in figures}
        self.assertNotIn("uncollected_tax", slugs)

