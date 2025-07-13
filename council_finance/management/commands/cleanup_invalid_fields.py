from django.core.management.base import BaseCommand

from council_finance.data_quality import cleanup_invalid_field_references, validate_field_data_consistency


class Command(BaseCommand):
    """Clean up invalid field references and inconsistent data."""

    help = "Remove references to invalid/renamed fields and fix data inconsistencies"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            
            # Count what would be removed
            from council_finance.models import DataIssue, FigureSubmission, Contribution, DataField
            
            valid_field_ids = set(DataField.objects.values_list("id", flat=True))
            
            invalid_issues = DataIssue.objects.exclude(field_id__in=valid_field_ids).count()
            invalid_submissions = FigureSubmission.objects.exclude(field_id__in=valid_field_ids).count()
            invalid_contributions = Contribution.objects.exclude(field_id__in=valid_field_ids).count()
            
            self.stdout.write(f"Would remove {invalid_issues} invalid DataIssue records")
            self.stdout.write(f"Would remove {invalid_submissions} invalid FigureSubmission records")
            self.stdout.write(f"Would remove {invalid_contributions} invalid Contribution records")
            
            return
        
        # Actually perform the cleanup
        cleanup_count = cleanup_invalid_field_references()
        consistency_count = validate_field_data_consistency()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleaned up {cleanup_count} invalid field references and "
                f"fixed {consistency_count} data consistency issues"
            )
        )
