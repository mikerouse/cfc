"""
Field Naming Convention Utilities

Provides standardized field name handling and validation to prevent
inconsistencies between hyphenated slugs and underscore variable names.
"""

import re
from typing import Set, Dict, List, Tuple
from django.core.exceptions import ValidationError

class FieldNamingValidator:
    """Validates and standardizes field naming conventions."""
    
    # Reserved words that shouldn't be used as field names
    RESERVED_WORDS = {
        'if', 'else', 'elif', 'while', 'for', 'def', 'class', 'import', 'from',
        'return', 'yield', 'try', 'except', 'finally', 'with', 'as', 'pass',
        'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'lambda', 'global',
        'nonlocal', 'assert', 'del', 'raise', 'True', 'False', 'None'
    }
    
    @staticmethod
    def validate_field_slug(slug: str) -> List[str]:
        """
        Validate a field slug follows naming conventions.
        
        Args:
            slug: The field slug to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not slug:
            errors.append("Field slug cannot be empty")
            return errors
            
        # Check basic format
        if not re.match(r'^[a-z][a-z0-9-]*[a-z0-9]$', slug) and slug != slug.lower():
            errors.append("Field slug must be lowercase, start with a letter, and contain only letters, numbers, and hyphens")
            
        # Check for reserved words
        slug_parts = slug.split('-')
        for part in slug_parts:
            if part in FieldNamingValidator.RESERVED_WORDS:
                errors.append(f"Field slug contains reserved word: '{part}'")
                
        # Check for problematic patterns
        if slug.startswith('-') or slug.endswith('-'):
            errors.append("Field slug cannot start or end with hyphen")
            
        if '--' in slug:
            errors.append("Field slug cannot contain consecutive hyphens")
            
        # Check length
        if len(slug) > 100:
            errors.append("Field slug is too long (max 100 characters)")
            
        if len(slug) < 2:
            errors.append("Field slug is too short (min 2 characters)")
            
        return errors
    
    @staticmethod
    def slug_to_variable_name(slug: str) -> str:
        """
        Convert a field slug to a valid Python variable name.
        
        Args:
            slug: The field slug (e.g., 'non-ring-fenced-grants')
            
        Returns:
            Valid Python variable name (e.g., 'non_ring_fenced_grants')
        """
        if not slug:
            return ''
            
        # Replace hyphens with underscores
        variable_name = slug.replace('-', '_')
        
        # Ensure it starts with a letter or underscore
        if variable_name and variable_name[0].isdigit():
            variable_name = f'field_{variable_name}'
            
        return variable_name
    
    @staticmethod
    def variable_name_to_slug(variable_name: str) -> str:
        """
        Convert a Python variable name back to a field slug.
        
        Args:
            variable_name: The variable name (e.g., 'non_ring_fenced_grants')
            
        Returns:
            Field slug (e.g., 'non-ring-fenced-grants')
        """
        if not variable_name:
            return ''
            
        # Remove 'field_' prefix if it was added for numeric starts
        if variable_name.startswith('field_') and variable_name[6:7].isdigit():
            variable_name = variable_name[6:]
            
        # Replace underscores with hyphens
        return variable_name.replace('_', '-')
    
    @staticmethod
    def normalize_field_reference(field_ref: str) -> Tuple[str, str]:
        """
        Normalize a field reference to both slug and variable name formats.
        
        Args:
            field_ref: Field reference in either format
            
        Returns:
            Tuple of (slug, variable_name)
        """
        if not field_ref:
            return '', ''
            
        # Determine which format we have
        if '_' in field_ref and '-' not in field_ref:
            # Likely a variable name
            variable_name = field_ref
            slug = FieldNamingValidator.variable_name_to_slug(field_ref)
        elif '-' in field_ref and '_' not in field_ref:
            # Likely a slug
            slug = field_ref
            variable_name = FieldNamingValidator.slug_to_variable_name(field_ref)
        else:
            # Ambiguous or mixed - treat as slug by default
            slug = field_ref
            variable_name = FieldNamingValidator.slug_to_variable_name(field_ref)
            
        return slug, variable_name
    
    @staticmethod
    def find_field_matches(field_ref: str, available_fields: Dict[str, any]) -> List[str]:
        """
        Find all possible matches for a field reference in available fields.
        
        Args:
            field_ref: The field reference to search for
            available_fields: Dict of available field names/slugs to field objects
            
        Returns:
            List of matching field identifiers
        """
        matches = []
        slug, variable_name = FieldNamingValidator.normalize_field_reference(field_ref)
        
        # Check exact matches
        if field_ref in available_fields:
            matches.append(field_ref)
            
        # Check slug format
        if slug != field_ref and slug in available_fields:
            matches.append(slug)
            
        # Check variable name format
        if variable_name != field_ref and variable_name in available_fields:
            matches.append(variable_name)
            
        # Check if any field objects have matching properties
        for field_id, field_obj in available_fields.items():
            if hasattr(field_obj, 'slug') and field_obj.slug in (field_ref, slug):
                if field_id not in matches:
                    matches.append(field_id)
                    
            if hasattr(field_obj, 'variable_name') and field_obj.variable_name in (field_ref, variable_name):
                if field_id not in matches:
                    matches.append(field_id)
                    
        return matches


class FormulaFieldExtractor:
    """Extracts field references from formulas with proper naming convention handling."""
    
    @staticmethod
    def extract_field_references(formula: str) -> Set[str]:
        """
        Extract all field references from a formula string.
        
        Args:
            formula: The formula string to parse
            
        Returns:
            Set of field references found in the formula
        """
        if not formula:
            return set()
            
        # Pattern to match field names (letters, numbers, hyphens, underscores)
        # Must start with letter, can contain numbers, hyphens, underscores
        pattern = r'\b[a-zA-Z][a-zA-Z0-9_-]*\b'
        
        # Find all potential field references
        potential_refs = re.findall(pattern, formula)
        
        # Filter out operators, functions, and numbers
        operators = {
            'and', 'or', 'not', 'in', 'is', 'if', 'else', 'elif',
            'true', 'false', 'none', 'null',
            'abs', 'min', 'max', 'sum', 'avg', 'count',
            'round', 'floor', 'ceil', 'sqrt', 'pow',
        }
        
        field_refs = set()
        for ref in potential_refs:
            ref_lower = ref.lower()
            
            # Skip operators and built-in functions
            if ref_lower in operators:
                continue
                
            # Skip if it looks like a number
            if ref.replace('.', '').replace('-', '').isdigit():
                continue
                
            # Skip very short references (likely operators)
            if len(ref) < 2:
                continue
                
            field_refs.add(ref)
            
        return field_refs
    
    @staticmethod
    def validate_formula_fields(formula: str, available_fields: Dict[str, any]) -> Dict[str, List[str]]:
        """
        Validate that all field references in a formula are available.
        
        Args:
            formula: The formula to validate
            available_fields: Dict of available field names to field objects
            
        Returns:
            Dict with 'valid' and 'invalid' lists of field references
        """
        field_refs = FormulaFieldExtractor.extract_field_references(formula)
        
        valid_refs = []
        invalid_refs = []
        
        for ref in field_refs:
            matches = FieldNamingValidator.find_field_matches(ref, available_fields)
            if matches:
                valid_refs.append(ref)
            else:
                invalid_refs.append(ref)
                
        return {
            'valid': valid_refs,
            'invalid': invalid_refs,
            'all_references': list(field_refs)
        }
