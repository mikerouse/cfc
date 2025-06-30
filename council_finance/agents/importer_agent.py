import json
from pathlib import Path
from .base import AgentBase
from council_finance.models import Council, FinancialYear, FigureSubmission

class ImporterAgent(AgentBase):
    """Loads council data from a JSON file."""
    name = 'ImporterAgent'

    def run(self, source='councils-migration.json', **kwargs):
        path = Path(source)
        with path.open() as fh:
            data = json.load(fh)
        for council_data in data.get('councils', []):
            council, _ = Council.objects.get_or_create(
                slug=council_data['slug'],
                defaults={
                    'name': council_data.get('name', ''),
                },
            )
            for field, year_map in council_data.get('values', {}).items():
                for year_label, value in year_map.items():
                    fy, _ = FinancialYear.objects.get_or_create(label=year_label)
                    FigureSubmission.objects.update_or_create(
                        council=council,
                        year=fy,
                        field_name=field,
                        defaults={'value': value},
                    )
