from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
import django
django.setup()

class SearchApiTests(TestCase):
    def setUp(self):
        call_command('runagent', 'ImporterAgent', '--source', 'councils-migration.json')

    def test_live_search_requires_two_chars(self):
        response = self.client.get(reverse('search_councils'), {'q': 'a'})
        self.assertEqual(response.json(), [])

    def test_live_search_returns_results(self):
        response = self.client.get(reverse('search_councils'), {'q': 'wort'})
        data = response.json()
        self.assertTrue(any('Worthing' in item['name'] for item in data))
