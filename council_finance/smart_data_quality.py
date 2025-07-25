"""
Smart Data Quality Assessment System

This module provides an enhanced data quality assessment that:
1. Only flags missing data for financial years that should contain data
2. Respects financial year priorities and relevance
3. Avoids creating excessive false positive issues
4. Coordinates with the financial year management system
"""

from typing import Set, Dict, Optional
from django.db import transaction
from django.utils import timezone
import logging

from .models import (
    Council,
    FinancialYear,
    DataField,
    CouncilCharacteristic,
    FinancialFigure,
    DataIssue,
)
from .models.field import CHARACTERISTIC_SLUGS

logger = logging.getLogger(__name__)


def get_relevant_financial_years() -> Set[int]:
    """
    Determine which financial years should actually contain data.
    
    Returns a set of financial year IDs that are considered active/relevant
    for data collection and quality assessment.
    """
    relevant_years = set()
    
    # Get the current financial year if marked
    current_years = FinancialYear.objects.filter(is_current=True)
    relevant_years.update(current_years.values_list('id', flat=True))
    
    # If no current year is marked, use the most recent 2 years
    if not relevant_years:
        recent_years = FinancialYear.objects.order_by('-label')[:2]
        relevant_years.update(recent_years.values_list('id', flat=True))
        logger.info(f"No current year marked, using {len(recent_years)} most recent years")
    
    # Add any years that already have substantial data (>10% populated)
    for year in FinancialYear.objects.all():
        submission_count = FinancialFigure.objects.filter(year=year).count()
        if submission_count > 100:  # Arbitrary threshold for "substantial data"
            relevant_years.add(year.id)
            logger.info(f"Year {year.label} has {submission_count} financial figures, marking as relevant")
    
    logger.info(f"Identified {len(relevant_years)} relevant financial years")
    return relevant_years


def smart_assess_data_issues() -> int:
    """
    Comprehensive data quality assessment that shows all missing data organized by priority.
    
    This version:
    - Creates issues for ALL missing data (characteristics + all financial years)
    - Organizes by priority using current year flags and data presence
    - Provides complete contribution queues as expected
    - Maintains smart prioritization without hiding legitimate missing data
    """
    logger.info("Starting comprehensive data quality assessment...")
    
    # Clear existing issues (same as before)
    old_count = DataIssue.objects.count()
    logger.info(f"Clearing {old_count} existing issues...")
    
    # Delete in manageable chunks
    batch_size = 1000
    while DataIssue.objects.exists():
        ids = list(DataIssue.objects.values_list('id', flat=True)[:batch_size])
        if not ids:
            break
        DataIssue.objects.filter(id__in=ids).delete()
    
    logger.info("Cleared all existing DataIssue records")
    
    # Get ALL years for comprehensive assessment
    all_years = list(FinancialYear.objects.all())
    relevant_year_ids = get_relevant_financial_years()
    
    # Get all active councils and fields
    councils = list(Council.objects.select_related('council_type', 'council_nation').filter(status='active'))
    char_fields = list(DataField.objects.filter(category='characteristic').exclude(slug='council_name'))
    financial_fields = list(DataField.objects.exclude(category='characteristic'))
    
    logger.info(f"Processing {len(councils)} councils")
    logger.info(f"Checking {len(char_fields)} characteristic fields")
    logger.info(f"Checking {len(financial_fields)} financial fields for ALL {len(all_years)} years")
    
    # Get existing contributions to avoid double-flagging
    from .models import Contribution
    contributed_keys = set(
        Contribution.objects.values_list('council_id', 'field_id', 'year_id')
    )
    
    issues_to_create = []
    count = 0
    
    # === ASSESS CHARACTERISTIC DATA (yearless) ===
    logger.info("Assessing characteristic data...")
    
    # Map characteristic slugs to council attribute checks
    COUNCIL_ATTRS = {
        "council_type": lambda c: c.council_type is not None,
        "council_nation": lambda c: c.council_nation is not None,
        "council_website": lambda c: bool(c.website and c.website.strip()),
    }
    
    for council in councils:
        for field in char_fields:
            # Skip if already contributed
            if (council.id, field.id, None) in contributed_keys:
                continue
            
            # Check if council already has this attribute
            has_data = False
            if field.slug in COUNCIL_ATTRS:
                has_data = COUNCIL_ATTRS[field.slug](council)
            else:
                # For other characteristics, check if a CouncilCharacteristic exists
                has_data = CouncilCharacteristic.objects.filter(
                    council=council,
                    field=field
                ).exclude(
                    value__in=['', None]
                ).exists()
            
            if not has_data:
                # Add priority flag to the issue for smart sorting later
                issue = DataIssue(
                    council=council,
                    field=field,
                    year=None,
                    issue_type="missing",
                    value="",
                )
                # Mark characteristics as high priority since they apply to all councils
                if hasattr(issue, 'priority'):
                    issue.priority = "high"
                issues_to_create.append(issue)
                count += 1
    
    logger.info(f"Found {count} missing characteristic issues")
    
    # === ASSESS FINANCIAL DATA (ALL YEARS) ===
    logger.info("Assessing financial data for ALL years...")
    
    # Build field-to-council-types mapping for efficiency
    field_council_types = {}
    for field in financial_fields:
        field_council_types[field.id] = set(field.council_types.values_list('id', flat=True))
      # Get existing financial figures for ALL years
    existing_submissions = {}
    submission_queryset = FinancialFigure.objects.select_related('field')
    for fs in submission_queryset:
        existing_submissions[(fs.council_id, fs.field_id, fs.year_id)] = fs
    
    financial_count_start = count
    
    for council in councils:
        for field in financial_fields:
            # Check if field applies to this council type
            field_types = field_council_types[field.id]
            if field_types and council.council_type_id not in field_types:
                continue
            
            # Check ALL financial years (not just relevant ones)
            for year in all_years:
                key = (council.id, field.id, year.id)
                
                # Skip if already contributed
                if key in contributed_keys:
                    continue
                  # Check if we have existing data
                fs = existing_submissions.get(key)
                if not fs or fs.value in (None, ""):
                    # Missing financial data
                    issue = DataIssue(
                        council=council,
                        field=field,
                        year=year,
                        issue_type="missing",
                        value=""
                    )
                    # Mark priority based on whether this is a relevant/current year
                    if hasattr(issue, 'priority'):
                        if year.id in relevant_year_ids:
                            issue.priority = "high"
                        else:
                            issue.priority = "normal"
                    issues_to_create.append(issue)
                    count += 1
                else:
                    # Check for suspicious values (zeros in monetary/integer fields)
                    if field.content_type in {"monetary", "integer"}:
                        val = str(fs.value).strip()
                        if val in {"0", "0.0"}:
                            issue = DataIssue(
                                council=council,
                                field=field,
                                year=year,
                                issue_type="suspicious",
                                value=val
                            )
                            if hasattr(issue, 'priority'):
                                issue.priority = "high" if year.id in relevant_year_ids else "normal"
                            issues_to_create.append(issue)
                            count += 1
        
        # Create in batches to avoid large transactions
        if len(issues_to_create) >= batch_size:
            with transaction.atomic():
                DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
            logger.info(f"Created batch of {len(issues_to_create)} issues. Total: {count}")
            issues_to_create = []
    
    # Create any remaining issues
    if issues_to_create:
        with transaction.atomic():
            DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
        logger.info(f"Created final batch of {len(issues_to_create)} issues")
    
    financial_issues = count - financial_count_start
    logger.info(f"Found {financial_issues} missing financial data issues for ALL years")
    
    logger.info(f"Comprehensive assessment complete. Created {count} total issues:")
    logger.info(f"  - {financial_count_start} characteristic issues")
    logger.info(f"  - {financial_issues} financial data issues")
    
    return count


def mark_financial_year_as_current(year_label: str) -> bool:
    """
    Mark a specific financial year as the current/active year for data collection.
    
    This helps the smart assessment system understand which years should be prioritized.
    """
    try:
        # Clear any existing current year flags
        FinancialYear.objects.filter(is_current=True).update(is_current=False)
        
        # Mark the specified year as current
        year = FinancialYear.objects.get(label=year_label)
        year.is_current = True
        year.save()
        
        logger.info(f"Marked {year_label} as current financial year")
        return True
        
    except FinancialYear.DoesNotExist:
        logger.error(f"Financial year {year_label} not found")
        return False
    except Exception as e:
        logger.error(f"Error marking year as current: {e}")
        return False


def generate_missing_data_issues_for_council(council) -> int:
    """
    Generate missing data issues for a specific council.
    
    This is used when a new council is created to automatically populate
    the contribution queues with missing data fields.
    
    Returns the number of issues created.
    """
    logger.info(f"Generating missing data issues for council: {council.name}")
    
    # Get existing contributions to avoid double-flagging
    from .models import Contribution
    contributed_keys = set(
        Contribution.objects.filter(council=council).values_list('council_id', 'field_id', 'year_id')
    )
    
    issues_to_create = []
    count = 0
    
    # Get all financial years and relevant years
    all_years = list(FinancialYear.objects.all())
    relevant_year_ids = get_relevant_financial_years()
    
    # === ASSESS CHARACTERISTIC DATA (yearless) ===
    char_fields = list(DataField.objects.filter(category='characteristic').exclude(slug='council_name'))
    
    # Map characteristic slugs to council attribute checks
    COUNCIL_ATTRS = {
        "council_type": lambda c: c.council_type is not None,
        "council_nation": lambda c: c.council_nation is not None,
        "council_website": lambda c: bool(c.website and c.website.strip()),
    }
    
    for field in char_fields:
        # Skip if already contributed
        if (council.id, field.id, None) in contributed_keys:
            continue
        
        # Check if council already has this attribute
        has_data = False
        if field.slug in COUNCIL_ATTRS:
            has_data = COUNCIL_ATTRS[field.slug](council)
        else:
            # For other characteristics, check if a CouncilCharacteristic exists
            has_data = CouncilCharacteristic.objects.filter(
                council=council,
                field=field
            ).exclude(
                value__in=['', None]
            ).exists()
        
        if not has_data:
            # Create missing data issue for characteristic
            issue = DataIssue(
                council=council,
                field=field,
                year=None,
                issue_type="missing",
                value="",
            )
            # Mark characteristics as high priority
            if hasattr(issue, 'priority'):
                issue.priority = "high"
            issues_to_create.append(issue)
            count += 1
    
    # === ASSESS FINANCIAL DATA (ALL YEARS) ===
    financial_fields = list(DataField.objects.exclude(category='characteristic'))
    
    # Build field-to-council-types mapping for efficiency
    field_council_types = {}
    for field in financial_fields:
        field_council_types[field.id] = set(field.council_types.values_list('id', flat=True))
    
    # Get existing financial figures for this council
    existing_submissions = {}
    submission_queryset = FinancialFigure.objects.filter(council=council).select_related('field')
    for fs in submission_queryset:
        existing_submissions[(fs.council_id, fs.field_id, fs.year_id)] = fs
    
    for field in financial_fields:
        # Check if field applies to this council type
        field_types = field_council_types[field.id]
        if field_types and council.council_type_id not in field_types:
            continue
        
        # Check ALL financial years
        for year in all_years:
            key = (council.id, field.id, year.id)
            
            # Skip if already contributed
            if key in contributed_keys:
                continue
            
            # Check if we have existing data
            fs = existing_submissions.get(key)
            if not fs or fs.value in (None, ""):
                # Missing financial data
                issue = DataIssue(
                    council=council,
                    field=field,
                    year=year,
                    issue_type="missing",
                    value=""
                )
                # Mark priority based on whether this is a relevant/current year
                if hasattr(issue, 'priority'):
                    if year.id in relevant_year_ids:
                        issue.priority = "high"
                    else:
                        issue.priority = "normal"
                issues_to_create.append(issue)
                count += 1
    
    # Create all issues in a single batch
    if issues_to_create:
        with transaction.atomic():
            DataIssue.objects.bulk_create(issues_to_create, ignore_conflicts=True)
        logger.info(f"Created {count} missing data issues for council: {council.name}")
    else:
        logger.info(f"No missing data issues found for council: {council.name}")
    
    return count


def get_data_collection_priorities() -> Dict[str, any]:
    """
    Get information about data collection priorities and relevant years.
    
    This helps users understand which years and fields should be focused on.
    """
    relevant_year_ids = get_relevant_financial_years()
    relevant_years = FinancialYear.objects.filter(id__in=relevant_year_ids).order_by('-label')
    
    # Get current year if marked
    current_year = FinancialYear.objects.filter(is_current=True).first()
    
    # Calculate data completeness for relevant years
    year_stats = []
    for year in relevant_years:
        total_possible = Council.objects.filter(status='active').count() * \
                        DataField.objects.exclude(category='characteristic').count()
        actual_submissions = FinancialFigure.objects.filter(year=year).exclude(
            value__in=[None]
        ).count()
        
        completeness = (actual_submissions / max(total_possible, 1)) * 100
        
        year_stats.append({
            'year': year,
            'completeness': completeness,
            'submissions': actual_submissions,
            'potential': total_possible,
            'is_current': year.is_current if hasattr(year, 'is_current') else False
        })
    
    return {
        'relevant_years': list(relevant_years),
        'current_year': current_year,
        'year_stats': year_stats,
        'total_characteristics_missing': DataIssue.objects.filter(
            issue_type='missing',
            field__category='characteristic'
        ).count(),
        'total_financial_missing': DataIssue.objects.filter(
            issue_type='missing'
        ).exclude(field__category='characteristic').count(),
    }
