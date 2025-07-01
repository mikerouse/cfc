from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
import django
django.setup()

from council_finance.models import Council


class HomeViewTest(TestCase):
    def setUp(self):
        # Load sample councils so the home view has data
        call_command('runagent', 'ImporterAgent', '--source', 'councils-migration.json')

    def test_home_page_renders(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Ensure the template context includes the debt total
        self.assertIn('total_debt', response.context)

    def test_search_returns_results(self):
        response = self.client.get(reverse('home'), {'q': 'Worthing'})
        self.assertContains(response, 'Worthing Borough Council')
