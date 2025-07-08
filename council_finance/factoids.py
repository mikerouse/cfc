"""Retrieve factoids associated with counters."""

from typing import List, Dict, Optional, Any
import random

from .models import Factoid


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
