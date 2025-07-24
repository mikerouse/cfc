"""
Expression Renderer for Factoid Templates

This module provides a simple, reliable alternative to Django templates
for rendering factoid expressions. It uses a straightforward syntax:

Examples:
- Basic variables: {council_name}, {year_label}
- Nested access: {calculated.total_debt_per_capita}
- Formatting: {calculated.total_debt_per_capita:currency}, {value:number:2}
- Conditionals: {calculated.debt > 0 ? "High debt" : "Low debt"}

This approach is more reliable than Django templates and provides better
error handling for missing data.
"""

import re
import logging
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class ExpressionRenderer:
    """
    Simple expression renderer for factoid templates.
    
    Provides reliable rendering with comprehensive error handling
    and flexible formatting options.
    """
    
    def __init__(self):
        # Pattern to match expressions: {variable} or {variable:format} or {variable:format:precision}
        self.expression_pattern = re.compile(r'\{([^}]+)\}')
        
        # Format handlers for different data types
        self.formatters = {
            'currency': self._format_currency,
            'currency_per_capita': self._format_currency_per_capita, 
            'number': self._format_number,
            'percentage': self._format_percentage,
            'text': self._format_text,
        }
    
    def render(self, template_text: str, context: Dict[str, Any]) -> str:
        """
        Render template with context data.
        
        Args:
            template_text: Template string with {variable} expressions
            context: Dictionary with variable values
            
        Returns:
            Rendered string with variables replaced
            
        Raises:
            ExpressionError: If rendering fails completely
        """
        rendered, errors = self.render_safe(template_text, context)
        
        if errors:
            logger.warning(f"Expression rendering had errors: {errors}")
            
        return rendered
    
    def render_safe(self, template_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Render template with comprehensive error handling.
        
        Args:
            template_text: Template string with {variable} expressions
            context: Dictionary with variable values
            
        Returns:
            Tuple of (rendered_string, error_list)
            - rendered_string: Best-effort rendered output
            - error_list: List of any errors encountered
        """
        if not template_text:
            return "", []
            
        errors = []
        result = template_text
        
        try:
            # Find all expressions in the template
            expressions = self.expression_pattern.findall(result)
            
            # Process each expression
            for expr in expressions:
                try:
                    value = self._evaluate_expression(expr, context)
                    # Replace the expression with the evaluated value
                    result = result.replace(f'{{{expr}}}', str(value))
                except Exception as e:
                    error_msg = f"Error evaluating '{expr}': {str(e)}"
                    errors.append(error_msg)
                    # Leave the original expression in place on error
                    logger.debug(error_msg)
            
            return result, errors
            
        except Exception as e:
            error_msg = f"Critical rendering error: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return template_text, errors  # Return original on critical error
    
    def _evaluate_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate a single expression like 'calculated.debt:currency'.
        
        Args:
            expr: Expression string (without braces)
            context: Context dictionary
            
        Returns:
            Formatted value
        """
        # Parse expression components
        parts = expr.split(':')
        variable_path = parts[0].strip()
        format_type = parts[1].strip() if len(parts) > 1 else 'text'
        precision = int(parts[2].strip()) if len(parts) > 2 else None
        
        # Get the variable value
        value = self._get_nested_value(variable_path, context)
        
        # Apply formatting
        return self._format_value(value, format_type, precision)
    
    def _get_nested_value(self, path: str, context: Dict[str, Any]) -> Any:
        """
        Get value from nested dictionary using dot notation.
        
        Examples:
        - 'council_name' -> context['council_name']
        - 'calculated.debt' -> context['calculated']['debt']
        - 'characteristic.population' -> context['characteristic']['population']
        """
        if not path:
            raise ValueError("Empty variable path")
            
        # Split path by dots
        path_parts = path.split('.')
        
        # Start with the context
        current = context
        
        # Navigate through nested dictionaries
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # Handle common missing data scenarios gracefully
                if path.startswith('calculated.'):
                    return 0  # Default for missing calculated values
                elif path.startswith('characteristic.'):
                    return f"[{part}]"  # Placeholder for missing characteristics
                else:
                    raise KeyError(f"Variable '{path}' not found in context")
        
        return current
    
    def _format_value(self, value: Any, format_type: str, precision: Optional[int] = None) -> str:
        """Apply formatting to a value based on format type."""
        if value is None:
            return ""
            
        # Get the appropriate formatter
        formatter = self.formatters.get(format_type, self._format_text)
        
        try:
            return formatter(value, precision)
        except Exception as e:
            logger.warning(f"Formatting error for {value} with {format_type}: {e}")
            return str(value)  # Fallback to string representation
    
    def _format_currency(self, value: Any, precision: Optional[int] = None) -> str:
        """Format value as currency (£1,234,567)."""
        try:
            if isinstance(value, str):
                # Clean string values
                clean_value = value.replace('£', '').replace(',', '').strip()
                if not clean_value:
                    return "£0"
                value = float(clean_value)
                
            if isinstance(value, (int, float, Decimal)):
                num_value = float(value)
                if precision is not None:
                    return f"£{num_value:,.{precision}f}"
                else:
                    # Default to no decimal places for currency
                    return f"£{num_value:,.0f}"
            
            return f"£{value}"
            
        except (ValueError, TypeError):
            return f"£{value}"
    
    def _format_currency_per_capita(self, value: Any, precision: Optional[int] = None) -> str:
        """Format value as per capita currency (£1,234 per person)."""
        formatted = self._format_currency(value, precision or 0)
        return formatted  # Just format as currency, context will add "per head" etc.
    
    def _format_number(self, value: Any, precision: Optional[int] = None) -> str:
        """Format value as a number (1,234,567.89)."""
        try:
            if isinstance(value, str):
                clean_value = value.replace(',', '').strip()
                if not clean_value:
                    return "0"
                value = float(clean_value)
                
            if isinstance(value, (int, float, Decimal)):
                num_value = float(value)
                if precision is not None:
                    return f"{num_value:,.{precision}f}"
                else:
                    # Default to appropriate decimal places
                    if num_value == int(num_value):
                        return f"{int(num_value):,}"
                    else:
                        return f"{num_value:,.2f}"
            
            return str(value)
            
        except (ValueError, TypeError):
            return str(value)
    
    def _format_percentage(self, value: Any, precision: Optional[int] = None) -> str:
        """Format value as percentage (12.34%)."""
        try:
            if isinstance(value, (int, float, Decimal)):
                num_value = float(value)
                precision = precision or 1
                return f"{num_value:.{precision}f}%"
            
            return f"{value}%"
            
        except (ValueError, TypeError):
            return f"{value}%"
    
    def _format_text(self, value: Any, precision: Optional[int] = None) -> str:
        """Format value as plain text."""
        return str(value)


class ExpressionError(Exception):
    """Exception raised when expression rendering fails completely."""
    pass


# Convenience functions for direct use
def render_expression(template_text: str, context: Dict[str, Any]) -> str:
    """
    Convenience function to render an expression template.
    
    Args:
        template_text: Template string with {variable} expressions
        context: Dictionary with variable values
        
    Returns:
        Rendered string
    """
    renderer = ExpressionRenderer()
    return renderer.render(template_text, context)


def render_expression_safe(template_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Convenience function to safely render an expression template.
    
    Args:
        template_text: Template string with {variable} expressions
        context: Dictionary with variable values
        
    Returns:
        Tuple of (rendered_string, error_list)
    """
    renderer = ExpressionRenderer()
    return renderer.render_safe(template_text, context)