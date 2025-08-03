"""
Centralized field name resolution utility for Council Finance Counters.

This module provides consistent field name conversion between different
formats used throughout the application:
- Database slugs: 'interest-paid', 'total-debt' (hyphenated) 
- Variable names: 'interest_paid', 'total_debt' (underscored)
- Formula references: Mixed usage, needs normalization

Usage:
    from council_finance.utils.field_resolver import FieldResolver
    
    resolver = FieldResolver()
    variable_name = resolver.to_variable_name('interest-paid')  # 'interest_paid'
    slug_name = resolver.to_slug_name('interest_paid')  # 'interest-paid'
    
    # Validate field exists
    if resolver.field_exists('interest-paid'):
        # Safe to use
        pass
"""

import re
import logging
from typing import Dict, List, Set, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class FieldResolver:
    """
    Centralized field name resolution and validation utility.
    
    Handles conversion between slug format (hyphenated) and variable format 
    (underscored) used throughout the application. Provides caching and 
    validation to prevent missing field reference errors.
    """
    
    def __init__(self):
        """Initialize resolver with caching."""
        self._field_cache = None
        self._cache_key = 'field_resolver_available_fields'
        self._cache_timeout = 300  # 5 minutes
    
    def get_available_fields(self) -> Set[str]:
        """
        Get set of all available field slugs from the database.
        
        Results are cached for performance.
        
        Returns:
            Set of field slugs that exist in the database
        """
        if self._field_cache is None:
            # Try cache first
            cached_fields = cache.get(self._cache_key)
            if cached_fields is not None:
                self._field_cache = cached_fields
            else:
                # Query database
                try:
                    from council_finance.models import DataField
                    self._field_cache = set(
                        DataField.objects.values_list('slug', flat=True)
                    )
                    # Cache the result
                    cache.set(self._cache_key, self._field_cache, self._cache_timeout)
                    logger.debug(f"Loaded {len(self._field_cache)} available fields")
                except Exception as e:
                    logger.warning(f"Failed to load available fields: {e}")
                    self._field_cache = set()
        
        return self._field_cache
    
    def clear_cache(self):
        """Clear the field cache to force reload on next access."""
        self._field_cache = None
        cache.delete(self._cache_key)
    
    def to_variable_name(self, slug: str) -> str:
        """
        Convert field slug to variable name format.
        
        Args:
            slug: Field slug like 'interest-paid' or 'total-debt'
            
        Returns:
            Variable name like 'interest_paid' or 'total_debt'
        """
        return slug.replace('-', '_')
    
    def to_slug_name(self, variable: str) -> str:
        """
        Convert variable name to field slug format.
        
        Args:
            variable: Variable name like 'interest_paid' or 'total_debt'
            
        Returns:
            Field slug like 'interest-paid' or 'total-debt'
        """
        return variable.replace('_', '-')
    
    def field_exists(self, field_name: str) -> bool:
        """
        Check if a field exists in the database.
        
        Accepts either slug format or variable format.
        
        Args:
            field_name: Field name in either format
            
        Returns:
            True if field exists, False otherwise
        """
        available_fields = self.get_available_fields()
        
        # Check both formats
        slug_format = self.to_slug_name(field_name)
        variable_format = self.to_variable_name(field_name)
        
        return (
            field_name in available_fields or
            slug_format in available_fields or
            variable_format in available_fields
        )
    
    def resolve_field_name(self, field_name: str) -> Optional[str]:
        """
        Resolve a field name to its canonical slug format.
        
        Args:
            field_name: Field name in any format
            
        Returns:
            Canonical slug format if field exists, None otherwise
        """
        available_fields = self.get_available_fields()
        
        # Try exact match first
        if field_name in available_fields:
            return field_name
        
        # Try slug format
        slug_format = self.to_slug_name(field_name)
        if slug_format in available_fields:
            return slug_format
        
        # Try variable format converted to slug
        variable_format = self.to_variable_name(field_name)
        slug_from_variable = self.to_slug_name(variable_format)
        if slug_from_variable in available_fields:
            return slug_from_variable
        
        return None
    
    def normalize_formula(self, formula: str) -> str:
        """
        Normalize all field references in a formula to variable format.
        
        Converts formulas like 'interest-paid / population' to 
        'interest_paid / population' for consistent evaluation.
        
        Args:
            formula: Mathematical formula with field references
            
        Returns:
            Formula with all field references in variable format
        """
        if not formula or not formula.strip():
            return formula
        
        # Find all potential field references
        field_pattern = r'\b([a-zA-Z][a-zA-Z0-9\-_]*)\b'
        
        def replace_field_reference(match):
            field_ref = match.group(1)
            
            # Skip if it's obviously not a field (like numbers)
            if field_ref.replace('.', '').replace('-', '').isdigit():
                return field_ref
            
            # Skip common non-field words
            if field_ref.lower() in ['and', 'or', 'not', 'in', 'is']:
                return field_ref
            
            # Convert to variable format
            return self.to_variable_name(field_ref)
        
        return re.sub(field_pattern, replace_field_reference, formula)
    
    def validate_formula_references(self, formula: str) -> List[str]:
        """
        Validate all field references in a formula.
        
        Args:
            formula: Mathematical formula to validate
            
        Returns:
            List of missing field references (empty if all valid)
        """
        if not formula or not formula.strip():
            return []
        
        # Extract field references
        field_pattern = r'\b([a-zA-Z][a-zA-Z0-9\-_]*)\b'
        references = re.findall(field_pattern, formula)
        
        missing_fields = []
        for ref in references:
            # Skip obvious non-fields
            if (ref.replace('.', '').replace('-', '').isdigit() or
                ref.lower() in ['and', 'or', 'not', 'in', 'is']):
                continue
            
            if not self.field_exists(ref):
                missing_fields.append(ref)
        
        return missing_fields
    
    def get_existing_fields_from_list(self, field_list: List[str]) -> List[str]:
        """
        Filter a list of field names to only include existing fields.
        
        Useful for cleaning up hardcoded field lists that may contain
        planned but not yet implemented fields.
        
        Args:
            field_list: List of field names to filter
            
        Returns:
            List containing only existing fields
        """
        existing_fields = []
        available_fields = self.get_available_fields()
        
        for field_name in field_list:
            canonical_name = self.resolve_field_name(field_name)
            if canonical_name:
                existing_fields.append(canonical_name)
            else:
                logger.debug(f"Field '{field_name}' not found in database")
        
        return existing_fields


# Global resolver instance for convenience
_resolver_instance = None

def get_field_resolver() -> FieldResolver:
    """
    Get a shared FieldResolver instance.
    
    Returns:
        Shared FieldResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = FieldResolver()
    return _resolver_instance


# Convenience functions
def to_variable_name(slug: str) -> str:
    """Convert field slug to variable name format."""
    return get_field_resolver().to_variable_name(slug)


def to_slug_name(variable: str) -> str:
    """Convert variable name to field slug format.""" 
    return get_field_resolver().to_slug_name(variable)


def field_exists(field_name: str) -> bool:
    """Check if a field exists in the database."""
    return get_field_resolver().field_exists(field_name)


def normalize_formula(formula: str) -> str:
    """Normalize field references in formula to variable format."""
    return get_field_resolver().normalize_formula(formula)


def validate_formula_references(formula: str) -> List[str]:
    """Validate all field references in a formula."""
    return get_field_resolver().validate_formula_references(formula)