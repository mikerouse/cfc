"""
Utilities for working with financial years and data reliability.
"""

from typing import Optional
from django.core.cache import cache
from .models import FinancialYear


def previous_year_label(label: str) -> Optional[str]:
    """
    Return the previous financial year label if parsable.
    
    Args:
        label: Financial year label like "2024/25" or "2024-25"
        
    Returns:
        Previous year label like "2023/24" or None if not parsable
        
    Examples:
        >>> previous_year_label("2024/25")
        "2023/24"
        >>> previous_year_label("2024-25") 
        "2023/24"
        >>> previous_year_label("invalid")
        None
    """
    try:
        # Accept formats like "2023/24" or "2023-24" by normalising the
        # separator. Using "replace" allows us to handle mixed inputs without
        # multiple branches.
        clean = str(label).replace("-", "/")
        parts = clean.split("/")
        if len(parts) == 2:
            # Keep the same width for the trailing year so "23/24" becomes
            # "22/23" rather than "22/3". This mirrors the original
            # formatting supplied by admins.
            first = int(parts[0])
            second_str = parts[1]
            second = int(second_str)
            prev_first = first - 1
            prev_second = second - 1
            second_fmt = f"{prev_second:0{len(second_str)}d}"
            return f"{prev_first}/{second_fmt}"
    except (ValueError, IndexError):
        pass
    return None


def get_year_status_context():
    """
    Get cached context about financial year statuses.
    Returns a dict with current, past, and future year IDs for quick lookups.
    """
    cache_key = "financial_year_status_context"
    context = cache.get(cache_key)
    
    if context is None:
        current_year = FinancialYear.get_current()
        all_years = FinancialYear.objects.all()
        
        context = {
            'current_year_id': current_year.id if current_year else None,
            'past_year_ids': [],
            'future_year_ids': [],
            'current_year_label': current_year.label if current_year else None,
        }
        
        for year in all_years:
            if year.is_past:
                context['past_year_ids'].append(year.id)
            elif year.is_future:
                context['future_year_ids'].append(year.id)
        
        # Cache for 1 hour
        cache.set(cache_key, context, 3600)
    
    return context


def invalidate_year_status_cache():
    """Invalidate the financial year status cache when years are modified."""
    cache.delete("financial_year_status_context")


def get_figure_reliability_warning(year):
    """
    Get a user-friendly warning about figure reliability for a given year.
    
    Args:
        year: FinancialYear instance
        
    Returns:
        dict with 'level' (info/warning/error) and 'message'
    """
    if not year:
        return {'level': 'error', 'message': 'No financial year specified'}
    
    reliability_level = year.data_reliability_level
    
    if reliability_level == 'low':
        return {
            'level': 'warning',
            'message': year.reliability_note
        }
    elif reliability_level == 'medium':
        return {
            'level': 'info',
            'message': year.reliability_note
        }
    else:  # high reliability
        return {
            'level': 'info',
            'message': year.reliability_note
        }


def validate_year_label_format(label):
    """
    Validate that a financial year label follows expected format.
    
    Args:
        label: String like "2023/24"
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not label:
        return False, "Year label cannot be empty"
    
    if len(label) > 20:
        return False, "Year label too long (max 20 characters)"
    
    # Check for common formats like "2023/24", "2023-24", "2023"
    import re
    
    # Format: YYYY/YY or YYYY-YY or just YYYY or YYYY/YYYY
    if re.match(r'^\d{4}[/-]\d{2}$', label):
        # Validate the year progression makes sense (e.g., 2023/24)
        parts = re.split(r'[/-]', label)
        start_year = int(parts[0])
        end_year_short = int(parts[1])
        
        # The second part should be the next year's last two digits
        expected_end = (start_year + 1) % 100
        if end_year_short != expected_end:
            return False, f"Year progression doesn't match: {start_year} should be followed by {expected_end:02d}, not {end_year_short:02d}"
        
        return True, ""
    elif re.match(r'^\d{4}[/-]\d{4}$', label):
        # Full year format like "2023/2024"
        parts = re.split(r'[/-]', label)
        start_year = int(parts[0])
        end_year = int(parts[1])
        
        if end_year != start_year + 1:
            return False, f"Year progression doesn't match: {start_year} should be followed by {start_year + 1}, not {end_year}"
        
        return True, ""
    elif re.match(r'^\d{4}$', label):
        # Just a year like "2023" - this is fine
        return True, ""
    else:
        return False, "Year format should be like '2023/24', '2023-24', '2023/2024', or '2023'"


def get_recommended_next_year():
    """
    Suggest the next logical financial year label based on existing years.
    
    Returns:
        string: Suggested year label or None if can't determine
    """
    try:
        # Get the latest year by parsing the start year from each label
        latest_year = None
        latest_start = 0
        
        for year in FinancialYear.objects.all():
            try:
                start_year = year._extract_start_year(year.label)
                if start_year > latest_start:
                    latest_start = start_year
                    latest_year = year
            except ValueError:
                continue
        
        if not latest_year:
            # No years exist, suggest current calendar year
            import datetime
            current_year = datetime.datetime.now().year
            return f"{current_year}/{(current_year + 1) % 100:02d}"
        
        # Try to parse the latest year and suggest next
        import re
        match = re.match(r'^(\d{4})[/-](\d{2})$', latest_year.label)
        if match:
            start_year = int(match.group(1))
            next_start = start_year + 1
            next_end = (next_start + 1) % 100
            return f"{next_start}/{next_end:02d}"
        
        match = re.match(r'^(\d{4})[/-](\d{4})$', latest_year.label)
        if match:
            start_year = int(match.group(1))
            next_start = start_year + 1
            next_end = next_start + 1
            return f"{next_start}/{next_end}"
        
        # If it's just a year like "2023", suggest "2024"
        match = re.match(r'^(\d{4})$', latest_year.label)
        if match:
            year = int(match.group(1))
            return str(year + 1)
            
    except Exception:
        pass
    
    return None


def create_year_with_smart_defaults(label, is_current=False, user=None):
    """
    Create a new financial year with smart defaults based on the year type.
    
    Args:
        label: Year label (e.g., "2024/25")
        is_current: Whether this should be the current year
        user: User creating the year (for logging)
    
    Returns:
        tuple: (FinancialYear instance, created boolean)
    """
    import datetime
    
    # Determine if this is a future year
    current_calendar_year = datetime.datetime.now().year
    try:
        year_start = FinancialYear._extract_start_year(None, label)
        is_future_year = year_start > current_calendar_year
    except:
        is_future_year = False
    
    # Set smart defaults
    defaults = {
        'is_current': is_current,
        'is_provisional': not is_future_year,  # Future years are forecasts, current/past are provisional
        'is_forecast': is_future_year,
    }
    
    # Add helpful notes
    if is_future_year:
        defaults['notes'] = f"Future financial year - created {datetime.datetime.now().strftime('%Y-%m-%d')}. Figures will be projections/estimates."
    elif is_current:
        defaults['notes'] = f"Current financial year - created {datetime.datetime.now().strftime('%Y-%m-%d')}. Figures may be incomplete."
    else:
        defaults['notes'] = f"Financial year created {datetime.datetime.now().strftime('%Y-%m-%d')}."
    
    year, created = FinancialYear.objects.get_or_create(
        label=label,
        defaults=defaults
    )
    
    return year, created


def mark_year_as_finalized(year, user=None):
    """
    Mark a financial year as finalized (no longer provisional).
    
    Args:
        year: FinancialYear instance
        user: User performing the action (for logging)
    """
    import datetime
    
    if year.is_provisional:
        year.is_provisional = False
        year.notes += f"\nMarked as finalized on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if user:
            year.notes += f" by {user.username}"
        year.save()
        
        # Log the action
        if user:
            from .models import ActivityLog
            ActivityLog.objects.create(
                user=user,
                activity_type="financial_year",
                description=f"Marked year {year.label} as finalized",
                details={
                    "operation": "finalize_year",
                    "year_label": year.label,
                    "year_id": year.id
                }
            )


def get_data_quality_summary():
    """
    Get a summary of data quality across all financial years.
    
    Returns:
        dict with statistics about year coverage and data quality
    """
    from .models import FinancialFigure
    
    summary = {
        'total_years': FinancialYear.objects.count(),
        'current_years': FinancialYear.objects.filter(is_current=True).count(),
        'provisional_years': FinancialYear.objects.filter(is_provisional=True).count(),
        'forecast_years': FinancialYear.objects.filter(is_forecast=True).count(),
        'finalized_years': FinancialYear.objects.filter(is_provisional=False, is_forecast=False).count(),
        'years_with_data': FinancialYear.objects.filter(
            id__in=FinancialFigure.objects.values_list('year_id', flat=True).distinct()
        ).count(),
        'years_without_data': FinancialYear.objects.exclude(
            id__in=FinancialFigure.objects.values_list('year_id', flat=True).distinct()
        ).count(),
    }
    
    return summary
