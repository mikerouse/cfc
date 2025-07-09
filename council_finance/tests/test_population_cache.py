from django.test import TestCase
from council_finance.models import Council, FinancialYear, DataField, FigureSubmission


class PopulationCacheTest(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="City", slug="city")
        self.year1 = FinancialYear.objects.create(label="2023")
        self.year2 = FinancialYear.objects.create(label="2024")
        try:
            self.field = DataField.objects.get(slug="population")
        except DataField.DoesNotExist:
            self.field = DataField.objects.create(
                name="Population", slug="population", content_type="integer"
            )

    def test_cache_updates_with_new_figures(self):
        FigureSubmission.objects.create(council=self.council, year=self.year1, field=self.field, value="100")
        self.council.refresh_from_db()
        self.assertEqual(self.council.latest_population, 100)

        fs = FigureSubmission.objects.create(council=self.council, year=self.year2, field=self.field, value="200")
        self.council.refresh_from_db()
        self.assertEqual(self.council.latest_population, 200)

        fs.value = "300"
        fs.save()
        self.council.refresh_from_db()
        self.assertEqual(self.council.latest_population, 300)

        fs.delete()
        self.council.refresh_from_db()
        self.assertEqual(self.council.latest_population, 100)
