"""Retrieve factoids associated with counters."""

from typing import List, Dict, Optional, Any
import random

from .models import Factoid


def previous_year_label(label: str) -> Optional[str]:
    """Return the previous financial year label if parsable."""
    try:
        base = int(str(label).split("/")[0])
    except (TypeError, ValueError):
        return None
    return str(base - 1)


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

        for item in data:
            safe = SafeDict(**context)
            if (
                item.get("factoid_type") == "percent_change"
                and context.get("previous_raw") not in (None, 0)
                and context.get("raw") not in (None, "")
            ):
                try:
                    current = float(context.get("raw"))
                    prev = float(context.get("previous_raw"))
                    change = (current - prev) / prev * 100
                    safe["value"] = f"{change:.1f}%"
                except Exception:
                    pass
            item["text"] = item["text"].format_map(safe)

    random.shuffle(data)
    return data
