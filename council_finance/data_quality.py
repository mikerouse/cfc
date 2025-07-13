from typing import Iterable

from django.db import transaction

from .models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    DataIssue,
)
# Import the list of protected slugs so we know which fields apply across
# all years. These fields are not repeated for each financial period and
# therefore should only generate a single DataIssue with ``year`` set to
# ``None`` if missing.
# ``CHARACTERISTIC_SLUGS`` represents council attributes that exist once per
# authority rather than repeating for every financial year.  We use this set to
# ensure missing data checks don't create duplicate issues for each year.
from .models.field import CHARACTERISTIC_SLUGS

# Map characteristic slugs that live directly on the ``Council`` model to a
# lambda returning their value. This allows the assessment routine to check
# those attributes without relying on a ``FigureSubmission`` entry.
COUNCIL_ATTRS = {
    "council_type": lambda c: c.council_type_id,
    "council_nation": lambda c: c.council_nation_id,
    "council_website": lambda c: c.website,
}


def cleanup_invalid_field_references() -> int:
    """Clean up references to non-existent or renamed fields."""
    removed_count = 0
    
    # Get all valid field IDs 
    valid_field_ids = set(DataField.objects.values_list("id", flat=True))
    
    # Remove DataIssues pointing to invalid fields
    invalid_issues = DataIssue.objects.exclude(field_id__in=valid_field_ids)
    removed_count += invalid_issues.count()
    invalid_issues.delete()
    
    # Remove FigureSubmissions pointing to invalid fields
    from .models import FigureSubmission
    invalid_submissions = FigureSubmission.objects.exclude(field_id__in=valid_field_ids)
    removed_count += invalid_submissions.count()
    invalid_submissions.delete()
    
    # Remove Contributions pointing to invalid fields
    from .models import Contribution
    invalid_contributions = Contribution.objects.exclude(field_id__in=valid_field_ids)
    removed_count += invalid_contributions.count() 
    invalid_contributions.delete()
    
    return removed_count


def validate_field_data_consistency() -> int:
    """Ensure data is consistent with current field definitions and clean up duplicates."""
    fixed_count = 0
    
    # Check for DataIssues that should no longer exist because data has been provided
    from .models import FigureSubmission, Contribution
    
    # Issues where data now exists
    resolved_issues = []
    for issue in DataIssue.objects.filter(issue_type="missing"):
        # Check if a FigureSubmission now exists
        submission_exists = FigureSubmission.objects.filter(
            council=issue.council,
            field=issue.field,
            year=issue.year
        ).exists()
        
        # Check if a pending contribution exists
        contribution_exists = Contribution.objects.filter(
            council=issue.council,
            field=issue.field,
            year=issue.year,
            status="pending"
        ).exists()
        
        if submission_exists or contribution_exists:
            resolved_issues.append(issue.id)
    
    if resolved_issues:
        fixed_count += len(resolved_issues)
        DataIssue.objects.filter(id__in=resolved_issues).delete()
    
    return fixed_count


def assess_data_issues() -> int:
    """Rebuild the :class:`DataIssue` table by scanning current figures."""
    # First, clean up any invalid field references
    cleanup_count = cleanup_invalid_field_references()
    consistency_count = validate_field_data_consistency()
    
    # Remove DataIssues for missing/obsolete fields (this is now redundant but kept for safety)
    valid_field_ids = set(DataField.objects.values_list("id", flat=True))
    DataIssue.objects.exclude(field_id__in=valid_field_ids).delete()
    DataIssue.objects.all().delete()
    years = list(FinancialYear.objects.all())
    fields = [f for f in DataField.objects.all() if f.slug != "council_name"]
    yearless_fields = set(
        FigureSubmission.objects.filter(year__isnull=True).values_list("field_id", flat=True)
    )
    yearless_fields.update(
        df.id for df in fields if df.slug in CHARACTERISTIC_SLUGS or df.category == "characteristic"
    )
    existing = {
        (fs.council_id, fs.field_id, fs.year_id): fs
        for fs in FigureSubmission.objects.all()
    }
    # Also exclude if a valid Contribution exists
    from .models import Contribution
    contributed = set(
        (c.council_id, c.field_id, c.year_id)
        for c in Contribution.objects.all()
    )
    count = 0
    with transaction.atomic():
        for council in Council.objects.all():
            for field in fields:
                allowed = list(field.council_types.all())
                if allowed and council.council_type not in allowed:
                    continue
                year_ids: Iterable[int | None]
                if field.id in yearless_fields:
                    year_ids = [None]
                else:
                    year_ids = [y.id for y in years]
                for year_id in year_ids:
                    attr_check = COUNCIL_ATTRS.get(field.slug)
                    if attr_check and year_id is None:
                        value = attr_check(council)
                        if value in (None, "") and (council.id, field.id, year_id) not in contributed:
                            DataIssue.objects.create(
                                council=council,
                                field=field,
                                issue_type="missing",
                            )
                            count += 1
                        continue

                    fs = existing.get((council.id, field.id, year_id))
                    if ((not fs or fs.needs_populating or fs.value in (None, "")) and
                        (council.id, field.id, year_id) not in contributed):
                        DataIssue.objects.create(
                            council=council,
                            field=field,
                            year_id=year_id,
                            issue_type="missing",
                        )
                        count += 1
                    else:
                        val = str(fs.value).strip() if fs else ""
                        if field.content_type in {"monetary", "integer"} and val in {"0", "0.0"}:
                            DataIssue.objects.create(
                                council=council,
                                field=field,
                                year_id=year_id,
                                issue_type="suspicious",
                                value=val,
                            )
                            count += 1
    return count
