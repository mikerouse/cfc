"""
Simple test to verify the financial year dropdown fix
"""
from django.test import TestCase, Client
from django.urls import reverse
from council_finance.models import Council, FinancialYear
from council_finance.views.general import current_financial_year_label

class FinancialYearDisplayTest(TestCase):
    def test_council_detail_dropdown(self):
        """Test that financial years have proper display text in council detail dropdown"""
        # Create test data
        council = Council.objects.create(name="Test Council", slug="test-council")
        
        # Create some financial years
        current_year = current_financial_year_label()
        fy1 = FinancialYear.objects.create(label=current_year)
        fy2 = FinancialYear.objects.create(label="2023/24")
        
        # Test the council detail view
        client = Client()
        response = client.get(reverse('council_detail', args=[council.slug]))
        
        self.assertEqual(response.status_code, 200)
        
        # Check the context
        years = response.context.get('years', [])
        self.assertTrue(len(years) > 0)
        
        # Verify that years have display attribute
        for year in years:
            self.assertTrue(hasattr(year, 'display'))
            
            # Verify that current year shows "Current Year to Date"
            if year.label == current_year:
                self.assertEqual(year.display, "Current Year to Date")
            else:
                self.assertEqual(year.display, year.label)
                
        print("✓ Financial year dropdown display test passed!")
