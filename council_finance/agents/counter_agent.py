from .base import AgentBase
from council_finance.models import Council, FinancialYear, FigureSubmission

class CounterAgent(AgentBase):
    """Simple counter that retrieves a figure for a council/year."""
    name = 'CounterAgent'

    def run(self, council_slug, field_name, year_label, **kwargs):
        council = Council.objects.get(slug=council_slug)
        year = FinancialYear.objects.get(label=year_label)
        try:
            figure = FigureSubmission.objects.get(
                council=council, year=year, field_name=field_name
            )
            print(f"{council.name} {field_name} {year_label}: {figure.value}")
        except FigureSubmission.DoesNotExist:
            print("No data found")
