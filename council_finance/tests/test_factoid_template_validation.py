from django.test import TestCase
from council_finance.models import DataField, FactoidTemplate


class FactoidTemplateValidationTest(TestCase):
    def test_validate_template_with_financial_prefix(self):
        DataField.objects.create(name="Total Debt", slug="total-debt")
        template = FactoidTemplate.objects.create(
            name="Debt Template",
            template_text="Total debt is {financial.total_debt}"
        )

        self.assertTrue(template.validate_template())
        self.assertEqual(template.validation_errors, [])

