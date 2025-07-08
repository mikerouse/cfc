from django.test import TestCase

from council_finance.factoids import get_factoids
from council_finance.models import Factoid, CounterDefinition


class FactoidPlaceholderTest(TestCase):
    """Ensure placeholders like {value} are substituted."""

    def test_value_placeholder_is_replaced(self):
        counter = CounterDefinition.objects.create(
            name="Debt", slug="debt", formula="1"
        )
        factoid = Factoid.objects.create(
            name="Change", slug="change", factoid_type="percent_change", text="{value} compared"
        )
        factoid.counters.add(counter)

        facts = get_factoids("debt", {"raw": 105, "previous_raw": 100})
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["text"], "5.0% compared")
