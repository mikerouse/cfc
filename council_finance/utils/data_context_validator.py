"""
Data Context Validation Utilities

Provides validation and consistency checking for data context structures
to prevent issues like the characteristics/characteristic key mismatch.
"""

import logging
from typing import Dict, Any, List, Set
from django.conf import settings

logger = logging.getLogger(__name__)

# Define the expected data context schema
EXPECTED_DATA_CONTEXT_SCHEMA = {
    'council_name': str,
    'council_slug': str,
    'year_label': (str, type(None)),
    'characteristic': dict,  # NOTE: singular, not plural
    'financial': dict,
    'calculated': dict,
}

# Expected keys that should be consistent across the application
CRITICAL_DATA_KEYS = {
    'characteristic',  # Council characteristics (non-year specific)
    'financial',       # Financial figures (year specific)
    'calculated',      # Calculated field values
}

class DataContextValidator:
    """Validates data context structures for consistency and completeness."""
    
    @staticmethod
    def validate_data_context(context: Dict[str, Any], source_function: str = "unknown") -> List[str]:
        """
        Validate that a data context follows the expected schema.
        
        Args:
            context: The data context dictionary to validate
            source_function: Name of function that generated this context (for logging)
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check for expected top-level keys
        for key, expected_type in EXPECTED_DATA_CONTEXT_SCHEMA.items():
            if key not in context:
                errors.append(f"Missing required key '{key}' in data context from {source_function}")
            elif not isinstance(context[key], expected_type):
                if not (isinstance(expected_type, tuple) and type(context[key]) in expected_type):
                    errors.append(f"Key '{key}' has wrong type {type(context[key])}, expected {expected_type}")
        
        # Check for common mistakes
        if 'characteristics' in context:
            errors.append(f"Found 'characteristics' (plural) key - should be 'characteristic' (singular)")
        
        # Validate data structure consistency
        if 'characteristic' in context and not isinstance(context['characteristic'], dict):
            errors.append(f"'characteristic' should be a dict, got {type(context['characteristic'])}")
            
        if 'financial' in context and not isinstance(context['financial'], dict):
            errors.append(f"'financial' should be a dict, got {type(context['financial'])}")
            
        # Log warnings for debugging
        if errors and settings.DEBUG:
            logger.warning(f"Data context validation failed for {source_function}: {errors}")
            
        return errors
    
    @staticmethod
    def get_all_field_keys(context: Dict[str, Any]) -> Set[str]:
        """
        Extract all available field keys from a data context.
        
        Args:
            context: The data context dictionary
            
        Returns:
            Set of all field names available for formulas
        """
        all_keys = set()
        
        # Add characteristics
        if 'characteristic' in context:
            all_keys.update(context['characteristic'].keys())
            
        # Add financial fields
        if 'financial' in context:
            all_keys.update(context['financial'].keys())
            
        # Add calculated fields
        if 'calculated' in context:
            all_keys.update(context['calculated'].keys())
            
        return all_keys
    
    @staticmethod
    def check_field_availability(context: Dict[str, Any], required_fields: List[str]) -> Dict[str, bool]:
        """
        Check which required fields are available in the data context.
        
        Args:
            context: The data context dictionary
            required_fields: List of field names needed for a formula
            
        Returns:
            Dict mapping field names to availability (True/False)
        """
        available_keys = DataContextValidator.get_all_field_keys(context)
        
        availability = {}
        for field in required_fields:
            # Check both hyphenated and underscore versions
            field_underscore = field.replace('-', '_')
            field_hyphenated = field.replace('_', '-')
            
            availability[field] = (
                field in available_keys or 
                field_underscore in available_keys or 
                field_hyphenated in available_keys
            )
            
        return availability


def validate_data_context_decorator(func):
    """
    Decorator to automatically validate data context return values.
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        if isinstance(result, dict):
            errors = DataContextValidator.validate_data_context(result, func.__name__)
            if errors and settings.DEBUG:
                logger.warning(f"Data context validation errors in {func.__name__}: {errors}")
                
        return result
    return wrapper


# Registry of functions that should return valid data contexts
DATA_CONTEXT_FUNCTIONS = {
    'get_data_context_for_council',
    'build_context_data',  # from FactoidEngine
    # Add other functions as needed
}

def log_data_context_usage(function_name: str, context: Dict[str, Any], 
                          requested_fields: List[str] = None):
    """
    Log data context usage for monitoring and debugging.
    
    Args:
        function_name: Name of function using the context
        context: The data context being used
        requested_fields: Fields that were requested (for formula evaluation)
    """
    if not settings.DEBUG:
        return
        
    available_fields = DataContextValidator.get_all_field_keys(context)
    
    log_data = {
        'function': function_name,
        'total_fields': len(available_fields),
        'characteristics_count': len(context.get('characteristic', {})),
        'financial_count': len(context.get('financial', {})),
        'calculated_count': len(context.get('calculated', {})),
    }
    
    if requested_fields:
        availability = DataContextValidator.check_field_availability(context, requested_fields)
        missing_fields = [f for f, avail in availability.items() if not avail]
        log_data['requested_fields'] = len(requested_fields)
        log_data['missing_fields'] = missing_fields
        
    logger.debug(f"Data context usage: {log_data}")
