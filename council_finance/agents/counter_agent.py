from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    FigureSubmission,
    CounterDefinition,
    FinancialFigure,
)


class MissingDataError(ValueError):
    """Raised when a required figure is absent for a council/year."""
    pass
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
        if council.council_type:
            counters = counters.filter(
                Q(council_types__isnull=True) | Q(council_types=council.council_type)
            )
        else:
            counters = counters.filter(council_types__isnull=True)
        counters = counters.distinct()

        # Preload all figures for this council/year using the new FinancialFigure model
        figure_map = {}
        missing = set()
        
        # Try new model first (FinancialFigure)
        financial_figures = FinancialFigure.objects.filter(council=council, year=year)
        if council.council_type:
            financial_figures = financial_figures.filter(
                Q(field__council_types__isnull=True)
                | Q(field__council_types=council.council_type)
            )
        else:
            financial_figures = financial_figures.filter(field__council_types__isnull=True)
        financial_figures = financial_figures.select_related("field").distinct()

        for f in financial_figures:
            slug = f.field.slug
            # Record slugs with empty or invalid values so we can surface a
            # helpful "no data" message later.
            if f.value in (None, ""):
                missing.add(slug)
                continue
            try:
                figure_map[slug] = float(f.value)
            except (TypeError, ValueError):
                missing.add(slug)
        
        # Fallback to legacy model (FigureSubmission) if no data found in new model
        if not figure_map:
            legacy_figures = FigureSubmission.objects.filter(council=council, year=year)
            if council.council_type:
                legacy_figures = legacy_figures.filter(
                    Q(field__council_types__isnull=True)
                    | Q(field__council_types=council.council_type)
                )
            else:
                legacy_figures = legacy_figures.filter(field__council_types__isnull=True)
            legacy_figures = legacy_figures.select_related("field").distinct()

            for f in legacy_figures:
                slug = f.field.slug
                # Record slugs with empty or invalid values so we can surface a
                # helpful "no data" message later.  Figures marked as needing
                # population are treated the same as entirely missing entries.
                if f.needs_populating or f.value in (None, ""):
                    missing.add(slug)
                    continue
                try:
                    figure_map[slug] = float(f.value)
                except (TypeError, ValueError):
                    missing.add(slug)

        def eval_formula(formula: str) -> float:
            """Safely evaluate a formula using the loaded figure values."""
            
            # Handle field slugs with hyphens by creating a mapping
            # from safe variable names to field values
            safe_vars = {}
            safe_formula = formula
            
            # Replace field slugs containing hyphens with safe variable names
            for field_slug, value in figure_map.items():
                if '-' in field_slug:
                    # Create a safe variable name by replacing hyphens with underscores
                    safe_var_name = field_slug.replace('-', '_')
                    safe_vars[safe_var_name] = value
                    # Replace the field slug in the formula
                    safe_formula = safe_formula.replace(field_slug, safe_var_name)
                else:
                    safe_vars[field_slug] = value
            

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
                    # When a figure is missing entirely return an explicit
                    # error so callers can display "No data" instead of zero.
                    if node.id not in safe_vars:
                        raise MissingDataError(node.id)
                    return safe_vars[node.id]
                raise ValueError("Unsupported expression element")

            tree = ast.parse(safe_formula, mode="eval")
            return float(_eval(tree))

        results = {}
        for counter in counters:
            try:
                total = eval_formula(counter.formula)
            except MissingDataError:
                # No figure exists for this counter. Indicate lack of data so
                # the UI can show an appropriate placeholder.
                results[counter.slug] = {
                    "value": None,
                    "formatted": "No data",
                    "error": None,
                }
                continue
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
