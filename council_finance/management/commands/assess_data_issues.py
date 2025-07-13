from django.core.management.base import BaseCommand
from django.utils import timezone
from council_finance.data_quality import (
    assess_data_issues, 
    assess_data_issues_chunked, 
    assess_data_issues_fast,
    assess_data_issues_simple,
    quick_assess_data_issues
)
import logging


class Command(BaseCommand):
    """Scan figures and rebuild DataIssue entries."""

    help = "Assess missing and suspicious data across all councils"

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress detailed output",
        )
        parser.add_argument(
            "--log-level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Set logging level (default: INFO)",
        )
        parser.add_argument(
            "--method",
            default="simple",
            choices=["simple", "standard", "chunked", "fast", "quick"],
            help="Assessment method: simple (default, characteristics only), standard, chunked (memory efficient), fast (SQL-based), quick (estimate only)",
        )

    def handle(self, *args, **options):
        # Configure logging
        log_level = getattr(logging, options["log_level"])
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
        
        method = options["method"]
        
        if not options["quiet"]:
            self.stdout.write(f"Starting data issues assessment ({method} method)...")
            self.stdout.write(f"Log level: {options['log_level']}")
        
        start_time = timezone.now()
        
        try:
            if method == "simple":
                count = assess_data_issues_simple()
            elif method == "chunked":
                count = assess_data_issues_chunked()
            elif method == "fast":
                count = assess_data_issues_fast()
            elif method == "quick":
                count = quick_assess_data_issues()
            else:
                count = assess_data_issues()
                
            end_time = timezone.now()
            duration = end_time - start_time
            
            if not options["quiet"]:
                result_type = "estimated" if method == "quick" else "created"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Assessment complete! {result_type.title()} {count} data issues in {duration.total_seconds():.1f} seconds"
                    )
                )
            else:
                self.stdout.write(f"{count}")
                
        except Exception as e:
            end_time = timezone.now()
            duration = end_time - start_time
            
            self.stdout.write(
                self.style.ERROR(
                    f"Assessment failed after {duration.total_seconds():.1f} seconds: {str(e)}"
                )
            )
            raise
