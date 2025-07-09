from django.core.management import call_command
from django.test import TestCase

from council_finance.models import Council, DataField, FinancialYear, FigureSubmission


class ReconcilePopulationCommandTest(TestCase):
    def setUp(self):
        self.field, _ = DataField.objects.get_or_create(
            slug="population",
            defaults={"name": "Population", "content_type": "integer"},
        )
        self.year1 = FinancialYear.objects.create(label="2023/24")
        self.year2 = FinancialYear.objects.create(label="2024/25")
        self.council = Council.objects.create(name="Sample", slug="sample")
        FigureSubmission.objects.create(council=self.council, year=self.year1, field=self.field, value="100")
        FigureSubmission.objects.create(council=self.council, year=self.year2, field=self.field, value="200")
        # Ensure cache starts empty
        self.council.latest_population = None
        self.council.save(update_fields=["latest_population"])

    def test_command_updates_cache(self):
        call_command("reconcile_population_cache")
        self.council.refresh_from_db()
        self.assertEqual(self.council.latest_population, 200)
