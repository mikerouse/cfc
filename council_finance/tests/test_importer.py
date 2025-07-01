from django.test import TestCase
from django.core.management import call_command
import django
django.setup()

from council_finance.models import Council, FinancialYear, FigureSubmission

class ImporterAgentTest(TestCase):
    def test_importer_creates_objects(self):
        call_command('runagent', 'ImporterAgent', '--source', 'councils-migration.json')
        self.assertTrue(Council.objects.exists())
        self.assertTrue(FinancialYear.objects.exists())
        self.assertTrue(FigureSubmission.objects.exists())
