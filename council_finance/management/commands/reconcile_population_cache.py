from django.core.management.base import BaseCommand

from council_finance.population import reconcile_populations


class Command(BaseCommand):
    """Reconcile cached population figures for all councils."""

    help = "Update latest_population using the newest figure submissions"

    def handle(self, *args, **options):
        updated = reconcile_populations()
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} councils"))
