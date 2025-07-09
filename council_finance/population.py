"""Utility functions for population cache management."""

from typing import List

from django.db import transaction

from .models import Council, DataField, FigureSubmission


def reconcile_populations() -> int:
    """Update ``Council.latest_population`` for all councils.

    Returns the number of councils that had their cache updated. If the
    ``population`` field is not defined, no action is taken.
    """
    pop_field = DataField.objects.filter(slug="population").first()
    if not pop_field:
        return 0

    updated = 0
    # Wrap in a transaction so changes are applied atomically
    with transaction.atomic():
        for council in Council.objects.all():
            latest = (
                FigureSubmission.objects.filter(council=council, field=pop_field)
                .select_related("year")
                .order_by("-year__label")
                .first()
            )
            if latest:
                try:
                    value = int(float(latest.value))
                except (TypeError, ValueError):
                    value = None
            else:
                value = None
            if council.latest_population != value:
                council.latest_population = value
                council.save(update_fields=["latest_population"])
                updated += 1
    return updated
