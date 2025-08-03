from typing import Iterable
import logging

from django.db import transaction
from django.db import models

logger = logging.getLogger(__name__)

from .models import (
    Council,
    FinancialYear,
    DataField,
    DataIssue,
    CouncilCharacteristic,
    FinancialFigure,
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
# those attributes without relying on a separate data entry.
COUNCIL_ATTRS = {
    "council_type": lambda c: c.council_type_id,
    "council_nation": lambda c: c.council_nation_id,
    "council_website": lambda c: c.website,
}


def cleanup_invalid_field_references() -> int:
    """Clean up references to non-existent or renamed fields."""
    removed_count = 0
    
    logger.info("Starting cleanup_invalid_field_references() routine ...")
    
    # Get all valid field IDs 
    valid_field_ids = set(DataField.objects.values_list("id", flat=True))
    logger.info(f"Found {len(valid_field_ids)} valid field IDs")
    
    # Remove DataIssues pointing to invalid fields
    invalid_issues = DataIssue.objects.exclude(field_id__in=valid_field_ids)
    if invalid_issues.exists():
        logger.info(f"Removing {invalid_issues.count()} invalid DataIssue records")
    removed_count += invalid_issues.count()
    invalid_issues.delete()
    logger.info("Removed invalid DataIssue records")
    logger.info("removed_count after DataIssue cleanup: %d", removed_count)
      # Remove invalid CouncilCharacteristic records pointing to invalid fields
    from .models import CouncilCharacteristic
    invalid_characteristics = CouncilCharacteristic.objects.exclude(field_id__in=valid_field_ids)
    if invalid_characteristics.exists():
        logger.info(f"Removing {invalid_characteristics.count()} invalid CouncilCharacteristic records")
    removed_count += invalid_characteristics.count()
    invalid_characteristics.delete()
    logger.info("Removed invalid CouncilCharacteristic records")
    logger.info("removed_count after CouncilCharacteristic cleanup: %d", removed_count)
    
    # Remove invalid FinancialFigure records pointing to invalid fields
    from .models import FinancialFigure
    invalid_figures = FinancialFigure.objects.exclude(field_id__in=valid_field_ids)
    if invalid_figures.exists():
        logger.info(f"Removing {invalid_figures.count()} invalid FinancialFigure records")
    removed_count += invalid_figures.count()
    invalid_figures.delete()
    logger.info("Removed invalid FinancialFigure records")
    logger.info("removed_count after FinancialFigure cleanup: %d", removed_count)

    # Remove Contributions pointing to invalid fields
    from .models import Contribution
    invalid_contributions = Contribution.objects.exclude(field_id__in=valid_field_ids)
    if invalid_contributions.exists():
        logger.info(f"Removing {invalid_contributions.count()} invalid Contribution records")
    removed_count += invalid_contributions.count() 
    invalid_contributions.delete()
    logger.info("Removed invalid Contribution records")
    logger.info("removed_count after Contribution cleanup: %d", removed_count)
    
    return removed_count


def validate_field_data_consistency() -> int:
    """Ensure data is consistent with current field definitions and clean up duplicates."""
    import logging
    import time
    fixed_count = 0
    # Start a timer to show how long this method ran for
    start_time = time.monotonic()

    logger = logging.getLogger(__name__)
    logger.info("Starting validate_field_data_consistency()...")
      # Check for DataIssues that should no longer exist because data has been provided
    from .models import Contribution
    
    # Get all missing DataIssues upfront
    missing_issues = list(DataIssue.objects.filter(issue_type="missing").select_related('council', 'field', 'year'))
    logger.info(f"Found {len(missing_issues)} missing data issues to validate")
    
    if not missing_issues:
        logger.info("No missing issues to validate")
        return 0
      # Build sets of existing data for efficient lookup
    logger.info("Building lookup sets for existing data and contributions...")
    
    # Get all existing data as a set of tuples (council_id, field_id, year_id)
    # For characteristics, year_id will be None
    existing_characteristics = set(
        (char.council_id, char.field_id, None) 
        for char in CouncilCharacteristic.objects.values('council_id', 'field_id')
    )
    existing_financial_figures = set(
        FinancialFigure.objects.values_list('council_id', 'field_id', 'year_id')
    )
    existing_submissions = existing_characteristics.union(existing_financial_figures)
    logger.info(f"Found {len(existing_submissions)} existing data points")
    
    # Get all pending contributions as a set of tuples
    pending_contributions = set(
        Contribution.objects.filter(status="pending").values_list('council_id', 'field_id', 'year_id')
    )
    logger.info(f"Found {len(pending_contributions)} pending contributions")
    
    # Check which issues can be resolved
    resolved_issues = []
    for issue in missing_issues:
        key = (issue.council_id, issue.field_id, issue.year_id)
        
        if key in existing_submissions or key in pending_contributions:
            resolved_issues.append(issue.id)
    
    logger.info(f"Found {len(resolved_issues)} issues that can be resolved")
    
    if resolved_issues:
        fixed_count = len(resolved_issues)
        # Delete in batches to avoid large transaction
        batch_size = 1000
        for i in range(0, len(resolved_issues), batch_size):
            batch = resolved_issues[i:i + batch_size]
            DataIssue.objects.filter(id__in=batch).delete()
            logger.info(f"Deleted batch of {len(batch)} resolved issues")
    
    # Log how long this method took to run
    elapsed_time = time.monotonic() - start_time
    logger.info("validate_field_data_consistency() completed in %.2f seconds, fixed %d issues", elapsed_time, fixed_count)
    return fixed_count


def assess_data_issues() -> int:
    """Rebuild the :class:`DataIssue` table by scanning current figures."""
    from django.db import connection
    from django.db.models import Q, Count, Prefetch
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Starting data issues assessment...")
    
    # First, clean up any invalid field references
    cleanup_count = cleanup_invalid_field_references()
    logger.info("cleanup_invalid_field_references() completed, cleaned up %d references", cleanup_count)
    consistency_count = validate_field_data_consistency()
    logger.info("validate_field_data_consistency() completed, fixed %d issues", consistency_count)
    
    # Clear all existing DataIssues - we'll rebuild from scratch
    # Delete in chunks to avoid long-running transactions
    old_count = DataIssue.objects.count()
    logger.info(f"Deleting {old_count} existing DataIssue records in chunks...")
    
    chunk_size = 10000
    deleted_total = 0
    
    while True:
        # Get a batch of IDs to delete
        ids_to_delete = list(DataIssue.objects.values_list('id', flat=True)[:chunk_size])
        
        if not ids_to_delete:
            break
            
        # Delete this batch
        with transaction.atomic():
            deleted_count = DataIssue.objects.filter(id__in=ids_to_delete).delete()[0]
            deleted_total += deleted_count
            logger.info(f"Deleted chunk of {deleted_count} records. Total deleted: {deleted_total}/{old_count}")
    
    logger.info(f"Cleared {deleted_total} existing DataIssue records")
    
    # Get all ACTIVE data with optimized queries upfront    logger.info("Loading active councils...")
    councils = list(Council.objects.select_related('council_type').filter(status='active'))
    council_count = len(councils)
    
    logger.info("Loading fields with council type relationships...")
    fields = list(DataField.objects.prefetch_related('council_types').exclude(slug="council_name"))
    field_count = len(fields)
    
    logger.info("Loading years...")
    years = list(FinancialYear.objects.all())
    year_count = len(years)
    
    logger.info(f"Will process {council_count} councils × {field_count} fields × {year_count} years = {council_count * field_count * year_count:,} combinations")
    
    # Build field-to-council-types mapping once
    field_council_types = {}
    for field in fields:
        field_council_types[field.id] = set(field.council_types.values_list('id', flat=True))
      # Build yearless field set from characteristics
    yearless_field_ids = set(
        CouncilCharacteristic.objects.values_list("field_id", flat=True)
    )
    yearless_field_ids.update(
        f.id for f in fields if f.slug in CHARACTERISTIC_SLUGS or f.category == "characteristic"
    )
    logger.info(f"Found {len(yearless_field_ids)} yearless fields")
    
    # Get ALL existing data from both model types in one query
    logger.info("Loading existing data...")
    existing_submissions = {}
    
    # Load characteristics (year_id will be None)
    for char in CouncilCharacteristic.objects.select_related('field').all():
        existing_submissions[(char.council_id, char.field_id, None)] = char
    
    # Load financial figures (year_id will be set)
    for fig in FinancialFigure.objects.select_related('field').all():
        existing_submissions[(fig.council_id, fig.field_id, fig.year_id)] = fig
    
    logger.info(f"Loaded {len(existing_submissions)} existing data points")
    
    # Get ALL contributed data in one query
    logger.info("Loading contributions...")
    from .models import Contribution
    contributed_keys = set(
        Contribution.objects.values_list('council_id', 'field_id', 'year_id')
    )
    logger.info(f"Loaded {len(contributed_keys)} contributions")
    
    # Process with progress tracking
    batch_size = 1000
    issues_to_create = []
    count = 0
    processed_councils = 0
    
    year_ids = [y.id for y in years]
    
    for council in councils:
        processed_councils += 1
        
        # Log progress every 10 councils
        if processed_councils % 10 == 0:
            logger.info(f"Processing council {processed_councils}/{council_count}: {council.name}")
            
        for field in fields:
            # Check if field applies to this council type using preloaded data
            field_types = field_council_types[field.id]
            if field_types and council.council_type_id not in field_types:
                continue
                
            # Determine which years to check for this field
            if field.id in yearless_field_ids:
                year_ids_to_check = [None]
            else:
                year_ids_to_check = year_ids
            
            for year_id in year_ids_to_check:
                key = (council.id, field.id, year_id)
                
                # Skip if already contributed
                if key in contributed_keys:
                    continue
                
                # Check council attributes first (for characteristic fields)
                attr_check = COUNCIL_ATTRS.get(field.slug)
                if attr_check and year_id is None:
                    try:
                        value = attr_check(council)
                        if value in (None, ""):
                            issues_to_create.append(DataIssue(
                                council=council,
                                field=field,
                                year_id=year_id,
                                issue_type="missing"
                            ))
                            count += 1
                    except Exception as e:
                        logger.warning(f"Error checking attribute {field.slug} for {council.name}: {e}")
                    continue
                
                # Check figure submissions
                fs = existing_submissions.get(key)
                if not fs or fs.needs_populating or fs.value in (None, ""):
                    # Missing data
                    issues_to_create.append(DataIssue(
                        council=council,
                        field=field,
                        year_id=year_id,
                        issue_type="missing"
                    ))
                    count += 1
                else:
                    # Check for suspicious values (zeros in monetary/integer fields)
                    if field.content_type in {"monetary", "integer"}:
                        val = str(fs.value).strip()
                        if val in {"0", "0.0"}:
                            issues_to_create.append(DataIssue(
                                council=council,
                                field=field,
                                year_id=year_id,
                                issue_type="suspicious",
                                value=val
                            ))
                            count += 1
                
                # Bulk create when we hit batch size
                if len(issues_to_create) >= batch_size:
                    with transaction.atomic():
                        DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
                    logger.info(f"Created batch of {len(issues_to_create)} issues. Total so far: {count}")
                    issues_to_create = []
    
    # Create any remaining issues
    if issues_to_create:
        with transaction.atomic():
            DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
        logger.info(f"Created final batch of {len(issues_to_create)} issues")
    
    logger.info(f"Data issues assessment complete. Created {count} new issues.")
    return count


def assess_data_issues_chunked() -> int:
    """
    Memory-efficient version that processes councils in chunks.
    Use this for very large datasets to avoid memory issues.
    """
    from django.core.paginator import Paginator
    from django.db.models import Prefetch
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Starting chunked data issues assessment...")
    
    # First, clean up any invalid field references
    cleanup_count = cleanup_invalid_field_references()
    consistency_count = validate_field_data_consistency()
    
    # Clear all existing DataIssues - we'll rebuild from scratch
    old_count = DataIssue.objects.count()
    DataIssue.objects.all().delete()
    logger.info(f"Cleared {old_count} existing DataIssue records")
    
    # Get basic counts first
    council_count = Council.objects.count()
    field_count = DataField.objects.exclude(slug="council_name").count()
    year_count = FinancialYear.objects.count()
    
    logger.info(f"Will process {council_count} councils × {field_count} fields × {year_count} years")
    
    # Load fields and years once (they're smaller datasets)
    logger.info("Loading fields and years...")
    fields = list(DataField.objects.prefetch_related('council_types').exclude(slug="council_name"))
    years = list(FinancialYear.objects.all())
    year_ids = [y.id for y in years]
      # Build field-to-council-types mapping once
    field_council_types = {}
    for field in fields:
        field_council_types[field.id] = set(field.council_types.values_list('id', flat=True))
    
    # Build yearless field set from characteristics  
    yearless_field_ids = set(
        CouncilCharacteristic.objects.values_list("field_id", flat=True)
    )
    yearless_field_ids.update(
        f.id for f in fields if f.slug in CHARACTERISTIC_SLUGS or f.category == "characteristic"
    )
      # Process councils in chunks
    chunk_size = 50  # Process 50 councils at a time
    councils_paginator = Paginator(Council.objects.select_related('council_type').all(), chunk_size)
    
    total_count = 0
    for page_num in councils_paginator.page_range:
        logger.info(f"Processing council chunk {page_num}/{councils_paginator.num_pages}")
        councils_page = councils_paginator.get_page(page_num)
        councils = list(councils_page)
        council_ids = [c.id for c in councils]
        
        # Load data for these councils only
        existing_submissions = {}
        
        # Load characteristics for these councils
        for char in CouncilCharacteristic.objects.filter(council_id__in=council_ids).select_related('field'):
            existing_submissions[(char.council_id, char.field_id, None)] = char
            
        # Load financial figures for these councils
        for fig in FinancialFigure.objects.filter(council_id__in=council_ids).select_related('field'):
            existing_submissions[(fig.council_id, fig.field_id, fig.year_id)] = fig
        
        # Load contributions for these councils only
        from .models import Contribution
        contributed_keys = set(
            Contribution.objects.filter(council_id__in=council_ids).values_list('council_id', 'field_id', 'year_id')
        )
        
        # Process this chunk
        issues_to_create = []
        batch_size = 1000
        
        for council in councils:
            for field in fields:
                # Check if field applies to this council type
                field_types = field_council_types[field.id]
                if field_types and council.council_type_id not in field_types:
                    continue
                    
                # Determine which years to check for this field
                if field.id in yearless_field_ids:
                    year_ids_to_check = [None]
                else:
                    year_ids_to_check = year_ids
                
                for year_id in year_ids_to_check:
                    key = (council.id, field.id, year_id)
                    
                    # Skip if already contributed
                    if key in contributed_keys:
                        continue
                    
                    # Check council attributes first (for characteristic fields)
                    attr_check = COUNCIL_ATTRS.get(field.slug)
                    if attr_check and year_id is None:
                        try:
                            value = attr_check(council)
                            if value in (None, ""):
                                issues_to_create.append(DataIssue(
                                    council=council,
                                    field=field,
                                    year_id=year_id,
                                    issue_type="missing"
                                ))
                        except Exception as e:
                            logger.warning(f"Error checking attribute {field.slug} for {council.name}: {e}")
                        continue
                    
                    # Check figure submissions
                    fs = existing_submissions.get(key)
                    if not fs or fs.needs_populating or fs.value in (None, ""):
                        # Missing data
                        issues_to_create.append(DataIssue(
                            council=council,
                            field=field,
                            year_id=year_id,
                            issue_type="missing"
                        ))
                    else:
                        # Check for suspicious values (zeros in monetary/integer fields)
                        if field.content_type in {"monetary", "integer"}:
                            val = str(fs.value).strip()
                            if val in {"0", "0.0"}:
                                issues_to_create.append(DataIssue(
                                    council=council,
                                    field=field,
                                    year_id=year_id,
                                    issue_type="suspicious",
                                    value=val
                                ))
                    
                    # Bulk create when we hit batch size
                    if len(issues_to_create) >= batch_size:
                        with transaction.atomic():
                            DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
                        total_count += len(issues_to_create)
                        logger.info(f"Created batch of {len(issues_to_create)} issues. Total so far: {total_count}")
                        issues_to_create = []
        
        # Create any remaining issues for this chunk
        if issues_to_create:
            with transaction.atomic():
                DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
            total_count += len(issues_to_create)
            logger.info(f"Created final batch for chunk: {len(issues_to_create)} issues. Total so far: {total_count}")
    
    logger.info(f"Chunked data issues assessment complete. Created {total_count} new issues.")
    return total_count


def quick_assess_data_issues() -> int:
    """
    Quick assessment that just counts potential issues without creating DataIssue records.
    Use this to get a fast estimate of the scope before running the full assessment.
    """
    import logging
    from .models import Contribution
    
    logger = logging.getLogger(__name__)
    logger.info("Starting quick data issues assessment (count only)...")
      # Get basic counts
    council_count = Council.objects.count()
    field_count = DataField.objects.exclude(slug="council_name").count()
    year_count = FinancialYear.objects.count()
    logger.info(f"Database contains: {council_count} councils, {field_count} fields, {year_count} years")
    
    # Get existing data counts from both model types
    characteristic_count = CouncilCharacteristic.objects.count()
    financial_figure_count = FinancialFigure.objects.count()
    submission_count = characteristic_count + financial_figure_count
    contribution_count = Contribution.objects.filter(status="pending").count()
    
    logger.info(f"Existing data: {submission_count} total data points ({characteristic_count} characteristics + {financial_figure_count} financial figures), {contribution_count} pending contributions")
    
    # Rough estimate: assume 70% of council/field/year combinations need data
    # This is just a ballpark figure - actual assessment will be more precise
    total_combinations = council_count * field_count * year_count
    estimated_missing = int(total_combinations * 0.7)
    
    logger.info(f"Estimated missing data issues: ~{estimated_missing:,}")
    logger.info("This is a rough estimate. Run the full assessment for precise counts.")
    
    return estimated_missing


def assess_data_issues_fast() -> int:
    """
    Fastest version that uses optimized SQL and avoids database locks.
    Only checks for truly missing council characteristics.
    """
    from django.db import connection
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Starting fast data issues assessment...")
    
    # Clear existing issues with a simple truncate-like operation
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM council_finance_dataissue")
        logger.info("Cleared all existing DataIssue records")
    
    # Use a much simpler approach - just find missing council characteristics
    # This avoids the complex cross joins that were causing locks
    with connection.cursor() as cursor:
        logger.info("Finding missing council characteristics...")
        
        # Insert missing council_type data - check if council_type_id is actually NULL
        cursor.execute("""
            INSERT INTO council_finance_dataissue (council_id, field_id, year_id, issue_type, value, created)
            SELECT DISTINCT 
                c.id,
                f.id,
                NULL,
                'missing',
                '',
                datetime('now')
            FROM council_finance_council c
            CROSS JOIN council_finance_datafield f
            WHERE f.slug = 'council_type'
            AND (c.council_type_id IS NULL OR c.council_type_id = '')
        """)
        council_type_count = cursor.rowcount
        logger.info(f"Found {council_type_count} councils missing council_type")
        
        # Insert missing council_website data
        cursor.execute("""
            INSERT INTO council_finance_dataissue (council_id, field_id, year_id, issue_type, value, created)
            SELECT DISTINCT 
                c.id,
                f.id,
                NULL,
                'missing',
                '',
                datetime('now')
            FROM council_finance_council c
            CROSS JOIN council_finance_datafield f
            WHERE f.slug = 'council_website'
            AND (c.website IS NULL OR c.website = '')
        """)
        website_count = cursor.rowcount
        logger.info(f"Found {website_count} councils missing website")
        
        # Insert missing council_nation data (if that field exists)
        cursor.execute("""
            INSERT INTO council_finance_dataissue (council_id, field_id, year_id, issue_type, value, created)
            SELECT DISTINCT 
                c.id,
                f.id,
                NULL,
                'missing',
                '',
                datetime('now')
            FROM council_finance_council c
            CROSS JOIN council_finance_datafield f
            WHERE f.slug = 'council_nation'
            AND (c.council_nation_id IS NULL OR c.council_nation_id = '')
        """)
        nation_count = cursor.rowcount
        logger.info(f"Found {nation_count} councils missing council_nation")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM council_finance_dataissue")
        total_count = cursor.fetchone()[0]
        
    logger.info(f"Fast assessment complete. Created {total_count} data issues.")
    return total_count


def assess_data_issues_simple() -> int:
    """
    Simple, fast assessment focused on characteristics and avoiding database locks.
    Only checks for truly missing characteristic data.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Starting simple data issues assessment...")
    
    # Clear existing issues in small batches to avoid locks
    old_count = DataIssue.objects.count()
    logger.info(f"Clearing {old_count} existing issues...")
    
    batch_size = 1000
    while DataIssue.objects.exists():
        ids = list(DataIssue.objects.values_list('id', flat=True)[:batch_size])
        if not ids:
            break
        DataIssue.objects.filter(id__in=ids).delete()
        logger.info(f"Cleared batch of {len(ids)} issues")
    
    # Get all ACTIVE councils and characteristic fields
    # Exclude merged, closed, or renamed councils from contribution queues
    councils = list(Council.objects.select_related('council_type', 'council_nation').filter(status='active'))
    char_fields = list(DataField.objects.filter(category='characteristic').exclude(slug='council_name'))
    
    logger.info(f"Checking {len(councils)} active councils for {len(char_fields)} characteristic fields")
    
    # Get existing contributions for characteristics
    from .models import Contribution
    contributed_keys = set(
        Contribution.objects.filter(
            field__category='characteristic'
        ).values_list('council_id', 'field_id')
    )
    
    issues_to_create = []
    count = 0
    
    for council in councils:
        for field in char_fields:            # Skip if already contributed
            if (council.id, field.id) in contributed_keys:
                continue
            
            # Check if council already has this attribute
            has_data = False
            
            if field.slug == 'council_type':
                has_data = council.council_type is not None
            elif field.slug == 'council_nation':
                has_data = council.council_nation is not None
            elif field.slug == 'council_website':
                has_data = bool(council.website and council.website.strip())
            else:
                # For other characteristics, check if a CouncilCharacteristic exists
                has_data = CouncilCharacteristic.objects.filter(
                    council=council,
                    field=field
                ).exclude(
                    value__in=['', None]
                ).exists()
            
            if not has_data:
                issues_to_create.append(DataIssue(
                    council=council,
                    field=field,
                    year=None,
                    issue_type="missing",
                    value=""
                ))
                count += 1
        
        # Create in batches to avoid large transactions
        if len(issues_to_create) >= 100:
            with transaction.atomic():
                DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
            logger.info(f"Created batch of {len(issues_to_create)} issues. Total: {count}")
            issues_to_create = []
    
    # Create any remaining issues
    if issues_to_create:
        with transaction.atomic():
            DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
        logger.info(f"Created final batch of {len(issues_to_create)} issues")
    
    logger.info(f"Simple assessment complete. Created {count} characteristic issues.")
    return count
