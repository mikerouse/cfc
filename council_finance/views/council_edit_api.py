"""
Council Edit API Views for React Interface

Provides mobile-first API endpoints for the React council editing interface.
Separates characteristics (non-temporal) from general/financial data (temporal).
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
import json
import logging

from council_finance.models import (
    Council, DataField, CouncilCharacteristic, FinancialFigure, 
    FinancialYear, ActivityLog
)

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(['GET'])
def council_characteristics_api(request, council_slug):
    """
    Get all council characteristics (non-temporal data)
    
    Returns:
    {
        "success": true,
        "characteristics": {
            "council-website": "https://example.com",
            "council-type": "District Council",
            "population": "50000"
        }
    }
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Get all characteristic fields
        characteristic_fields = DataField.objects.filter(category='characteristic')
        
        # Get all characteristics for this council
        characteristics_qs = CouncilCharacteristic.objects.filter(
            council=council,
            field__category='characteristic'
        ).select_related('field')
        
        # Build characteristics map
        characteristics = {}
        for char in characteristics_qs:
            characteristics[char.field.slug] = char.value
        
        return JsonResponse({
            'success': True,
            'characteristics': characteristics,
            'available_fields': [
                {
                    'slug': field.slug,
                    'name': field.name,
                    'content_type': field.content_type,
                    'required': field.required,
                    'description': field.explanation or ''
                }
                for field in characteristic_fields
            ]
        })
        
    except Exception as e:
        logger.error(f"Error fetching characteristics for {council_slug}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load council characteristics'
        }, status=500)


@login_required
@require_http_methods(['POST'])
def save_council_characteristic_api(request, council_slug):
    """
    Save a council characteristic (non-temporal data)
    
    Body:
    {
        "field": "council-website",
        "value": "https://example.com",
        "category": "characteristics"
    }
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Parse request data
        data = json.loads(request.body)
        field_slug = data.get('field')
        value = data.get('value', '').strip()
        
        if not field_slug:
            return JsonResponse({
                'success': False,
                'error': 'Field slug is required'
            }, status=400)
        
        # Get the field
        field = get_object_or_404(DataField, slug=field_slug, category='characteristic')
        
        # Validate URL fields
        if field.content_type == 'url' and value:
            from council_finance.views.api import validate_url_api
            
            # Create a mock request for URL validation
            mock_request = type('MockRequest', (), {
                'body': json.dumps({'url': value, 'field_slug': field_slug}).encode(),
                'method': 'POST'
            })()
            
            validation_response = validate_url_api(mock_request)
            validation_data = json.loads(validation_response.content)
            
            if not validation_data.get('valid', False):
                return JsonResponse({
                    'success': False,
                    'error': validation_data.get('message', 'URL validation failed')
                }, status=400)
        
        with transaction.atomic():
            # Create or update characteristic
            characteristic, created = CouncilCharacteristic.objects.get_or_create(
                council=council,
                field=field,
                defaults={'value': value}
            )
            
            if not created:
                old_value = characteristic.value
                characteristic.value = value
                characteristic.save()
            else:
                old_value = None
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='data_edit',
                description=f"Updated {field.name} for {council.name}",
                related_council=council,
                field=field,
                old_value=old_value,
                new_value=value
            )
        
        # Calculate points (3 points for characteristics)
        points = 3
        
        return JsonResponse({
            'success': True,
            'message': f'{field.name} updated successfully',
            'field_name': field.name,
            'points': points,
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving characteristic for {council_slug}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to save characteristic'
        }, status=500)


@login_required
@require_http_methods(['GET'])
def council_temporal_data_api(request, council_slug, year_id):
    """
    Get temporal data (general + financial) for a specific year
    
    Returns:
    {
        "success": true,
        "general": {
            "link-to-financial-statement": "https://example.com/statement.pdf",
            "political-control": "Conservative"
        },
        "financial": {
            "total-debt": "1000000",
            "current-liabilities": "500000"
        }
    }
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        year = get_object_or_404(FinancialYear, id=year_id)
        
        # Get all temporal data for this council and year
        # Financial categories: balance_sheet, income, spending, calculated
        # General categories: general
        temporal_data_qs = FinancialFigure.objects.filter(
            council=council,
            year=year,
            field__category__in=['general', 'balance_sheet', 'income', 'spending', 'calculated']
        ).select_related('field')
        
        # Separate general and financial data
        general_data = {}
        financial_data = {}
        
        for figure in temporal_data_qs:
            # Get the appropriate value based on field content type
            if figure.field.content_type in ['monetary', 'integer', 'percentage']:
                figure_value = figure.value
            else:
                figure_value = figure.text_value
            
            if figure.field.category == 'general':
                general_data[figure.field.slug] = figure_value
            elif figure.field.category in ['balance_sheet', 'income', 'spending', 'calculated']:
                financial_data[figure.field.slug] = figure_value
        
        # Get available fields for this temporal data
        general_fields = DataField.objects.filter(category='general')
        financial_fields = DataField.objects.filter(category__in=['balance_sheet', 'income', 'spending', 'calculated'])
        
        return JsonResponse({
            'success': True,
            'year': {
                'id': year.id,
                'label': year.label,
                'display': getattr(year, 'display', None) or year.label.replace('/', '-'),
                'is_current': getattr(year, 'is_current', False)
            },
            'general': general_data,
            'financial': financial_data,
            'available_fields': {
                'general': [
                    {
                        'slug': field.slug,
                        'name': field.name,
                        'content_type': field.content_type,
                        'required': field.required,
                        'description': field.explanation or '',
                        'category': field.category
                    }
                    for field in general_fields
                ],
                'financial': [
                    {
                        'slug': field.slug,
                        'name': field.name,
                        'content_type': field.content_type,
                        'required': field.required,
                        'description': field.explanation or '',
                        'category': field.category
                    }
                    for field in financial_fields
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching temporal data for {council_slug}/{year_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load temporal data'
        }, status=500)


@login_required
@require_http_methods(['POST'])
def save_temporal_data_api(request, council_slug, year_id):
    """
    Save temporal data (general or financial) for a specific year
    
    Body:
    {
        "field": "link-to-financial-statement",
        "value": "https://example.com/statement.pdf",
        "category": "general"
    }
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        year = get_object_or_404(FinancialYear, id=year_id)
        
        # Parse request data
        data = json.loads(request.body)
        field_slug = data.get('field')
        value = data.get('value', '').strip()
        category = data.get('category')
        
        if not field_slug or not category:
            return JsonResponse({
                'success': False,
                'error': 'Field slug and category are required'
            }, status=400)
        
        if category not in ['general', 'financial']:
            return JsonResponse({
                'success': False,
                'error': 'Category must be general or financial'
            }, status=400)
        
        # Get the field - map frontend categories to database categories
        if category == 'financial':
            # Frontend sends 'financial' for all balance_sheet, income, spending, calculated fields
            field = get_object_or_404(
                DataField, 
                slug=field_slug, 
                category__in=['balance_sheet', 'income', 'spending', 'calculated']
            )
        else:
            # For general category, use as-is
            field = get_object_or_404(DataField, slug=field_slug, category=category)
        
        # Validate URL fields for general category
        if category == 'general' and field.content_type == 'url' and value:
            from council_finance.views.api import validate_url_api
            
            # Create a mock request for URL validation
            mock_request = type('MockRequest', (), {
                'body': json.dumps({'url': value, 'field_slug': field_slug}).encode(),
                'method': 'POST'
            })()
            
            validation_response = validate_url_api(mock_request)
            validation_data = json.loads(validation_response.content)
            
            if not validation_data.get('valid', False):
                return JsonResponse({
                    'success': False,
                    'error': validation_data.get('message', 'URL validation failed')
                }, status=400)
        
        with transaction.atomic():
            # Determine which field to use based on content type
            # Numeric types: monetary, integer, percentage (regardless of category)
            # Text types: url, text, list, date, and any other non-numeric types
            is_numeric = field.content_type in ['monetary', 'integer', 'percentage']
            
            # For numeric fields, convert value to decimal if needed
            if is_numeric and value:
                try:
                    # Convert to Decimal for proper storage
                    from decimal import Decimal
                    numeric_value = Decimal(str(value).replace(',', ''))
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'error': f'Invalid numeric value: {value}'
                    }, status=400)
            else:
                numeric_value = None
            
            # Create or update financial figure
            if is_numeric:
                # Use decimal value field for numeric data
                figure, created = FinancialFigure.objects.get_or_create(
                    council=council,
                    year=year,
                    field=field,
                    defaults={'value': numeric_value, 'text_value': None}
                )
                
                if not created:
                    old_value = figure.value
                    figure.value = numeric_value
                    figure.text_value = None  # Clear text value when saving numeric
                    figure.save()
                else:
                    old_value = None
            else:
                # Use text value field for URLs, text, etc.
                figure, created = FinancialFigure.objects.get_or_create(
                    council=council,
                    year=year,
                    field=field,
                    defaults={'text_value': value, 'value': None}
                )
                
                if not created:
                    old_value = figure.text_value
                    figure.text_value = value
                    figure.value = None  # Clear numeric value when saving text
                    figure.save()
                else:
                    old_value = None
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='data_edit',
                description=f"Updated {field.name} for {council.name} ({year.label})",
                related_council=council,
                details={
                    'field_slug': field.slug,
                    'field_name': field.name,
                    'old_value': str(old_value) if old_value is not None else None,
                    'new_value': str(value),
                    'content_type': field.content_type,
                    'category': field.category
                }
            )
        
        # Calculate points based on category
        if category == 'general':
            points = 4  # General data is worth more due to URL validation
        else:
            points = 2  # Financial data
        
        return JsonResponse({
            'success': True,
            'message': f'{field.name} updated successfully',
            'field_name': field.name,
            'points': points,
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving temporal data for {council_slug}/{year_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to save temporal data'
        }, status=500)


@login_required
@require_http_methods(['GET'])
def council_available_years_api(request, council_slug):
    """
    Get available financial years for temporal data editing
    
    Returns:
    {
        "success": true,
        "years": [
            {
                "id": 1,
                "label": "2023/24",
                "display": "2023-24",
                "is_current": true,
                "description": "Current financial year"
            }
        ]
    }
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Get all available financial years
        years = FinancialYear.objects.all().order_by('-start_date')
        
        years_data = []
        for year in years:
            # Handle missing display attribute gracefully
            display_label = getattr(year, 'display', None) or year.label.replace('/', '-')
            years_data.append({
                'id': year.id,
                'label': year.label,
                'display': display_label,
                'is_current': getattr(year, 'is_current', False),
                'description': f"Financial year {year.label}" + (" (Current)" if getattr(year, 'is_current', False) else "")
            })
        
        return JsonResponse({
            'success': True,
            'years': years_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching years for {council_slug}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load available years'
        }, status=500)


@login_required
@require_http_methods(['GET'])
def council_edit_context_api(request, council_slug):
    """
    Get full context data for React council edit interface
    Combines council info, years, and field definitions
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Get council data
        council_data = {
            'id': council.id,
            'slug': council.slug,
            'name': council.name,
            'councilType': council.council_type.name if council.council_type else None,
            'nation': council.council_nation.name if council.council_nation else None,
            'website': council.website,
            'logo_url': council.logo.url if hasattr(council, 'logo') and council.logo else None
        }
        
        # Get available years
        years = FinancialYear.objects.all().order_by('-start_date')
        years_data = [
            {
                'id': year.id,
                'label': year.label,
                'display': getattr(year, 'display', None) or year.label.replace('/', '-'),
                'is_current': getattr(year, 'is_current', False)
            }
            for year in years
        ]
        
        # Get field definitions grouped by category
        fields_by_category = {}
        all_fields = DataField.objects.all().order_by('category', 'name')
        
        for field in all_fields:
            if field.category not in fields_by_category:
                fields_by_category[field.category] = []
            
            fields_by_category[field.category].append({
                'slug': field.slug,
                'name': field.name,
                'content_type': field.content_type,
                'category': field.category,
                'required': field.required,
                'description': field.explanation or '',
                'points': 3 if field.category == 'characteristic' else 4 if field.category == 'general' else 2
            })
        
        return JsonResponse({
            'success': True,
            'council': council_data,
            'years': years_data,
            'fields': fields_by_category
        })
        
    except Exception as e:
        logger.error(f"Error fetching edit context for {council_slug}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load edit context'
        }, status=500)