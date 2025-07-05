from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    FigureSubmission,
    CounterDefinition,
)
from django.db.models import Q
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
        # Only include counters relevant to this council's type. When a counter
        # has no types assigned it applies everywhere.
        if council.council_type_id:
            counters = counters.filter(
                Q(council_types__isnull=True) | Q(council_types=council.council_type)
            )
        else:
            counters = counters.filter(council_types__isnull=True)
        counters = counters.distinct()

        # Preload all figures for this council/year. Any record flagged as
        # needing population is recorded so formulas referencing it can raise a
        # helpful error instead of silently using zero.
        figure_map = {}
        missing = set()
        figures = FigureSubmission.objects.filter(council=council, year=year)
        if council.council_type_id:
            figures = figures.filter(
                Q(field__council_types__isnull=True)
                | Q(field__council_types=council.council_type)
            )
        else:
            figures = figures.filter(field__council_types__isnull=True)
        figures = figures.select_related("field").distinct()

        for f in figures:
            slug = f.field.slug
            if f.needs_populating or f.value in (None, ""):
                missing.add(slug)
                continue
            try:
                figure_map[slug] = float(f.value)
            except (TypeError, ValueError):
                missing.add(slug)

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
                    # If the value is missing, surface a helpful error so the
                    # user knows which figure needs to be populated.
                    if node.id in missing:
                        raise ValueError(
                            (
                                "Counter failed - no %s figure is held for %s in %s. "
                                "Please populate the figure from the council's official sources and try again."
                            )
                            % (node.id.replace('_', ' '), council.name, year.label)
                        )
                    return figure_map.get(node.id, 0)
                raise ValueError("Unsupported expression element")

            tree = ast.parse(formula, mode="eval")
            return float(_eval(tree))

        results = {}
        for counter in counters:
            try:
                total = eval_formula(counter.formula)
            except ValueError as e:
                results[counter.slug] = {"error": str(e)}
                continue
            except Exception:
                results[counter.slug] = {"error": "calculation failed"}
                continue

            results[counter.slug] = {
                "value": total,
                "formatted": counter.format_value(total),
            }

        return results
