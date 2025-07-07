"""Simple factoid engine for counters.

This module provides a helper to fetch factoids for a given counter
slug. In a real implementation this might query the database or
perform calculations based on financial data. For now we return
static examples so the templates can demonstrate the feature.
"""
from typing import Dict, List
import random

FACTOID_DATA: Dict[str, List[Dict[str, str]]] = {
    "total_debt": [
        {"icon": "fa-arrow-up text-red-600", "text": "Debt up 5% vs last year"},
        {"icon": "fa-city", "text": "Highest debt: Example Council"},
        {"icon": "fa-city", "text": "Lowest debt: Sample Borough"},
    ],
    "total_reserves": [
        {"icon": "fa-arrow-down text-green-600", "text": "Reserves down 2%"},
    ],
}


def get_factoids(counter_slug: str) -> List[Dict[str, str]]:
    """Return a list of factoids for the given counter slug."""
    factoids = FACTOID_DATA.get(counter_slug, [])
    # Shuffle so repeated page loads vary the order.
    random.shuffle(factoids)
    return factoids
