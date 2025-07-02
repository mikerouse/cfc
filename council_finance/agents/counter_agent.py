from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    FigureSubmission,
    CounterDefinition,
)

class CounterAgent(AgentBase):
    """Simple counter that retrieves a figure for a council/year."""
    name = 'CounterAgent'

    def run(self, council_slug, year_label, **kwargs):
        """Return all counter values for a council/year."""
        council = Council.objects.get(slug=council_slug)
        year = FinancialYear.objects.get(label=year_label)
        counters = CounterDefinition.objects.all()
        results = {}
        for counter in counters:
            fields = [f.strip() for f in counter.formula.split("+") if f.strip()]
            total = 0
            for field in fields:
                try:
                    figure = FigureSubmission.objects.get(
                        council=council, year=year, field_name=field
                    )
                    total += float(figure.value)
                except (FigureSubmission.DoesNotExist, ValueError):
                    continue
            results[counter.slug] = total
        return results
