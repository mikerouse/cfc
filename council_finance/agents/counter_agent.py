import ast
import logging
import operator
from django.db.models import Q
from django.utils import timezone

from .base import AgentBase
from council_finance.models import (
    Council,
    FinancialYear,
    FigureSubmission,
    CounterDefinition,
    FinancialFigure,
)

# Event Viewer integration
try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False

logger = logging.getLogger(__name__)


def log_counter_event(level, category, title, message, details=None):
    """Log counter calculation events to Event Viewer system"""
    if not EVENT_VIEWER_AVAILABLE:
        return
    
    try:
        event_details = {
            'module': 'counter_agent',
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            event_details.update(details)
        
        SystemEvent.objects.create(
            source='counter_agent',
            level=level,
            category=category,
            title=title,
            message=message,
            details=event_details
        )
        
    except Exception as e:
        logger.error(f"Failed to log counter Event Viewer event: {e}")


class MissingDataError(Exception):
    """Raised when a required field is missing from the dataset."""
    pass


class CounterAgent(AgentBase):
    """Simple counter that retrieves a figure for a council/year."""
    name = 'CounterAgent'

    def run(self, council_slug, year_label, **kwargs):
        """Return all counter values for a council/year."""
        calculation_start = timezone.now()
        
        try:
            council = Council.objects.get(slug=council_slug)
            year = FinancialYear.objects.get(label=year_label)
        except Council.DoesNotExist:
            log_counter_event(
                'error', 'data_integrity',
                'Council Not Found in Counter Calculation',
                f'Council {council_slug} not found for counter calculation',
                details={
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'error_type': 'Council.DoesNotExist'
                }
            )
            return {}
        except FinancialYear.DoesNotExist:
            log_counter_event(
                'error', 'data_integrity',
                'Financial Year Not Found in Counter Calculation',
                f'Financial Year {year_label} not found for counter calculation',
                details={
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'error_type': 'FinancialYear.DoesNotExist'
                }
            )
            return {}
        
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
        
        # Log counter calculation start
        log_counter_event(
            'info', 'calculation',
            'Counter Calculation Started',
            f'Starting counter calculation for {council.name} ({year_label})',
            details={
                'council_slug': council_slug,
                'council_name': council.name,
                'year_label': year_label,
                'counters_to_calculate': list(counters.values_list('slug', flat=True))
            }
        )

        # Preload all figures for this council/year using the new FinancialFigure model
        figure_map = {}
        missing = set()
        
        # Try new model first (FinancialFigure)
        financial_figures_query_start = timezone.now()
        financial_figures = FinancialFigure.objects.filter(council=council, year=year)
        if council.council_type:
            financial_figures = financial_figures.filter(
                Q(field__council_types__isnull=True)
                | Q(field__council_types=council.council_type)
            )
        else:
            financial_figures = financial_figures.filter(field__council_types__isnull=True)
        financial_figures = financial_figures.select_related("field").distinct()
        
        financial_figures_list = list(financial_figures)  # Execute query
        query_time = (timezone.now() - financial_figures_query_start).total_seconds()
        
        # Log data retrieval results - critical for Birmingham debugging
        log_counter_event(
            'info', 'data_access',
            'Financial Figures Retrieved for Counter Calculation',
            f'Found {len(financial_figures_list)} financial figures for {council.name} ({year_label})',
            details={
                'council_slug': council_slug,
                'year_label': year_label,
                'figures_found_count': len(financial_figures_list),
                'query_time_seconds': query_time,
                'fields_found': [f.field.slug for f in financial_figures_list]
            }
        )

        for f in financial_figures_list:
            slug = f.field.slug
            # Record slugs with empty or invalid values so we can surface a
            # helpful "no data" message later.
            if f.value in (None, ""):
                missing.add(slug)
                # Log missing/empty values for Birmingham debugging
                log_counter_event(
                    'warning', 'data_quality',
                    'Empty Financial Figure Value in Counter Calculation',
                    f'Field {slug} has empty value for {council.name} ({year_label})',
                    details={
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'field_slug': slug,
                        'field_name': f.field.name,
                        'value_found': f.value,
                        'reason': 'empty_or_null_value'
                    }
                )
                continue
            try:
                figure_map[slug] = float(f.value)
            except (TypeError, ValueError) as conversion_error:
                missing.add(slug)
                # Log conversion errors - critical for Birmingham data issues
                log_counter_event(
                    'error', 'data_quality',
                    'Financial Figure Conversion Failed in Counter Calculation',
                    f'Failed to convert {slug} value to float for {council.name} ({year_label}): {f.value}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'field_slug': slug,
                        'field_name': f.field.name,
                        'invalid_value': str(f.value),
                        'error_type': type(conversion_error).__name__,
                        'reason': 'type_conversion_failed'
                    }
                )
        
        # Also include calculated fields by getting the unified data context
        # This is CRITICAL for Birmingham data issue debugging
        data_context_start = timezone.now()
        
        try:
            from council_finance.calculators import get_data_context_for_council
            
            # Get the comprehensive data context that includes calculated fields
            data_context = get_data_context_for_council(council, year)
            data_context_time = (timezone.now() - data_context_start).total_seconds()
            
            # Log data context retrieval success
            log_counter_event(
                'info', 'data_access',
                'Data Context Retrieved for Counter Calculation',
                f'Retrieved data context for {council.name} ({year_label}) in {data_context_time:.3f}s',
                details={
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'data_context_time_seconds': data_context_time,
                    'calculated_fields_count': len(data_context.get('calculated', {})),
                    'characteristic_fields_count': len(data_context.get('characteristic', {})),
                    'calculated_fields': list(data_context.get('calculated', {}).keys()),
                    'characteristic_fields': list(data_context.get('characteristic', {}).keys())
                }
            )
            
            # Add calculated fields to figure_map using underscore variable names
            calculated_fields = data_context.get('calculated', {})
            for field_name, value in calculated_fields.items():
                if value is not None:
                    try:
                        figure_map[field_name] = float(value)
                    except (TypeError, ValueError) as calc_error:
                        missing.add(field_name)
                        log_counter_event(
                            'warning', 'data_quality',
                            'Calculated Field Conversion Failed in Counter Calculation',
                            f'Failed to convert calculated field {field_name} to float: {value}',
                            details={
                                'council_slug': council_slug,
                                'year_label': year_label,
                                'field_name': field_name,
                                'invalid_value': str(value),
                                'error_type': type(calc_error).__name__,
                                'reason': 'calculated_field_conversion_failed'
                            }
                        )
                else:
                    missing.add(field_name)
                    log_counter_event(
                        'info', 'data_quality',
                        'Calculated Field Has No Value in Counter Calculation',
                        f'Calculated field {field_name} returned None for {council.name} ({year_label})',
                        details={
                            'council_slug': council_slug,
                            'year_label': year_label,
                            'field_name': field_name,
                            'reason': 'calculated_field_returned_none'
                        }
                    )
                    
            # Also add characteristics that can be used in formulas
            characteristics = data_context.get('characteristic', {})
            for field_name, value in characteristics.items():
                if value is not None:
                    try:
                        # Only add characteristics that are numeric types
                        # First try to get the field to check its content_type
                        from council_finance.models import DataField
                        
                        # Convert field_name back to slug format to find the field
                        field_slug = field_name.replace('_', '-')
                        try:
                            # Use getattr to access cached field if available, otherwise query
                            if not hasattr(self, '_field_cache'):
                                self._field_cache = {}
                            
                            if field_slug not in self._field_cache:
                                self._field_cache[field_slug] = DataField.objects.get(slug=field_slug)
                            
                            field = self._field_cache[field_slug]
                            # Only include numeric content types in formula calculations
                            if field.content_type in ('monetary', 'integer'):
                                figure_map[field_name] = float(value)
                        except DataField.DoesNotExist:
                            # If we can't find the field, try to convert anyway as a fallback
                            # but silently skip if it fails
                            try:
                                figure_map[field_name] = float(value)
                            except (TypeError, ValueError):
                                # Silently skip non-numeric characteristics
                                pass
                    except (TypeError, ValueError):
                        # Non-numeric characteristics can't be used in formulas - skip silently
                        pass
                        
        except Exception as data_context_error:
            data_context_time = (timezone.now() - data_context_start).total_seconds()
            
            # Critical error logging - data context failure could cause Birmingham "no data" issue
            log_counter_event(
                'error', 'calculation',
                'Data Context Retrieval Failed in Counter Calculation',
                f'Failed to load data context for {council.name} ({year_label}): {str(data_context_error)}',
                details={
                    'council_slug': council_slug,
                    'year_label': year_label,
                    'error_type': type(data_context_error).__name__,
                    'data_context_time_seconds': data_context_time,
                    'impact': 'calculated_fields_unavailable_for_counters',
                    'reason': 'data_context_service_failed'
                }
            )
            
            # If data context fails, log but continue with just financial figures
            logger.warning(f"Failed to load calculated fields for {council.slug} {year.label}: {data_context_error}")
        
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
            
            # First, create a comprehensive mapping of all possible field name variations
            # This handles both regular fields and calculated fields that use underscores
            for field_slug, value in figure_map.items():
                # Add the field with its current name
                safe_vars[field_slug] = value
                
                # If the field has underscores, also map the hyphenated version
                if '_' in field_slug:
                    hyphenated_name = field_slug.replace('_', '-')
                    # Replace any hyphenated version in the formula with the underscore version
                    safe_formula = safe_formula.replace(hyphenated_name, field_slug)
                
                # If the field has hyphens, create underscore version
                if '-' in field_slug:
                    underscore_name = field_slug.replace('-', '_')
                    safe_vars[underscore_name] = value
                    safe_formula = safe_formula.replace(field_slug, underscore_name)
            

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
        successful_calculations = 0
        
        # Log final data summary before counter calculations
        log_counter_event(
            'info', 'calculation',
            'Starting Individual Counter Calculations',
            f'Beginning {len(counters)} counter calculations for {council.name} ({year_label})',
            details={
                'council_slug': council_slug,
                'year_label': year_label,
                'total_counters_to_calculate': len(counters),
                'available_fields_count': len(figure_map),
                'missing_fields_count': len(missing),
                'available_fields': list(figure_map.keys()),
                'missing_fields': list(missing)
            }
        )
        
        for counter in counters:
            counter_calc_start = timezone.now()
            
            try:
                total = eval_formula(counter.formula)
                counter_calc_time = (timezone.now() - counter_calc_start).total_seconds()
                successful_calculations += 1
                
                results[counter.slug] = {
                    "value": total,
                    "formatted": counter.format_value(total),
                }
                
                # Log successful counter calculation
                log_counter_event(
                    'info', 'calculation',
                    'Counter Calculation Successful',
                    f'Successfully calculated {counter.slug} for {council.name} ({year_label}): {total}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'counter_slug': counter.slug,
                        'counter_name': counter.name,
                        'formula': counter.formula,
                        'calculated_value': total,
                        'formatted_value': counter.format_value(total),
                        'calculation_time_seconds': counter_calc_time
                    }
                )
                
            except MissingDataError as missing_error:
                counter_calc_time = (timezone.now() - counter_calc_start).total_seconds()
                
                # CRITICAL: Log exactly what field is missing for Birmingham debugging
                log_counter_event(
                    'warning', 'data_quality',
                    'Counter Calculation Failed - Missing Data',
                    f'Counter {counter.slug} failed for {council.name} ({year_label}) - missing field: {str(missing_error)}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'counter_slug': counter.slug,
                        'counter_name': counter.name,
                        'formula': counter.formula,
                        'missing_field': str(missing_error),
                        'available_fields_in_formula_context': list(figure_map.keys()),
                        'all_missing_fields': list(missing),
                        'calculation_time_seconds': counter_calc_time,
                        'result': 'no_data_displayed'
                    }
                )
                
                # No figure exists for this counter. Indicate lack of data so
                # the UI can show an appropriate placeholder.
                results[counter.slug] = {
                    "value": None,
                    "formatted": "No data",
                    "error": None,
                }
                continue
                
            except ValueError as value_error:
                counter_calc_time = (timezone.now() - counter_calc_start).total_seconds()
                
                log_counter_event(
                    'error', 'calculation',
                    'Counter Calculation Failed - Formula Error',
                    f'Counter {counter.slug} formula error for {council.name} ({year_label}): {str(value_error)}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'counter_slug': counter.slug,
                        'counter_name': counter.name,
                        'formula': counter.formula,
                        'error_message': str(value_error),
                        'error_type': 'ValueError',
                        'calculation_time_seconds': counter_calc_time
                    }
                )
                
                results[counter.slug] = {"error": str(value_error)}
                continue
                
            except Exception as calc_error:
                counter_calc_time = (timezone.now() - counter_calc_start).total_seconds()
                
                log_counter_event(
                    'error', 'calculation',
                    'Counter Calculation Failed - Unexpected Error',
                    f'Counter {counter.slug} unexpected error for {council.name} ({year_label}): {str(calc_error)}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year_label,
                        'counter_slug': counter.slug,
                        'counter_name': counter.name,
                        'formula': counter.formula,
                        'error_message': str(calc_error),
                        'error_type': type(calc_error).__name__,
                        'calculation_time_seconds': counter_calc_time
                    }
                )
                
                results[counter.slug] = {"error": "calculation failed"}
                continue

        # Log final calculation summary
        total_calculation_time = (timezone.now() - calculation_start).total_seconds()
        
        log_counter_event(
            'info', 'calculation',
            'Counter Calculation Completed',
            f'Completed counter calculations for {council.name} ({year_label}): {successful_calculations}/{len(counters)} successful',
            details={
                'council_slug': council_slug,
                'year_label': year_label,
                'total_counters': len(counters),
                'successful_calculations': successful_calculations,
                'failed_calculations': len(counters) - successful_calculations,
                'total_calculation_time_seconds': total_calculation_time,
                'success_rate_percentage': (successful_calculations / len(counters) * 100) if counters else 0
            }
        )

        return results
