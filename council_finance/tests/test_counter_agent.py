from django.test import TestCase
from council_finance.models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    CounterDefinition,
)

from council_finance.agents.counter_agent import CounterAgent


class CounterAgentRunTest(TestCase):
    """Ensure CounterAgent correctly handles valid and missing figures."""

    def setUp(self):
        # Basic objects shared across tests
        self.council = Council.objects.create(name="Demo", slug="demo")
        self.year = FinancialYear.objects.create(label="2025")
        self.field = DataField.objects.create(name="Total Debt", slug="total_debt")
        self.counter = CounterDefinition.objects.create(
            name="Debt", slug="debt", formula="total_debt", precision=0
        )
        self.agent = CounterAgent()

    def test_valid_figure_returns_value(self):
        """A numeric figure should be returned with a formatted value."""
        FigureSubmission.objects.create(
            council=self.council,
            year=self.year,
            field=self.field,
            value="123",
        )
        result = self.agent.run(council_slug="demo", year_label="2025")
        self.assertEqual(result["debt"]["value"], 123.0)
        self.assertEqual(result["debt"]["formatted"], "£123")

    def test_invalid_figure_returns_no_data(self):
        """Non-numeric figures are treated as missing."""
        FigureSubmission.objects.create(
            council=self.council,
            year=self.year,
            field=self.field,
            value="abc",
        )
        result = self.agent.run(council_slug="demo", year_label="2025")
        self.assertIsNone(result["debt"]["value"])
        self.assertEqual(result["debt"]["formatted"], "No data")

    def test_missing_figure_returns_no_data(self):
        """When no figure exists the counter reports missing data."""
        result = self.agent.run(council_slug="demo", year_label="2025")
        self.assertIsNone(result["debt"]["value"])
        self.assertEqual(result["debt"]["formatted"], "No data")
