from django.test import TestCase
from council_finance.factoids import get_factoids
from council_finance.models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    CounterDefinition,
    Factoid,
)


class FactoidPercentChangeTest(TestCase):
    """Ensure percent_change factoids compute the correct value."""

    def setUp(self):
        self.council = Council.objects.create(name="A", slug="a")
        self.field = DataField.objects.create(name="Debt", slug="debt")
        self.year_prev = FinancialYear.objects.create(label="2024")
        self.year_curr = FinancialYear.objects.create(label="2025")
        FigureSubmission.objects.create(
            council=self.council, year=self.year_prev, field=self.field, value="100"
        )
        FigureSubmission.objects.create(
            council=self.council, year=self.year_curr, field=self.field, value="110"
        )
        self.counter = CounterDefinition.objects.create(
            name="Debt", slug="debt", formula="debt"
        )
        self.factoid = Factoid.objects.create(
            name="Change",
            slug="change",
            factoid_type="percent_change",
            text="{value} change",
        )
        self.factoid.counters.add(self.counter)

    def test_percent_change_substitution(self):
        facts = get_factoids(
            "debt",
            {"raw": 110, "previous_raw": 100},
        )
        self.assertEqual(facts[0]["text"], "10.0% change")
