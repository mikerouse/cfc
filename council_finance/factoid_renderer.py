"""
Modern Factoid Rendering System

This module provides server-side rendering of factoid templates using
the new FactoidTemplate model and ExpressionRenderer system.

This replaces the legacy factoids.py functions with a system that uses
the same templates and rendering logic as the React-based admin interface.
"""

import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal

from .models import FactoidTemplate, Council, FinancialYear, CounterDefinition
from .expression_renderer import ExpressionRenderer
from .calculators import get_data_context_for_council
from .agents.counter_agent import CounterAgent

logger = logging.getLogger(__name__)


def get_factoids_for_counter(counter_slug: str, council: Optional[Council] = None, 
                           year: Optional[FinancialYear] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get rendered factoids for a specific counter using the new template system.
    
    This replaces the legacy get_factoids() function with one that uses
    FactoidTemplate and ExpressionRenderer.
    
    Args:
        counter_slug: Slug of the counter to get factoids for
        council: Council instance (optional, for specific council context)
        year: FinancialYear instance (optional, defaults to current year)
        limit: Maximum number of factoids to return
        
    Returns:
        List of dictionaries containing rendered factoid data
    """
    try:
        # Get the counter
        counter = CounterDefinition.objects.filter(slug=counter_slug).first()
        if not counter:
            logger.warning(f"Counter not found: {counter_slug}")
            return []
        
        # Get active factoid templates for this counter
        templates = FactoidTemplate.objects.filter(
            counters=counter,
            is_active=True
        ).order_by('-priority')[:limit]
        
        if not templates.exists():
            return []
        
        # Get year context
        if not year:
            year = FinancialYear.get_current()
        if not year:
            return []
        
        # Use sample council if none provided
        if not council:
            council = Council.objects.filter(is_active=True).first()
        if not council:
            return []
        
        # Get counter value and context
        agent = CounterAgent()
        counter_values = agent.run(council_slug=council.slug, year_label=year.label)
        counter_data = counter_values.get(counter_slug, {})
        
        if not counter_data or counter_data.get('value') in (None, ''):
            return []
        
        # Get full data context for expressions
        try:
            data_context = get_data_context_for_council(council, year.label)
        except Exception as e:
            logger.error(f"Failed to get data context for {council.slug} {year.label}: {e}")
            data_context = {}
        
        # Build expression context
        context = {
            'council_name': council.name,
            'council_slug': council.slug,
            'year_label': year.label,
            'counter_name': counter.name,
            'counter_slug': counter.slug,
            'value': counter_data.get('value', 0),
            'formatted': counter_data.get('formatted', ''),
            'calculated': data_context.get('calculated', {}),
            'characteristic': data_context.get('characteristic', {}),
            'financial': data_context.get('financial', {}),
        }
        
        # Render each template
        renderer = ExpressionRenderer()
        factoids = []
        
        for template in templates:
            try:
                rendered_text = renderer.render_safe(template.template_text, context)
                
                factoid = {
                    'id': template.id,
                    'name': template.name,
                    'slug': template.slug,
                    'text': rendered_text,
                    'emoji': template.emoji,
                    'color_scheme': template.color_scheme,
                    'factoid_type': template.factoid_type,
                    'priority': template.priority,
                    'template': template
                }
                
                # Only include factoids with successfully rendered text
                if rendered_text and not rendered_text.startswith('Error:'):
                    factoids.append(factoid)
                    
            except Exception as e:
                logger.error(f"Error rendering factoid template {template.slug}: {e}")
                continue
        
        return factoids
        
    except Exception as e:
        logger.error(f"Error getting factoids for counter {counter_slug}: {e}")
        return []


def get_factoids_for_council_detail(council: Council, year: Optional[FinancialYear] = None, 
                                  limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get factoids for a council detail page across all counters.
    
    This replaces the legacy get_factoids_for_template_system() function.
    
    Args:
        council: Council instance
        year: FinancialYear instance (optional, defaults to current year)
        limit: Maximum number of factoids to return
        
    Returns:
        List of rendered factoid dictionaries
    """
    try:
        if not year:
            year = FinancialYear.get_current()
        if not year:
            return []
        
        # Get all active factoid templates, prioritized
        templates = FactoidTemplate.objects.filter(
            is_active=True
        ).select_related().prefetch_related('counters').order_by('-priority')[:limit * 2]
        
        if not templates.exists():
            return []
        
        # Get counter values for this council/year
        agent = CounterAgent()
        counter_values = agent.run(council_slug=council.slug, year_label=year.label)
        
        # Get data context for expressions
        try:
            data_context = get_data_context_for_council(council, year.label)
        except Exception as e:
            logger.error(f"Failed to get data context for {council.slug} {year.label}: {e}")
            data_context = {}
        
        # Base context for all factoids
        base_context = {
            'council_name': council.name,
            'council_slug': council.slug,
            'year_label': year.label,
            'calculated': data_context.get('calculated', {}),
            'characteristic': data_context.get('characteristic', {}),
            'financial': data_context.get('financial', {}),
        }
        
        # Render factoids
        renderer = ExpressionRenderer()
        factoids = []
        
        for template in templates:
            # Check if template applies to any counters with data
            template_counters = template.counters.all()
            applicable = False
            
            for counter in template_counters:
                counter_data = counter_values.get(counter.slug, {})
                if counter_data and counter_data.get('value') not in (None, ''):
                    applicable = True
                    
                    # Add counter-specific context
                    context = base_context.copy()
                    context.update({
                        'counter_name': counter.name,
                        'counter_slug': counter.slug,
                        'value': counter_data.get('value', 0),
                        'formatted': counter_data.get('formatted', ''),
                    })
                    
                    try:
                        rendered_text = renderer.render_safe(template.template_text, context)
                        
                        if rendered_text and not rendered_text.startswith('Error:'):
                            factoid = {
                                'id': template.id,
                                'name': template.name,
                                'slug': template.slug,
                                'text': rendered_text,
                                'emoji': template.emoji,
                                'color_scheme': template.color_scheme,
                                'factoid_type': template.factoid_type,
                                'priority': template.priority,
                                'counter_slug': counter.slug,
                                'template': template
                            }
                            factoids.append(factoid)
                            break  # Only use first applicable counter per template
                            
                    except Exception as e:
                        logger.error(f"Error rendering factoid template {template.slug} for counter {counter.slug}: {e}")
                        continue
            
            # Stop when we have enough factoids
            if len(factoids) >= limit:
                break
        
        # Sort by priority and return
        factoids.sort(key=lambda x: x['priority'], reverse=True)
        return factoids[:limit]
        
    except Exception as e:
        logger.error(f"Error getting factoids for council {council.slug}: {e}")
        return []


def get_sample_factoids(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get sample factoids using a representative council and current year.
    
    This is useful for displaying factoids on the home page or other
    general contexts where no specific council is selected.
    
    Args:
        limit: Maximum number of factoids to return
        
    Returns:
        List of rendered factoid dictionaries
    """
    try:
        # Get a representative council (prefer one with lots of data)
        council = Council.objects.filter(
            is_active=True,
            financialfigure__isnull=False
        ).distinct().first()
        
        if not council:
            council = Council.objects.filter(is_active=True).first()
        
        if not council:
            return []
        
        # Use current year
        year = FinancialYear.get_current()
        if not year:
            return []
        
        return get_factoids_for_council_detail(council, year, limit)
        
    except Exception as e:
        logger.error(f"Error getting sample factoids: {e}")
        return []


# Legacy compatibility functions
def get_factoids(counter_slug: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Legacy compatibility function.
    
    This maintains the old API for backwards compatibility while using
    the new factoid template system under the hood.
    """
    try:
        # Extract council from context if provided
        council = None
        if context and 'council_name' in context:
            council = Council.objects.filter(name=context['council_name']).first()
        
        factoids = get_factoids_for_counter(counter_slug, council=council)
        
        # Convert to legacy format
        return [{'text': f['text']} for f in factoids]
        
    except Exception as e:
        logger.error(f"Error in legacy get_factoids function: {e}")
        return []


def get_factoids_for_template_system(counter_slug: str, council=None, year=None, 
                                   base_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Legacy compatibility function for template system.
    
    This maintains the old API while using the new system.
    """
    try:
        factoids = get_factoids_for_council_detail(council, year)
        
        # Convert to legacy format
        return [{'text': f['text']} for f in factoids]
        
    except Exception as e:
        logger.error(f"Error in legacy get_factoids_for_template_system function: {e}")
        return []