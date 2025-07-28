"""
Integration Tests for Data Context Consistency

Tests to ensure data context structures remain consistent across
the application and prevent issues like the characteristics key mismatch.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from council_finance.models import (
    Council, FinancialYear, DataField, CouncilCharacteristic, 
    FinancialFigure, CouncilType, CouncilNation
)
from council_finance.calculators import get_data_context_for_council
from council_finance.utils.data_context_validator import DataContextValidator
from council_finance.utils.field_naming import FieldNamingValidator, FormulaFieldExtractor


class DataContextConsistencyTest(TestCase):
    """Test data context consistency across different functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create basic objects
        self.council_type = CouncilType.objects.create(name="Test Council")
        self.council_nation = CouncilNation.objects.create(name="Test Nation")
        self.council = Council.objects.create(
            name="Test Council",
            slug="test-council",
            council_type=self.council_type,
            council_nation=self.council_nation
        )
        self.year = FinancialYear.objects.create(label="2024/25")
        
        # Create test fields
        self.char_field = DataField.objects.create(
            name="Population",
            slug="population",
            category="characteristic"
        )
        self.financial_field = DataField.objects.create(
            name="Total Debt",
            slug="total-debt",
            category="balance_sheet"
        )
        self.calculated_field = DataField.objects.create(
            name="Debt Per Capita",
            slug="debt-per-capita",
            category="calculated",
            formula="total_debt / population"
        )
        
        # Create test data
        CouncilCharacteristic.objects.create(
            council=self.council,
            field=self.char_field,
            value="100000"
        )
        FinancialFigure.objects.create(
            council=self.council,
            year=self.year,
            field=self.financial_field,
            value="50000000"
        )
    
    def test_data_context_schema_validation(self):
        """Test that data context follows expected schema."""
        context = get_data_context_for_council(self.council, year=self.year)
        
        # Validate schema
        errors = DataContextValidator.validate_data_context(context, "test")
        self.assertEqual(errors, [], f"Data context validation failed: {errors}")
        
        # Check required keys exist
        self.assertIn('characteristic', context, "Missing 'characteristic' key")
        self.assertIn('financial', context, "Missing 'financial' key")
        self.assertIn('calculated', context, "Missing 'calculated' key")
        
        # Ensure we don't have the wrong plural form
        self.assertNotIn('characteristics', context, "Found incorrect 'characteristics' (plural) key")
    
    def test_data_context_contains_test_data(self):
        """Test that created test data appears in context."""
        context = get_data_context_for_council(self.council, year=self.year)
        
        # Check characteristic data
        self.assertIn('population', context['characteristic'])
        self.assertEqual(context['characteristic']['population'], "100000")
        
        # Check financial data  
        self.assertIn('total_debt', context['financial'])
        self.assertEqual(float(context['financial']['total_debt']), 50000000.0)
        
        # Check calculated data (if dependency resolution works)
        if 'debt_per_capita' in context['calculated']:
            self.assertIsNotNone(context['calculated']['debt_per_capita'])
    
    def test_field_name_consistency(self):
        """Test field naming consistency between slugs and variable names."""
        test_cases = [
            ("total-debt", "total_debt"),
            ("non-ring-fenced-grants", "non_ring_fenced_grants"),
            ("council-tax-income", "council_tax_income"),
            ("debt-per-capita", "debt_per_capita"),
        ]
        
        for slug, expected_var_name in test_cases:
            var_name = FieldNamingValidator.slug_to_variable_name(slug)
            self.assertEqual(var_name, expected_var_name, 
                           f"Slug '{slug}' should convert to '{expected_var_name}', got '{var_name}'")
            
            # Test reverse conversion
            back_to_slug = FieldNamingValidator.variable_name_to_slug(var_name)
            self.assertEqual(back_to_slug, slug,
                           f"Variable name '{var_name}' should convert back to '{slug}', got '{back_to_slug}'")
    
    def test_formula_field_extraction(self):
        """Test extraction of field references from formulas."""
        test_formulas = [
            ("total_debt / population", {"total_debt", "population"}),
            ("total-debt / population", {"total-debt", "population"}),
            ("(income - expenditure) / population", {"income", "expenditure", "population"}),
            ("council_tax_income + business_rates", {"council_tax_income", "business_rates"}),
            ("1000 + 500", set()),  # No field references
        ]
        
        for formula, expected_refs in test_formulas:
            extracted_refs = FormulaFieldExtractor.extract_field_references(formula)
            self.assertEqual(extracted_refs, expected_refs,
                           f"Formula '{formula}' should extract {expected_refs}, got {extracted_refs}")
    
    def test_preview_counter_data_consistency(self):
        """Test that preview_counter_value gets consistent data."""
        from council_finance.views.admin import preview_counter_value
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # Create superuser for auth
        user = User.objects.create_superuser('test', 'test@test.com', 'testpass')
        
        # Test simple formula
        request = factory.get('/preview/', {
            'council': self.council.slug,
            'year': self.year.label,
            'formula': 'total_debt',
            'precision': '0',
            'show_currency': 'true',
            'friendly_format': 'false'
        })
        request.user = user
        
        response = preview_counter_value(request)
        self.assertEqual(response.status_code, 200, 
                        f"Preview should succeed, got {response.status_code}: {response.content}")
        
        # Test calculated field formula  
        request = factory.get('/preview/', {
            'council': self.council.slug,
            'year': self.year.label,
            'formula': 'total_debt / population',
            'precision': '2',
            'show_currency': 'false',
            'friendly_format': 'false'
        })
        request.user = user
        
        response = preview_counter_value(request)
        self.assertEqual(response.status_code, 200,
                        f"Calculated formula should succeed, got {response.status_code}: {response.content}")
    
    def test_hyphenated_field_handling(self):
        """Test that hyphenated field names work correctly."""
        # Create a field with hyphens
        hyphenated_field = DataField.objects.create(
            name="Non Ring Fenced Government Grants",
            slug="non-ring-fenced-government-grants",
            category="income"
        )
        
        FinancialFigure.objects.create(
            council=self.council,
            year=self.year,
            field=hyphenated_field,
            value="1000000"
        )
        
        context = get_data_context_for_council(self.council, year=self.year)
        
        # Check that hyphenated field appears in context with underscore variable name
        expected_var_name = "non_ring_fenced_government_grants"
        self.assertIn(expected_var_name, context['financial'],
                     f"Hyphenated field should appear as '{expected_var_name}' in financial context")
        
        # Test formula evaluation with hyphenated field
        from council_finance.views.admin import preview_counter_value
        from django.test import RequestFactory
        
        factory = RequestFactory()
        user = User.objects.create_superuser('test2', 'test2@test.com', 'testpass')
        
        request = factory.get('/preview/', {
            'council': self.council.slug,
            'year': self.year.label,
            'formula': 'non_ring_fenced_government_grants / population',
            'precision': '2',
            'show_currency': 'false',
            'friendly_format': 'false'
        })
        request.user = user
        
        response = preview_counter_value(request)
        self.assertEqual(response.status_code, 200,
                        f"Hyphenated field formula should work, got {response.status_code}: {response.content}")


class FieldValidationTest(TestCase):
    """Test field naming validation utilities."""
    
    def test_valid_field_slugs(self):
        """Test validation of valid field slugs."""
        valid_slugs = [
            "population",
            "total-debt", 
            "council-tax-income",
            "non-ring-fenced-grants",
            "debt-per-capita-2024",
        ]
        
        for slug in valid_slugs:
            errors = FieldNamingValidator.validate_field_slug(slug)
            self.assertEqual(errors, [], f"Valid slug '{slug}' should not have errors: {errors}")
    
    def test_invalid_field_slugs(self):
        """Test validation catches invalid field slugs."""
        invalid_slugs = [
            "",  # Empty
            "Total-Debt",  # Capital letters
            "-population",  # Starts with hyphen
            "debt-",  # Ends with hyphen
            "total--debt",  # Double hyphen
            "if",  # Reserved word
            "a",  # Too short
            "a" * 101,  # Too long
        ]
        
        for slug in invalid_slugs:
            errors = FieldNamingValidator.validate_field_slug(slug)
            self.assertGreater(len(errors), 0, f"Invalid slug '{slug}' should have validation errors")
    
    def test_field_matching(self):
        """Test field reference matching."""
        # Mock available fields
        available_fields = {
            'total-debt': type('Field', (), {'slug': 'total-debt', 'variable_name': 'total_debt'}),
            'population': type('Field', (), {'slug': 'population', 'variable_name': 'population'}),
        }
        
        # Test exact matches
        matches = FieldNamingValidator.find_field_matches('total-debt', available_fields)
        self.assertIn('total-debt', matches)
        
        # Test variable name matching
        matches = FieldNamingValidator.find_field_matches('total_debt', available_fields)
        self.assertGreater(len(matches), 0, "Should find matches for variable name format")
        
        # Test no matches
        matches = FieldNamingValidator.find_field_matches('nonexistent-field', available_fields)
        self.assertEqual(matches, [], "Should not find matches for nonexistent field")
