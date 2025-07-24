"""Retrieve factoids associated with counters."""

from typing import List, Dict, Optional, Any
import random
import logging

from .models import Factoid

logger = logging.getLogger(__name__)


def previous_year_label(label: str) -> Optional[str]:
    """Return the previous financial year label if parsable."""
    try:
        # Accept formats like ``2023/24`` or ``2023-24`` by normalising the
        # separator. Using ``replace`` allows us to handle mixed inputs without
        # multiple branches.
        clean = str(label).replace("-", "/")
        parts = clean.split("/")
        if len(parts) == 2:
            # Keep the same width for the trailing year so ``23/24`` becomes
            # ``22/23`` rather than ``22/23``. This mirrors the original
            # formatting supplied by admins.
            first = int(parts[0])
            second_str = parts[1]
            second = int(second_str)
            prev_first = first - 1
            prev_second = second - 1
            second_fmt = f"{prev_second:0{len(second_str)}d}"
            return f"{prev_first}/{second_fmt}"
        base = int(parts[0])
        return str(base - 1)
    except (TypeError, ValueError):
        # Invalid or non-numeric labels simply return ``None`` so callers can
        # decide how to handle missing data gracefully.
        return None


def get_factoids(counter_slug: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Return factoids linked to the given counter slug.

    ``context`` can include placeholders such as ``value`` or ``name`` which
    will be substituted into the factoid text. Missing keys are left in place so
    admins can easily spot problems.
    """
    # Look up any Factoid objects related to a counter with this slug. This
    # keeps the logic flexible so managers can add new snippets without code
    # changes. When no factoids exist we fall back to the built-in examples so
    # templates always have something to show during development.
    qs = Factoid.objects.filter(counters__slug=counter_slug)
    data = list(qs.values("text", "factoid_type"))

    if not data:
        fallback = {
            "total_debt": [
                {"icon": "fa-arrow-up text-red-600", "text": "Debt up 5% vs last year"},
                {"icon": "fa-city", "text": "Highest debt: Example Council"},
                {"icon": "fa-city", "text": "Lowest debt: Sample Borough"},
            ],
            "total_reserves": [
                {"icon": "fa-arrow-down text-green-600", "text": "Reserves down 2%"},
            ],
        }
        data = fallback.get(counter_slug, [])

    if context:
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        filtered = []
        for item in data:
            safe = SafeDict(**context)
            if item.get("factoid_type") == "percent_change":
                # Skip percent change factoids when the required numeric values
                # are missing. Returning ``filtered`` without this item ensures
                # invalid factoids disappear from playlists.
                if context.get("raw") in (None, ""):
                    continue
                if context.get("previous_raw") in (None, ""):
                    continue

                # ``raw`` values are numbers from counters while
                # ``previous_raw`` holds the prior year's figure. We coerce both
                # to floats so the percentage can be calculated reliably.
                try:
                    current = float(context.get("raw"))
                    prev = float(context.get("previous_raw"))
                except (TypeError, ValueError):
                    continue

                if prev:
                    # Normal case: compute the percentage difference using the
                    # previous year as the baseline.
                    change = (current - prev) / prev * 100
                    safe["value"] = f"{change:.1f}%"
                    if change > 0:
                        item["icon"] = "fa-chevron-up text-green-600"
                    elif change < 0:
                        item["icon"] = "fa-chevron-down text-red-600"
                    else:
                        item["icon"] = "fa-chevron-right text-gray-500"
                else:
                    # ``prev`` may legitimately be ``0``. Avoid a divide-by-zero
                    # and show ``0%`` with a neutral indicator.
                    safe["value"] = "0%"
                    item["icon"] = "fa-chevron-right text-gray-500"

            item = item.copy()
            item["text"] = item["text"].format_map(safe)
            filtered.append(item)

        data = filtered

    random.shuffle(data)
    return data


def get_enhanced_factoids(counter_slug: str, council=None, year=None, base_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Enhanced factoids with support for calculated fields, characteristics, and financial data.
    
    Args:
        counter_slug: Counter slug to get factoids for
        council: Council instance for context building
        year: FinancialYear instance for context building  
        base_context: Additional context from counter calculations (value, raw, etc.)
        
    Returns:
        List of factoid dictionaries with rendered text
    """
    # Start with the base factoid data
    data = get_factoids(counter_slug, context=None)  # Get raw templates first
    
    if not data:
        return data
    
    # Build enhanced context if council is provided
    enhanced_context = {}
    if council:
        try:
            from .calculators import get_data_context_for_council
            enhanced_context = get_data_context_for_council(council, year, counter_slug)
        except Exception as e:
            logger.warning(f"Failed to build enhanced context for {council.slug}: {e}")
    
    # Merge base context (from counter calculations) with enhanced context
    if base_context:
        enhanced_context.update(base_context)
    
    # Now use the original logic but with enhanced context
    if enhanced_context:
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        filtered = []
        for item in data:
            safe = SafeDict(**enhanced_context)
            
            if item.get("factoid_type") == "percent_change":
                # Skip percent change factoids when the required numeric values
                # are missing. Returning ``filtered`` without this item ensures
                # invalid factoids disappear from playlists.
                if enhanced_context.get("raw") in (None, ""):
                    continue
                if enhanced_context.get("previous_raw") in (None, ""):
                    continue

                # ``raw`` values are numbers from counters while
                # ``previous_raw`` holds the prior year's figure. We coerce both
                # to floats so the percentage can be calculated reliably.
                try:
                    current = float(enhanced_context.get("raw"))
                    prev = float(enhanced_context.get("previous_raw"))
                except (TypeError, ValueError):
                    continue

                if prev:
                    # Normal case: compute the percentage difference using the
                    # previous year as the baseline.
                    change = (current - prev) / prev * 100
                    safe["value"] = f"{change:.1f}%"
                    if change > 0:
                        item["icon"] = "fa-chevron-up text-green-600"
                    elif change < 0:
                        item["icon"] = "fa-chevron-down text-red-600"
                    else:
                        item["icon"] = "fa-chevron-right text-gray-500"
                else:
                    # ``prev`` may legitimately be ``0``. Avoid a divide-by-zero
                    # and show ``0%`` with a neutral indicator.
                    safe["value"] = "0%"
                    item["icon"] = "fa-chevron-right text-gray-500"

            item = item.copy()
            
            try:
                item["text"] = item["text"].format_map(safe)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to format factoid text '{item['text']}': {e}")
                # Keep original text if formatting fails
                
            filtered.append(item)

        data = filtered

    random.shuffle(data)
    return data


def get_factoids_for_template_system(counter_slug: str, council=None, year=None, base_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Get factoids compatible with the new FactoidTemplate system.
    
    This function bridges the old Factoid system with the new FactoidTemplate
    system by providing enhanced context for template rendering.
    
    Args:
        counter_slug: Counter slug to get factoids for
        council: Council instance
        year: FinancialYear instance
        base_context: Base context from counter calculations
        
    Returns:
        List of rendered factoids from both old and new systems
    """
    from .models import FactoidTemplate, CounterDefinition
    
    factoids = []
    
    # 1. Get legacy factoids with enhanced context
    legacy_factoids = get_enhanced_factoids(counter_slug, council, year, base_context)
    factoids.extend(legacy_factoids)
    
    # 2. Get new template-based factoids
    try:
        # Find counter definition
        counter = CounterDefinition.objects.filter(slug=counter_slug).first()
        if counter:
            # Get templates associated with this counter
            templates = FactoidTemplate.objects.filter(
                counters=counter,
                is_active=True
            ).order_by('-priority')
            
            # Build enhanced context for templates
            template_context = {}
            if council:
                try:
                    from .calculators import get_data_context_for_council
                    template_context = get_data_context_for_council(council, year, counter_slug)
                except Exception as e:
                    logger.warning(f"Failed to build template context: {e}")
            
            if base_context:
                template_context.update(base_context)
            
            # Render each template
            for template in templates:
                try:
                    rendered_text = render_factoid_template(template, template_context)
                    if rendered_text:
                        factoids.append({
                            "text": rendered_text,
                            "factoid_type": template.factoid_type,
                            "icon": f"fa-{template.emoji}" if template.emoji else "fa-info",
                            "color_scheme": template.color_scheme,
                        })
                except Exception as e:
                    logger.warning(f"Failed to render template {template.slug}: {e}")
                    
    except Exception as e:
        logger.warning(f"Failed to get template factoids for {counter_slug}: {e}")
    
    random.shuffle(factoids)
    return factoids


def render_factoid_template(template, context: Dict[str, Any]) -> Optional[str]:
    """
    Render a FactoidTemplate using Django's template system for robust rendering.
    
    Args:
        template: FactoidTemplate instance
        context: Context dictionary with all available variables
        
    Returns:
        Rendered template text or None if rendering fails
    """
    from django.template import Template, Context
    from django.template.engine import Engine
    from decimal import Decimal
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Prepare context data with proper formatting and validation
        safe_context = _build_safe_context(context, template)
        
        # Log debug info for troubleshooting
        logger.info(f"Rendering template '{template.name}' with context keys: {list(safe_context.keys())}")
        
        # DEBUG: Log calculated data specifically
        if 'calculated' in safe_context:
            logger.info(f"Calculated data available: {safe_context['calculated']}")
        else:
            logger.info("No calculated data in context")
            
        # DEBUG: Log template text
        logger.info(f"Template text: {template.template_text}")
        
        # Create Django template from the template text
        django_template = Template(template.template_text)
        django_context = Context(safe_context)
        
        # Render with Django's robust template engine
        rendered_text = django_template.render(django_context)
        
        # Clean up any remaining empty spaces or formatting issues
        rendered_text = _clean_rendered_text(rendered_text)
        
        logger.info(f"Successfully rendered template '{template.name}': {rendered_text[:100]}...")
        return rendered_text if rendered_text.strip() else None
        
    except Exception as e:
        logger.error(f"Failed to render template '{template.name}': {e}")
        logger.error(f"Template text: {template.template_text}")
        logger.error(f"Available context keys: {list(context.keys())}")
        return None


def _build_safe_context(context: Dict[str, Any], template) -> Dict[str, Any]:
    """
    Build a safe context dictionary with proper data validation and formatting.
    
    Args:
        context: Raw context data
        template: FactoidTemplate instance for type-specific formatting
        
    Returns:
        Safe context dictionary ready for Django template rendering
    """
    from decimal import Decimal
    import logging
    
    logger = logging.getLogger(__name__)
    safe_context = {}
    
    # Copy all values, preserving nested dictionaries
    for key, value in context.items():
        if value is not None:
            safe_context[key] = value
    
    # Apply special formatting to calculated values
    if 'calculated' in safe_context and isinstance(safe_context['calculated'], dict):
        formatted_calculated = {}
        for field_name, value in safe_context['calculated'].items():
            formatted_calculated[field_name] = _format_calculated_value(value, field_name)
        safe_context['calculated'] = formatted_calculated
        
    # Apply special formatting to financial values  
    if 'financial' in safe_context and isinstance(safe_context['financial'], dict):
        formatted_financial = {}
        for field_name, value in safe_context['financial'].items():
            formatted_financial[field_name] = _format_financial_value(value)
        safe_context['financial'] = formatted_financial
        
    # Ensure core template variables are always available
    safe_context.setdefault('council_name', 'Unknown Council')
    safe_context.setdefault('year_label', 'Unknown Year')
    safe_context.setdefault('value', 0)
    safe_context.setdefault('formatted', '£0')
    
    logger.debug(f"Built safe context with keys: {list(safe_context.keys())}")
    if 'characteristic' in safe_context:
        logger.debug(f"Characteristic data: {safe_context['characteristic']}")
    if 'calculated' in safe_context:
        logger.debug(f"Calculated data: {safe_context['calculated']}")
        
    return safe_context


def _format_calculated_value(value, field_name: str):
    """Format calculated values based on their type and field name."""
    from decimal import Decimal
    
    if value is None:
        return 0
        
    try:
        # Convert to numeric if possible
        if isinstance(value, str):
            # Remove currency symbols and commas
            clean_value = value.replace('£', '').replace(',', '').strip()
            if clean_value:
                value = float(clean_value)
            else:
                return 0
        
        # Format per capita values specially
        if 'per_capita' in field_name:
            if isinstance(value, (int, float, Decimal)) and value > 0:
                return f"£{float(value):,.0f}"
            else:
                return "£0"
        
        # Format other calculated values
        if isinstance(value, (int, float, Decimal)):
            if abs(value) >= 1000000:
                return f"£{float(value):,.0f}"
            elif abs(value) >= 1:
                return f"£{float(value):,.2f}"
            else:
                return f"£{float(value):.2f}"
                
        return str(value)
        
    except (ValueError, TypeError):
        return str(value) if value else "0"


def _format_financial_value(value):
    """Format financial values consistently."""
    from decimal import Decimal
    
    if value is None:
        return "£0"
        
    try:
        if isinstance(value, str):
            clean_value = value.replace('£', '').replace(',', '').strip()
            if clean_value:
                value = float(clean_value)
            else:
                return "£0"
                
        if isinstance(value, (int, float, Decimal)):
            return f"£{float(value):,.0f}"
            
        return str(value)
        
    except (ValueError, TypeError):
        return str(value) if value else "£0"


def _clean_rendered_text(text: str) -> str:
    """Clean up rendered text by removing extra whitespace and formatting issues."""
    if not text:
        return ""
        
    # Remove multiple consecutive spaces
    import re
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove any remaining placeholder brackets
    text = re.sub(r'\{\s*\}', '', text)
    
    return text
