from typing import Iterable

from django.db import transaction

from .models import (
    Council,
    FinancialYear,
    DataField,
    FigureSubmission,
    DataIssue,
)
# Import the list of protected slugs so we know which fields apply across
# all years. These fields are not repeated for each financial period and
# therefore should only generate a single DataIssue with ``year`` set to
# ``None`` if missing.
from .models.field import PROTECTED_SLUGS


def assess_data_issues() -> int:
    """Rebuild the :class:`DataIssue` table by scanning current figures."""
    DataIssue.objects.all().delete()
    years = list(FinancialYear.objects.all())
    fields = list(DataField.objects.all())
    yearless_fields = set(
        FigureSubmission.objects.filter(year__isnull=True).values_list("field_id", flat=True)
    )
    # Protected fields like "population" or "council_location" are intended to
    # exist once for a council regardless of financial year. Include their IDs
    # in the ``yearless_fields`` set so we don't generate per-year issues.
    yearless_fields.update(df.id for df in fields if df.slug in PROTECTED_SLUGS)
    existing = {
        (fs.council_id, fs.field_id, fs.year_id): fs
        for fs in FigureSubmission.objects.all()
    }
    count = 0
    with transaction.atomic():
        for council in Council.objects.all():
            for field in fields:
                allowed = list(field.council_types.all())
                if allowed and council.council_type not in allowed:
                    continue
                year_ids: Iterable[int | None]
                if field.id in yearless_fields:
                    year_ids = [None]
                else:
                    year_ids = [y.id for y in years]
                for year_id in year_ids:
                    fs = existing.get((council.id, field.id, year_id))
                    if not fs or fs.needs_populating or fs.value in (None, ""):
                        DataIssue.objects.create(
                            council=council,
                            field=field,
                            year_id=year_id,
                            issue_type="missing",
                        )
                        count += 1
                    else:
                        val = str(fs.value).strip()
                        if field.content_type in {"monetary", "integer"} and val in {"0", "0.0"}:
                            DataIssue.objects.create(
                                council=council,
                                field=field,
                                year_id=year_id,
                                issue_type="suspicious",
                                value=val,
                            )
                            count += 1
    return count
