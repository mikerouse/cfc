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
    Render a FactoidTemplate with the given context.
    
    Args:
        template: FactoidTemplate instance
        context: Context dictionary with all available variables
        
    Returns:
        Rendered template text or None if rendering fails
    """
    try:
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        
        safe_context = SafeDict(**context)
        
        # Handle nested context (e.g., characteristic.population)
        def resolve_nested_key(key):
            if '.' in key:
                parts = key.split('.')
                value = safe_context
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return "{" + key + "}"
                return value
            return safe_context[key]
        
        # Custom format_map that handles nested keys
        import re
        template_text = template.template_text
        
        # Find all template variables
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template_text)
        
        for match in matches:
            var_name = match.strip()
            try:
                value = resolve_nested_key(var_name)
                # Format the value if it's numeric
                if isinstance(value, (int, float)):
                    if template.factoid_type == 'per_capita' and 'per_capita' in var_name:
                        # Format per capita values nicely
                        value = f"£{value:,.0f}"
                    elif isinstance(value, float):
                        value = f"{value:,.1f}"
                    else:
                        value = f"{value:,}"
                
                template_text = template_text.replace('{{' + match + '}}', str(value))
            except Exception as e:
                logger.warning(f"Failed to resolve template variable {var_name}: {e}")
        
        return template_text if template_text else None
        
    except Exception as e:
        logger.warning(f"Failed to render template {template.slug}: {e}")
        return None
