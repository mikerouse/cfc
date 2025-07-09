from django.test import TestCase
from django.urls import reverse
import django
django.setup()

class SearchApiTests(TestCase):
    def setUp(self):
        from council_finance.models import Council
        Council.objects.create(name='Worthing Borough Council', slug='worthing')

    def test_live_search_requires_two_chars(self):
        response = self.client.get(reverse('search_councils'), {'q': 'a'})
        self.assertEqual(response.json(), [])

    def test_live_search_returns_results(self):
        response = self.client.get(reverse('search_councils'), {'q': 'wort'})
        data = response.json()
        self.assertTrue(any('Worthing' in item['name'] for item in data))
