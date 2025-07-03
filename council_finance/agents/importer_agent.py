import json
from pathlib import Path
from .base import AgentBase
from council_finance.models import (
    Council,
    CouncilType,
    FinancialYear,
    FigureSubmission,
    DataField,
)

class ImporterAgent(AgentBase):
    """Loads council data from a JSON file."""
    name = 'ImporterAgent'

    def run(self, source='councils-migration.json', **kwargs):
        path = Path(source)
        with path.open() as fh:
            data = json.load(fh)
        for council_data in data.get('councils', []):
            type_name = council_data.get('council_type', '')
            council_type = None
            if type_name:
                # Create types on the fly so the dataset can introduce new
                # categories without manual setup.
                council_type, _ = CouncilType.objects.get_or_create(name=type_name)

            council, _ = Council.objects.get_or_create(
                slug=council_data['slug'],
                defaults={
                    'name': council_data.get('name', ''),
                    'council_type': council_type,
                },
            )
            for field, year_map in council_data.get('values', {}).items():
                df, _ = DataField.objects.get_or_create(
                    slug=field, defaults={"name": field.replace("_", " ").title()}
                )
                for year_label, value in year_map.items():
                    fy, _ = FinancialYear.objects.get_or_create(label=year_label)
                    # Blank entries mean we do not have the figure for that
                    # council/year. Preserve the blank and mark the record so
                    # staff can find and populate it later.
                    cleaned = str(value).strip() if value is not None else ""
                    needs_populating = cleaned == ""
                    FigureSubmission.objects.update_or_create(
                        council=council,
                        year=fy,
                        field=df,
                        defaults={
                            'value': cleaned,
                            'needs_populating': needs_populating,
                        },
                    )
