from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    FigureSubmission,
    CounterDefinition,
)
import ast
import operator

class CounterAgent(AgentBase):
    """Simple counter that retrieves a figure for a council/year."""
    name = 'CounterAgent'

    def run(self, council_slug, year_label, **kwargs):
        """Return all counter values for a council/year."""
        council = Council.objects.get(slug=council_slug)
        year = FinancialYear.objects.get(label=year_label)
        counters = CounterDefinition.objects.all()

        # Preload all figures for this council/year so repeated lookups are cheap
        figure_map = {
            f.field_name: float(f.value)
            for f in FigureSubmission.objects.filter(council=council, year=year)
        }

        def eval_formula(formula: str) -> float:
            """Safely evaluate a formula using the loaded figure values."""

            allowed_ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
            }

            def _eval(node):
                if isinstance(node, ast.Expression):
                    return _eval(node.body)
                if isinstance(node, ast.Num):  # numbers in the expression
                    return node.n
                if isinstance(node, ast.BinOp):
                    return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
                if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                    return -_eval(node.operand)
                if isinstance(node, ast.Name):
                    # Look up the figure value, defaulting to 0 if missing
                    return figure_map.get(node.id, 0)
                raise ValueError("Unsupported expression element")

            tree = ast.parse(formula, mode="eval")
            return float(_eval(tree))

        results = {}
        for counter in counters:
            try:
                total = eval_formula(counter.formula)
            except Exception:
                total = 0

            results[counter.slug] = {
                "value": total,
                "formatted": counter.format_value(total),
            }

        return results
