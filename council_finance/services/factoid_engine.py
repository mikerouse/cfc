"""
Real-time Factoid Engine

This service provides real-time factoid computation and cache management.
It automatically responds to data field changes and keeps factoids up-to-date.
"""
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.db.models import Q, F
from decimal import Decimal
import logging
import asyncio
from typing import List, Dict, Any, Optional

from ..models.factoid import (
    FactoidTemplate, 
    FactoidInstance, 
    FactoidFieldDependency,
)
from ..models.field import DataField
from ..models.council import Council, FinancialYear
from ..models.counter import CounterDefinition
from ..models.new_data_model import CouncilCharacteristic, FinancialFigure

logger = logging.getLogger(__name__)


class FactoidEngine:
    """
    Real-time factoid computation and management engine
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes default cache
        self.batch_size = 50
    
    def get_field_value(self, field_name: str, council: Council, year: FinancialYear, counter: CounterDefinition = None) -> Any:
        """
        Get the actual value for a field name from the data models
        """
        # Define virtual/computed fields that don't exist in DataField
        virtual_fields = ['council_name', 'year_label', 'council_slug', 'council_type']
        
        try:
            # Handle virtual fields first to avoid database lookup
            if field_name in virtual_fields:
                return self._get_calculated_value(field_name, council, year, counter)
            
            # Try to get the field definition for database fields
            data_field = DataField.from_variable_name(field_name)
            
            # Handle different field categories
            if data_field.category == 'characteristic':
                return self._get_characteristic_value(field_name, council, year)
            elif data_field.category in ['financial', 'income', 'balance_sheet', 'spending']:
                # All these categories are stored in FinancialFigure model
                return self._get_financial_value(field_name, council, year)
            elif data_field.category == 'calculated':
                return self._get_calculated_value(field_name, council, year, counter)
            else:
                logger.warning(f"Unknown field category: {data_field.category}")
                return None
                
        except DataField.DoesNotExist:
            # If field doesn't exist in database, try calculated values
            return self._get_calculated_value(field_name, council, year, counter)
        except Exception as e:
            logger.error(f"Error getting field value for {field_name}: {e}")
            return None
    
    def _get_characteristic_value(self, field_name: str, council: Council, year: FinancialYear) -> Any:
        """Get value from council characteristics"""
        try:
            slug = DataField.from_variable_name(field_name).slug
            characteristic = CouncilCharacteristic.objects.filter(
                council=council,
                field__slug=slug
            ).first()
            
            if characteristic:
                return characteristic.value
            
            # Fallback to council direct attributes
            if hasattr(council, field_name):
                return getattr(council, field_name)
                
            return None
        except Exception as e:
            logger.error(f"Error getting characteristic {field_name}: {e}")
            return None
    
    def _get_financial_value(self, field_name: str, council: Council, year: FinancialYear) -> Any:
        """Get value from financial figures"""
        try:
            slug = DataField.from_variable_name(field_name).slug
            figure = FinancialFigure.objects.filter(
                council=council,
                field__slug=slug,
                year=year
            ).first()
            
            return figure.value if figure else None
        except Exception as e:
            logger.error(f"Error getting financial figure {field_name}: {e}")
            return None
    
    def _get_calculated_value(self, field_name: str, council: Council, year: FinancialYear, counter: CounterDefinition = None) -> Any:
        """Get calculated/computed values"""
        try:
            # Handle common calculated fields
            if field_name == 'council_name':
                return council.name
            elif field_name == 'year_label':
                return str(year.label)
            elif field_name == 'council_slug':
                return council.slug
            elif field_name == 'council_type':
                return council.council_type.name if council.council_type else 'Unknown'
            elif field_name.endswith('_per_capita'):
                # Calculate per capita values - need to map field names correctly
                base_field = field_name.replace('_per_capita', '')
                
                # Handle special mappings
                field_mappings = {
                    'interest_payments': 'interest_paid',
                    'government_grants': 'government_grants_non_strings',
                    # Add more mappings as needed
                }
                
                mapped_field = field_mappings.get(base_field, base_field)
                base_value = self.get_field_value(mapped_field, council, year, counter)
                population = self._get_population(council, year)
                
                if base_value and population:
                    return Decimal(str(base_value)) / Decimal(str(population))
            elif field_name.endswith('_change_percent'):
                # Calculate year-over-year percentage change
                base_field = field_name.replace('_change_percent', '')
                return self._calculate_percentage_change(base_field, council, year)
            
            # If it's a counter-specific calculation
            if counter:
                return self._get_counter_calculated_value(field_name, council, year, counter)
                
            return None
        except Exception as e:
            logger.error(f"Error calculating {field_name}: {e}")
            return None
    
    def _get_population(self, council: Council, year: FinancialYear) -> Optional[int]:
        """Get council population for per capita calculations"""
        try:
            slug = DataField.from_variable_name('population').slug
            pop_characteristic = CouncilCharacteristic.objects.filter(
                council=council,
                field__slug=slug
            ).first()
            
            if pop_characteristic and pop_characteristic.value:
                return int(pop_characteristic.value)
            
            return None
        except (ValueError, TypeError):
            return None
    
    def _calculate_percentage_change(self, base_field: str, council: Council, year: FinancialYear) -> Optional[Decimal]:
        """Calculate year-over-year percentage change"""
        try:
            current_value = self.get_field_value(base_field, council, year)
            
            # Get previous year
            from ..year_utils import previous_year_label
            previous_year_str = previous_year_label(year.label)
            previous_year = None
            if previous_year_str:
                previous_year = FinancialYear.objects.filter(label=previous_year_str).first()
            
            if not previous_year:
                return None
                
            previous_value = self.get_field_value(base_field, council, previous_year)
            
            if current_value and previous_value and previous_value != 0:
                current = Decimal(str(current_value))
                previous = Decimal(str(previous_value))
                
                change = ((current - previous) / previous) * 100
                return change.quantize(Decimal('0.1'))
                
            return None
        except Exception as e:
            logger.error(f"Error calculating percentage change for {base_field}: {e}")
            return None
    
    def _get_counter_calculated_value(self, field_name: str, council: Council, year: FinancialYear, counter: CounterDefinition) -> Any:
        """Get counter-specific calculated values"""
        try:
            # This would integrate with your existing counter calculation logic
            # For now, return None - this can be expanded based on your counter system
            return None
        except Exception as e:
            logger.error(f"Error getting counter calculated value {field_name}: {e}")
            return None
    
    def format_value(self, value: Any, format_type: str = 'default') -> str:
        """
        Format values according to specified format type
        """
        if value is None:
            return "N/A"
        
        try:
            if format_type == 'currency':
                if isinstance(value, (int, float, Decimal)):
                    return f"£{value:,.0f}"
            elif format_type == 'percentage':
                if isinstance(value, (int, float, Decimal)):
                    return f"{value:.1f}%"
            elif format_type == 'number':
                if isinstance(value, (int, float, Decimal)):
                    return f"{value:,.0f}"
            elif format_type == 'decimal':
                if isinstance(value, (int, float, Decimal)):
                    return f"{value:.2f}"
            
            return str(value)
        except Exception as e:
            logger.error(f"Error formatting value {value} as {format_type}: {e}")
            return str(value)
    
    def build_context_data(self, council: Council, year: FinancialYear, counter: CounterDefinition = None) -> Dict[str, Any]:
        """
        Build complete context data for factoid rendering
        """
        context = {
            'council_name': council.name,
            'council_slug': council.slug,
            'year_label': str(year.label),
            'council_type': council.council_type.name if council.council_type else 'Unknown',
        }
        
        # Add all available fields
        for field in DataField.objects.all():
            value = self.get_field_value(field.variable_name, council, year, counter)
            if value is not None:
                context[field.variable_name] = value
        
        return context
    
    def render_template(self, template: FactoidTemplate, context_data: Dict[str, Any]) -> str:
        """
        Render a factoid template with context data and formatting
        """
        import re
        
        template_text = template.template_text
        
        # Find all {field:format} patterns
        pattern = r'\{([^}]+)\}'
        
        def replace_field(match):
            field_spec = match.group(1)
            
            # Parse field name and format
            if ':' in field_spec:
                field_name, format_type = field_spec.split(':', 1)
            else:
                field_name = field_spec
                format_type = 'default'
            
            # Convert slug format to variable name format for context lookup
            field_variable_name = field_name.replace('-', '_')
            
            # Get value from context
            value = context_data.get(field_variable_name)
            
            # Format and return
            return self.format_value(value, format_type)
        
        # Replace all field references
        rendered = re.sub(pattern, replace_field, template_text)
        
        return rendered
    
    def compute_factoid_instance(self, template: FactoidTemplate, council: Council, year: FinancialYear, counter: CounterDefinition = None) -> FactoidInstance:
        """
        Compute a single factoid instance
        """
        try:
            # Build context data
            context_data = self.build_context_data(council, year, counter)
            
            # Render template
            rendered_text = self.render_template(template, context_data)
            
            # Calculate relevance score (simple implementation)
            relevance_score = self._calculate_relevance_score(template, context_data)
            
            # Convert context_data to JSON-serializable format
            json_safe_context = self._make_json_safe(context_data)
            
            # Create or update instance
            instance, created = FactoidInstance.objects.update_or_create(
                template=template,
                council=council,
                financial_year=year,
                counter=counter,
                defaults={
                    'rendered_text': rendered_text,
                    'computed_data': json_safe_context,
                    'relevance_score': relevance_score,
                    'is_significant': relevance_score > 0.5,
                    'expires_at': timezone.now() + timezone.timedelta(hours=24),
                }
            )
            
            return instance
            
        except Exception as e:
            logger.error(f"Error computing factoid instance: {e}")
            raise
    
    def _make_json_safe(self, data: Any) -> Any:
        """
        Convert data to JSON-serializable format by converting Decimals to floats
        """
        if isinstance(data, dict):
            return {key: self._make_json_safe(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_safe(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data
    
    def _calculate_relevance_score(self, template: FactoidTemplate, context_data: Dict[str, Any]) -> float:
        """
        Calculate relevance score for a factoid instance
        """
        score = 0.5  # Base score
        
        # Boost for templates with higher priority
        score += (template.priority / 100) * 0.3
        
        # Boost for templates with significant values
        for field_name in template.referenced_fields:
            value = context_data.get(field_name)
            if value and isinstance(value, (int, float, Decimal)):
                if abs(float(value)) > 1000:  # Arbitrary threshold
                    score += 0.1
        
        # Ensure score is between 0 and 1
        return min(max(score, 0.0), 1.0)
    
    def invalidate_instances_for_field(self, field: DataField):
        """
        Invalidate factoid instances when a field changes
        """
        try:
            # Find all templates that depend on this field
            dependencies = FactoidFieldDependency.objects.filter(field=field)
            
            template_ids = [dep.template_id for dep in dependencies]
            
            # Mark instances as expired
            FactoidInstance.objects.filter(
                template_id__in=template_ids
            ).update(expires_at=timezone.now())
            
            logger.info(f"Invalidated factoid instances for field {field.name}")
            
        except Exception as e:
            logger.error(f"Error invalidating instances for field {field.name}: {e}")
    
    def update_field_dependencies(self, template: FactoidTemplate):
        """
        Update field dependencies for a template
        """
        try:
            # Clear existing dependencies
            FactoidFieldDependency.objects.filter(template=template).delete()
            
            # Create new dependencies
            for field_name in template.referenced_fields:
                try:
                    field = DataField.from_variable_name(field_name)
                    FactoidFieldDependency.objects.create(
                        template=template,
                        field=field,
                        is_critical=True
                    )
                except DataField.DoesNotExist:
                    logger.warning(f"Field {field_name} referenced in template {template.name} does not exist")
            
            logger.info(f"Updated dependencies for template {template.name}")
            
        except Exception as e:
            logger.error(f"Error updating dependencies for template {template.name}: {e}")
    
    def get_factoids_for_counter(self, counter: CounterDefinition, council: Council, year: FinancialYear) -> List[FactoidInstance]:
        """
        Get all relevant factoids for a specific counter context
        Only returns factoids specifically assigned to this counter.
        """
        try:
            # Get templates specifically assigned to this counter only
            # NO generic templates - factoids should only show on their assigned counters
            templates = FactoidTemplate.objects.filter(
                is_active=True,
                counters=counter  # Only templates specifically assigned to this counter
            ).order_by('-priority')
            
            # Filter by council type if specified
            if council.council_type:
                templates = templates.filter(
                    Q(council_types__isnull=True) | 
                    Q(council_types=council.council_type)
                )
            
            # Ensure unique templates (in case a template matches both generic and counter-specific criteria)
            templates = templates.distinct()
            
            instances = []
            for template in templates:
                try:
                    # Check if instance exists and is valid
                    instance = FactoidInstance.objects.filter(
                        template=template,
                        council=council,
                        financial_year=year,
                        counter=counter
                    ).first()
                    
                    if not instance or instance.is_expired():
                        # Compute new instance
                        instance = self.compute_factoid_instance(template, council, year, counter)
                    
                    if instance and instance.is_significant:
                        instances.append(instance)
                        
                except Exception as e:
                    logger.error(f"Error processing template {template.name}: {e}")
                    continue
            
            return instances
            
        except Exception as e:
            logger.error(f"Error getting factoids for counter {counter.name}: {e}")
            return []
