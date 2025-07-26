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


class DataFieldVariableNameTest(TestCase):
    def test_from_variable_name_success(self):
        """Test successful lookup of field by variable name."""
        DataField.objects.create(name="Total Debt", slug="total-debt")
        field = DataField.from_variable_name("total_debt")
        self.assertEqual(field.slug, "total-debt")

    def test_from_variable_name_with_prefix(self):
        """Test successful lookup with prefix (e.g., 'financial.total_debt')."""
        DataField.objects.create(name="Total Debt", slug="total-debt")
        field = DataField.from_variable_name("financial.total_debt")
        self.assertEqual(field.slug, "total-debt")

    def test_from_variable_name_not_found_descriptive_error(self):
        """Test that missing fields raise descriptive errors with variable name."""
        with self.assertRaises(DataField.DoesNotExist) as context:
            DataField.from_variable_name("nonexistent_field")
        
        error_message = str(context.exception)
        self.assertIn("nonexistent_field", error_message)
        self.assertIn("slug='nonexistent-field'", error_message)

    def test_from_variable_name_with_prefix_not_found_descriptive_error(self):
        """Test descriptive error message includes full variable name with prefix."""
        with self.assertRaises(DataField.DoesNotExist) as context:
            DataField.from_variable_name("financial.missing_field")
        
        error_message = str(context.exception)
        self.assertIn("financial.missing_field", error_message)
        self.assertIn("slug='missing-field'", error_message)

