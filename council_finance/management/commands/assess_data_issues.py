from django.core.management.base import BaseCommand

from council_finance.data_quality import assess_data_issues


class Command(BaseCommand):
    """Scan figures and rebuild DataIssue entries."""

    help = "Assess missing and suspicious data across all councils"

    def handle(self, *args, **options):
        count = assess_data_issues()
        self.stdout.write(self.style.SUCCESS(f"Identified {count} issues"))
