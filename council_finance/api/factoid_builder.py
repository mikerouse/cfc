"""
React Factoid Builder API Endpoints

This module provides API endpoints for the React-based factoid template builder.
It offers field discovery, live preview, and template management functionality.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from typing import Dict, List, Any
import logging

from council_finance.models import (
    Council, FinancialYear, DataField, CounterDefinition,
    CouncilCharacteristic, FinancialFigure, FactoidTemplate
)
from council_finance.calculators import get_data_context_for_council
from council_finance.agents.counter_agent import CounterAgent

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_fields_api(request, council_slug=None):
    """
    Get all available fields for factoid templates with sample data.
    
    This endpoint provides the React frontend with:
    - All available field types (characteristics, calculated, financial, counters)
    - Sample data for live preview
    - Field metadata (description, formatting hints)
    """
    logger.info(f"🔍 FACTOID BUILDER API: available_fields_api called by user {request.user}")
    logger.info(f"📊 Request details: method={request.method}, council_slug={council_slug}")
    
    try:
        # Get sample council for field discovery
        sample_council = None
        if council_slug:
            sample_council = get_object_or_404(Council, slug=council_slug)
        else:
            # Use first available council as sample
            sample_council = Council.objects.filter(status='active').first()
            
        if not sample_council:
            return Response({
                'error': 'No councils available for field discovery'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get sample year (prefer current year)
        sample_year = FinancialYear.objects.filter(
            label__in=['2024/25', '2023/24', '2022/23']
        ).first()
        
        if not sample_year:
            sample_year = FinancialYear.objects.first()
            
        # Build comprehensive field data
        field_data = {
            'council_info': {
                'name': sample_council.name,
                'slug': sample_council.slug,
                'year': sample_year.label if sample_year else None
            },
            'characteristics': _get_characteristic_fields(sample_council),
            'calculated': _get_calculated_fields(sample_council, sample_year),
            'financial': _get_financial_fields(sample_council, sample_year),
            'counters': _get_counter_fields(sample_council, sample_year),
            'core_variables': _get_core_variables(sample_council, sample_year),
        }
        
        return Response({
            'success': True,
            'fields': field_data
        })
        
    except Exception as e:
        logger.error(f"Error in available_fields_api: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_factoid_api(request):
    """
    Generate live preview of factoid template with actual data.
    
    Accepts:
    - template_text: The factoid template expression
    - council_slug: Council to use for preview data
    - year_label: Financial year for preview data
    
    Returns:
    - rendered_text: The factoid rendered with actual data
    - errors: Any rendering errors or warnings
    """
    try:
        template_text = request.data.get('template_text', '')
        council_slug = request.data.get('council_slug')
        year_label = request.data.get('year_label')
        
        if not template_text:
            return Response({
                'success': False,
                'error': 'Template text is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Get council and year for preview
        council = None
        if council_slug:
            council = get_object_or_404(Council, slug=council_slug)
        else:
            council = Council.objects.filter(status='active').first()
            
        year = None  
        if year_label:
            year = FinancialYear.objects.filter(label=year_label).first()
        else:
            year = FinancialYear.objects.filter(
                label__in=['2024/25', '2023/24']
            ).first()
            
        # Get context data for rendering
        context = get_data_context_for_council(council, year)
        
        # Use our new expression renderer (will create this next)
        from council_finance.expression_renderer import ExpressionRenderer
        renderer = ExpressionRenderer()
        
        rendered_text, errors = renderer.render_safe(template_text, context)
        
        return Response({
            'success': True,
            'rendered_text': rendered_text,
            'errors': errors,
            'context_keys': list(context.keys())
        })
        
    except Exception as e:
        logger.error(f"Error in preview_factoid_api: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'rendered_text': template_text  # Return original on error
        }, status=status.HTTP_200_OK)  # Don't fail the request


def _get_characteristic_fields(council: Council) -> List[Dict[str, Any]]:
    """Get all characteristic fields with sample data."""
    characteristics = []
    
    # Get defined characteristic fields
    char_fields = DataField.objects.filter(category='characteristic').order_by('name')
    
    for field in char_fields:
        # Try to get actual value for this council
        sample_value = None
        try:
            char_obj = CouncilCharacteristic.objects.filter(
                council=council, field=field
            ).first()
            if char_obj:
                sample_value = char_obj.value
        except:
            pass
            
        characteristics.append({
            'slug': field.slug,
            'name': field.name,
            'description': field.description or f"Council {field.name.lower()}",
            'variable': f"characteristic.{field.slug.replace('-', '_')}",
            'sample_value': sample_value or f"Sample {field.name}",
            'format_hint': 'text'
        })
    
    return characteristics


def _get_calculated_fields(council: Council, year: FinancialYear) -> List[Dict[str, Any]]:
    """Get all calculated fields with sample data."""
    calculated = []
    
    calc_fields = DataField.objects.filter(category='calculated').order_by('name')
    
    # Get actual calculated values
    context = get_data_context_for_council(council, year) if year else {}
    calc_data = context.get('calculated', {})
    
    for field in calc_fields:
        field_key = field.slug.replace('-', '_')
        sample_value = calc_data.get(field_key, 0)
        
        # Format based on field type
        format_hint = 'currency'
        if 'per_capita' in field.slug or 'per_head' in field.slug:
            format_hint = 'currency_per_capita'
        elif 'percentage' in field.slug or 'rate' in field.slug:
            format_hint = 'percentage'
            
        calculated.append({
            'slug': field.slug,
            'name': field.name,
            'description': field.description or f"Calculated {field.name.lower()}",
            'variable': f"calculated.{field_key}",
            'sample_value': sample_value,
            'format_hint': format_hint,
            'formula': field.formula
        })
    
    return calculated


def _get_financial_fields(council: Council, year: FinancialYear) -> List[Dict[str, Any]]:
    """Get all financial fields with sample data."""
    financial = []
    
    fin_fields = DataField.objects.exclude(
        category__in=['characteristic', 'calculated']
    ).order_by('category', 'name')
    
    # Get actual financial values
    context = get_data_context_for_council(council, year) if year else {}
    fin_data = context.get('financial', {})
    
    for field in fin_fields:
        field_key = field.slug.replace('-', '_')
        sample_value = fin_data.get(field_key, 0)
        
        financial.append({
            'slug': field.slug,
            'name': field.name,
            'description': field.description or f"{field.category.title()} figure",
            'variable': f"financial.{field_key}",
            'sample_value': sample_value,
            'format_hint': 'currency',
            'category': field.category
        })
    
    return financial


def _get_counter_fields(council: Council, year: FinancialYear) -> List[Dict[str, Any]]:
    """Get all counter fields with sample data."""
    counters = []
    
    counter_defs = CounterDefinition.objects.filter(
        is_active=True
    ).order_by('name')
    
    # Get actual counter values
    try:
        if year:
            agent = CounterAgent()
            counter_results = agent.run(
                council_slug=council.slug,
                year_label=year.label
            )
        else:
            counter_results = {}
    except:
        counter_results = {}
    
    for counter in counter_defs:
        result = counter_results.get(counter.slug, {})
        sample_value = 0
        
        if isinstance(result, dict):
            sample_value = result.get('value', result.get('raw', 0))
        elif isinstance(result, (int, float)):
            sample_value = result
            
        counters.append({
            'slug': counter.slug,
            'name': counter.name,
            'description': counter.description or f"Counter: {counter.name}",
            'variable': f"counters.{counter.slug.replace('-', '_')}",
            'sample_value': sample_value,
            'format_hint': 'currency'
        })
    
    return counters


def _get_core_variables(council: Council, year: FinancialYear) -> List[Dict[str, Any]]:
    """Get core template variables that are always available."""
    return [
        {
            'slug': 'council_name',
            'name': 'Council Name',
            'description': 'The name of the council',
            'variable': 'council_name',
            'sample_value': council.name,
            'format_hint': 'text'
        },
        {
            'slug': 'year_label',
            'name': 'Financial Year',
            'description': 'The financial year label',
            'variable': 'year_label',
            'sample_value': year.label if year else '2024/25',
            'format_hint': 'text'
        },
        {
            'slug': 'council_slug',
            'name': 'Council Slug',
            'description': 'The URL-friendly council identifier',
            'variable': 'council_slug',
            'sample_value': council.slug,
            'format_hint': 'text'
        }
    ]