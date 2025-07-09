from django.core.management import call_command
from django.test import TestCase

from council_finance.models import Council, DataField, FinancialYear, FigureSubmission, DataIssue


class AssessDataIssuesTests(TestCase):
    def setUp(self):
        self.year = FinancialYear.objects.create(label="2024/25")
        self.field = DataField.objects.create(name="Employees", slug="employees", content_type="integer")
        self.council = Council.objects.create(name="GapTown", slug="gap-town")
        # Create a suspicious zero value
        FigureSubmission.objects.create(council=self.council, field=self.field, year=self.year, value="0")

    def test_command_creates_issue_entries(self):
        call_command("assess_data_issues")
        self.assertTrue(DataIssue.objects.filter(issue_type="suspicious").exists())
        issue = DataIssue.objects.filter(issue_type="suspicious").first()
        self.assertEqual(issue.value, "0")
