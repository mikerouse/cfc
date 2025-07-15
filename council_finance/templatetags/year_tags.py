"""
Template tags for financial year utilities.
"""

from django import template
from django.utils.safestring import mark_safe
from ..year_utils import get_figure_reliability_warning

register = template.Library()


@register.simple_tag
def year_status_badge(year):
    """Return an HTML badge showing the year status."""
    if not year:
        return ""
    
    status = year.status
    if status == 'current':
        return mark_safe('<span class="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Current</span>')
    elif status == 'future':
        return mark_safe('<span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">Future</span>')
    elif status == 'past':
        return mark_safe('<span class="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">Past</span>')
    else:
        return mark_safe('<span class="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">Unknown</span>')


@register.simple_tag
def year_reliability_icon(year):
    """Return an emoji icon indicating data reliability."""
    if not year:
        return "❓"
    
    status = year.status
    if status == 'current':
        return "📊"  # Chart - data in progress
    elif status == 'future':
        return "🔮"  # Crystal ball - predictions
    elif status == 'past':
        return "✅"  # Check mark - reliable
    else:
        return "❓"  # Question mark - unknown


@register.inclusion_tag('council_finance/year_reliability_warning.html')
def show_year_reliability_warning(year):
    """Show a reliability warning for the given year."""
    warning = get_figure_reliability_warning(year) if year else None
    return {'warning': warning, 'year': year}


@register.filter
def year_status_class(year):
    """Return CSS class for year status styling."""
    if not year:
        return "text-gray-500"
    
    status = year.status
    if status == 'current':
        return "text-green-600"
    elif status == 'future':
        return "text-blue-600"
    elif status == 'past':
        return "text-gray-600"
    else:
        return "text-yellow-600"
