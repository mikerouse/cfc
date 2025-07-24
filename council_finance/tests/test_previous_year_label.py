from django.test import SimpleTestCase
from council_finance.year_utils import previous_year_label

class PreviousYearLabelTests(SimpleTestCase):
    def test_slash_format(self):
        self.assertEqual(previous_year_label('23/24'), '22/23')
        self.assertEqual(previous_year_label('2023/24'), '2022/23')

    def test_dash_format(self):
        # Mixed separators like ``2023-24`` should be interpreted the same
        # as slash separated years.
        self.assertEqual(previous_year_label('2023-24'), '2022/23')

    def test_simple_year(self):
        self.assertEqual(previous_year_label('2024'), '2023')
