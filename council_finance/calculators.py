"""
Formula evaluation engine for calculated fields and factoid templates.

This module provides safe evaluation of mathematical expressions used in
calculated DataField formulas and factoid template variables.
"""

import re
import logging
from typing import Dict, Any, Optional, Union
from decimal import Decimal, InvalidOperation
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


class FormulaEvaluationError(Exception):
    """Raised when formula evaluation fails."""
    pass


class FormulaEvaluator:
    """
    Safe formula evaluator for calculated fields.
    
    Supports basic mathematical operations and field references.
    """
    
    # Allowed operations for safe evaluation
    ALLOWED_OPS = {'+', '-', '*', '/', '(', ')'}
    
    def __init__(self):
        self.variables = {}
    
    def set_variables(self, variables: Dict[str, Union[int, float, Decimal]]):
        """Set variable values for formula evaluation."""
        self.variables = {}
        for key, value in variables.items():
            if value is not None:
                try:
                    # Convert to float for calculations
                    self.variables[key] = float(value)
                except (ValueError, TypeError, InvalidOperation):
                    logger.warning(f"Could not convert {key}={value} to number")
    
    def evaluate(self, formula: str) -> Optional[float]:
        """
        Safely evaluate a mathematical formula.
        
        Args:
            formula: Mathematical expression like "(total-debt)/population"
            
        Returns:
            Calculated result or None if evaluation fails
            
        Raises:
            FormulaEvaluationError: If formula contains unsafe operations
        """
        if not formula or not formula.strip():
            return None
            
        try:
            # Clean and validate the formula
            cleaned_formula = self._clean_formula(formula)
            
            # Replace field references with values
            resolved_formula = self._resolve_field_references(cleaned_formula)
            
            # Validate that only safe operations remain
            self._validate_safe_expression(resolved_formula)
            
            # Evaluate the expression
            result = eval(resolved_formula)
            
            # Ensure result is a number
            if isinstance(result, (int, float)) and not (
                result != result  # NaN check
                or result == float('inf') 
                or result == float('-inf')
            ):
                return float(result)
            else:
                logger.warning(f"Formula evaluation returned invalid result: {result}")
                return None
                
        except (ZeroDivisionError, ValueError, TypeError, SyntaxError) as e:
            logger.warning(f"Formula evaluation error for '{formula}': {e}")
            return None
        except FormulaEvaluationError as e:
            logger.error(f"Unsafe formula detected: '{formula}': {e}")
            return None
    
    def _clean_formula(self, formula: str) -> str:
        """Clean and normalize the formula string."""
        # Remove whitespace  
        cleaned = re.sub(r'\s+', '', formula)
        
        # Convert field references to lowercase with underscores
        # e.g., "total-debt" -> "total_debt"
        # This should match our variable naming convention
        def normalize_field_name(match):
            field_name = match.group(1)
            return field_name.replace('-', '_').lower()
        
        cleaned = re.sub(r'([a-zA-Z][a-zA-Z0-9\-_]*)', normalize_field_name, cleaned)
        
        return cleaned
    
    def _resolve_field_references(self, formula: str) -> str:
        """Replace field references with actual values."""
        # Find all field references (letters followed by letters/numbers/underscores)
        field_pattern = r'([a-zA-Z][a-zA-Z0-9_]*)'
        
        def replace_field(match):
            field_name = match.group(1)
            if field_name in self.variables:
                return str(self.variables[field_name])
            else:
                raise FormulaEvaluationError(f"Unknown field reference: {field_name}")
        
        return re.sub(field_pattern, replace_field, formula)
    
    def _validate_safe_expression(self, expression: str) -> None:
        """Validate that expression contains only safe operations."""
        # Check for any non-numeric, non-operator characters
        safe_pattern = r'^[0-9+\-*/().\s]+$'
        if not re.match(safe_pattern, expression):
            raise FormulaEvaluationError(f"Expression contains unsafe characters: {expression}")
        
        # Additional safety checks could be added here
        # e.g., preventing overly complex expressions, recursion limits, etc.


def _resolve_calculated_field_dependencies(calculated_fields, evaluator, variables):
    """
    Resolve calculated field dependencies using topological sorting.
    
    This ensures that fields are calculated in the correct order,
    with dependencies calculated before fields that depend on them.
    
    Args:
        calculated_fields: QuerySet of calculated DataField objects
        evaluator: FormulaEvaluator instance
        variables: Dict of existing variables
    
    Returns:
        Dict mapping field objects to their calculated results
    """
    from collections import defaultdict, deque
    import re
    
    # Create dependency graph
    dependencies = defaultdict(set)
    dependents = defaultdict(set)
    field_by_name = {}
    
    # Index fields by their variable names (both slug and underscore versions)
    for field in calculated_fields:
        field_by_name[field.slug] = field
        field_by_name[field.slug.replace('-', '_')] = field
        field_by_name[field.variable_name] = field
    
    # Build dependency graph
    for field in calculated_fields:
        if not field.formula:
            continue
            
        # Extract field references from formula
        field_refs = _extract_field_references(field.formula)
        
        for ref in field_refs:
            # Check if this reference is to another calculated field
            ref_field = field_by_name.get(ref) or field_by_name.get(ref.replace('_', '-')) or field_by_name.get(ref.replace('-', '_'))
            
            if ref_field and ref_field in calculated_fields:
                # This field depends on ref_field
                dependencies[field].add(ref_field)
                dependents[ref_field].add(field)
    
    # Topological sort using Kahn's algorithm
    resolved_fields = {}
    queue = deque()
    in_degree = defaultdict(int)
    
    # Calculate in-degrees
    for field in calculated_fields:
        in_degree[field] = len(dependencies[field])
        if in_degree[field] == 0:
            queue.append(field)
    
    # Process fields in dependency order
    while queue:
        current_field = queue.popleft()
        
        # Calculate this field
        if current_field.formula:
            try:
                result = evaluator.evaluate(current_field.formula)
                resolved_fields[current_field] = result
                
                if result is not None:
                    # Add result to variables for subsequent calculations
                    field_name = current_field.slug.replace('-', '_')
                    variables[field_name] = result
                    evaluator.set_variables(variables)
                    
                    logger.debug(f"Calculated {current_field.slug} = {result}")
                    
            except Exception as e:
                logger.warning(f"Failed to calculate {current_field.slug}: {e}")
                resolved_fields[current_field] = None
        
        # Update in-degrees for dependent fields
        for dependent in dependents[current_field]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # Check for circular dependencies
    unresolved = [field for field in calculated_fields if field not in resolved_fields]
    if unresolved:
        logger.warning(f"Circular dependencies detected in calculated fields: {[f.slug for f in unresolved]}")
        
        # Try to calculate unresolved fields anyway (they might not actually be circular)
        for field in unresolved:
            if field.formula:
                try:
                    result = evaluator.evaluate(field.formula)
                    resolved_fields[field] = result
                    
                    if result is not None:
                        field_name = field.slug.replace('-', '_')
                        variables[field_name] = result
                        evaluator.set_variables(variables)
                        
                except Exception as e:
                    logger.warning(f"Failed to calculate potentially circular field {field.slug}: {e}")
                    resolved_fields[field] = None
    
    return resolved_fields


def _extract_field_references(formula):
    """
    Extract field references from a formula string.
    
    Returns list of field names referenced in the formula.
    """
    # Pattern to match field names (letters, numbers, hyphens, underscores)
    pattern = r'\b([a-zA-Z][a-zA-Z0-9_-]*)\b'
    
    # Find all potential field references
    matches = re.findall(pattern, formula)
    
    # Filter out numeric values and operators
    field_refs = []
    for match in matches:
        # Skip if it's a number or common operator keyword
        if not match.replace('.', '').replace('-', '').isdigit() and match not in ['and', 'or', 'not', 'in', 'is']:
            field_refs.append(match)
    
    return field_refs


def get_data_context_for_council(council, year=None, counter_slug=None):
    """
    Build comprehensive data context for a council including characteristics,
    financial figures, and calculated values.
    
    Args:
        council: Council instance
        year: FinancialYear instance (optional)
        counter_slug: Counter slug for additional context (optional)
        
    Returns:
        Dictionary with all available data for template rendering
    """
    from council_finance.models import (
        DataField, CouncilCharacteristic, FinancialFigure
    )
    from council_finance.utils.data_context_validator import validate_data_context_decorator
    
    context = {
        'council_name': council.name,
        'council_slug': council.slug,
        'year_label': year.label if year else None,
    }
    
    # Build variable lookup for formula evaluation
    variables = {}
    
    # 1. Add characteristics
    characteristics = CouncilCharacteristic.objects.filter(council=council)
    context['characteristic'] = {}  # Note: singular form for consistency
    
    for char in characteristics:
        field_name = char.field.slug.replace('-', '_')
        context['characteristic'][field_name] = char.value
        variables[field_name] = char.value
    
    # 2. Add financial figures for the specified year
    if year:
        financial_figures = FinancialFigure.objects.filter(
            council=council, year=year
        ).select_related('field')
        
        context['financial'] = {}
        for figure in financial_figures:
            field_name = figure.field.slug.replace('-', '_')
            context['financial'][field_name] = figure.value
            variables[field_name] = figure.value
    else:
        context['financial'] = {}
    
    # 3. Add ALL counter values as potential variables for calculated fields
    try:
        from council_finance.agents.counter_agent import CounterAgent
        from council_finance.models import FinancialYear
        
        agent = CounterAgent()
        
        # Get year label - use provided year, or find a default
        year_label = None
        if year:
            year_label = year.label
        else:
            # Try to find a year with actual data (prefer 2024/25, 2023/24, etc.)
            for test_year in ['2024/25', '2023/24', '2022/23']:
                if FinancialYear.objects.filter(label=test_year).exists():
                    year_label = test_year
                    break
            
            # Fallback to any year if none of the preferred ones exist
            if not year_label:
                default_year = FinancialYear.objects.first()
                if default_year:
                    year_label = default_year.label
        
        counter_results = {}
        if year_label:
            counter_results = agent.run(
                council_slug=council.slug,
                year_label=year_label
            )
        
        # Add all counter results to variables for formula evaluation
        for slug, result in counter_results.items():
            if isinstance(result, dict):
                # Try 'raw' first, then 'value'
                if 'raw' in result and result['raw'] is not None:
                    variables[slug.replace('-', '_')] = result['raw']
                elif 'value' in result and result['value'] is not None:
                    variables[slug.replace('-', '_')] = result['value']
            elif isinstance(result, (int, float)):
                variables[slug.replace('-', '_')] = result
        
        # If a specific counter_slug was requested, add its formatted output to context
        if counter_slug and counter_slug in counter_results:
            result = counter_results[counter_slug]
            if isinstance(result, dict):
                context.update(result)  # Add value, formatted, etc.
            else:
                context['value'] = result
                
    except Exception as e:
        logger.warning(f"Failed to get counter values: {e}")
    
    # 4. Calculate and add all calculated fields with dependency resolution
    calculated_fields = DataField.objects.filter(category='calculated')
    context['calculated'] = {}
    
    evaluator = FormulaEvaluator()
    evaluator.set_variables(variables)
    
    # Resolve calculated fields in dependency order
    resolved_fields = _resolve_calculated_field_dependencies(calculated_fields, evaluator, variables)
    
    for field, result in resolved_fields.items():
        if result is not None:
            field_name = field.slug.replace('-', '_')
            context['calculated'][field_name] = result
    
    return context


def test_formula_evaluator():
    """Test function for the formula evaluator."""
    evaluator = FormulaEvaluator()
    
    # Test basic operations
    test_cases = [
        ("10 + 5", {}, 15.0),
        ("(total_debt) / population", {"total_debt": 1000000, "population": 50000}, 20.0),
        ("total_debt * 1.05", {"total_debt": 100}, 105.0),
        ("(current_liabilities + long_term_liabilities)", 
         {"current_liabilities": 500, "long_term_liabilities": 1500}, 2000.0),
    ]
    
    for formula, variables, expected in test_cases:
        evaluator.set_variables(variables)
        result = evaluator.evaluate(formula)
        print(f"Formula: {formula}")
        print(f"Variables: {variables}")  
        print(f"Result: {result}, Expected: {expected}")
        print(f"✓ Pass" if abs(result - expected) < 0.001 else "✗ Fail")
        print()


if __name__ == "__main__":
    test_formula_evaluator()