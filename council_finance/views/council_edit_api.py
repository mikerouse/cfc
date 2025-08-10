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
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
import json
import logging
import tempfile
import os
import requests
from decimal import Decimal

from council_finance.models import (
    Council, DataField, CouncilCharacteristic, FinancialFigure, 
    FinancialYear, ActivityLog
)

# Event Viewer integration
try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False

logger = logging.getLogger(__name__)


def log_council_edit_event(request, level, category, title, message, details=None, council=None):
    """Log council edit events to Event Viewer system"""
    if not EVENT_VIEWER_AVAILABLE:
        return
    
    try:
        event_details = {
            'module': 'council_edit_api',
            'function': request.resolver_match.url_name if (hasattr(request, 'resolver_match') and request.resolver_match) else 'unknown',
            'request_method': request.method,
            'user_tier': getattr(request.user, 'tier', None) if hasattr(request.user, 'tier') else None,
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            event_details.update(details)
        
        SystemEvent.objects.create(
            source='council_edit_api',
            level=level,
            category=category,
            title=title,
            message=message,
            user=request.user if request.user.is_authenticated else None,
            details=event_details
        )
        
    except Exception as e:
        logger.error(f"Failed to log Event Viewer event: {e}")


def log_cache_operation(council_slug, operation_type, cache_keys, success=True, error_message=None, details=None):
    """Log cache operations for debugging cache-related issues"""
    if not EVENT_VIEWER_AVAILABLE:
        return
    
    try:
        event_details = {
            'council_slug': council_slug,
            'operation_type': operation_type,
            'cache_keys': cache_keys if isinstance(cache_keys, list) else [cache_keys],
            'success': success,
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            event_details.update(details)
        
        SystemEvent.objects.create(
            source='cache_management',
            level='info' if success else 'warning',
            category='performance',
            title=f'Cache {operation_type.title()} {"Successful" if success else "Failed"}',
            message=f'Cache {operation_type} for {council_slug}: {"Success" if success else error_message}',
            details=event_details
        )
        
    except Exception as e:
        logger.error(f"Failed to log cache operation event: {e}")

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
    start_time = timezone.now()
    
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Parse request data
        data = json.loads(request.body)
        field_slug = data.get('field')
        value = data.get('value', '').strip()
        
        if not field_slug:
            log_council_edit_event(
                request, 'warning', 'data_validation',
                'Missing Field Slug in Council Edit',
                f'User attempted to save characteristic for {council.name} without field slug',
                details={'council_slug': council_slug, 'submitted_data': data}
            )
            return JsonResponse({
                'success': False,
                'error': 'Field slug is required'
            }, status=400)
        
        # Get the field
        try:
            field = get_object_or_404(DataField, slug=field_slug, category='characteristic')
        except Exception as e:
            log_council_edit_event(
                request, 'error', 'data_integrity',
                'Invalid Field Reference in Council Edit',
                f'Field {field_slug} not found for characteristic category: {str(e)}',
                details={
                    'council_slug': council_slug,
                    'field_slug': field_slug,
                    'category_expected': 'characteristic',
                    'error_type': type(e).__name__
                }
            )
            raise
        
        # Validate URL fields with Event Viewer logging
        if field.content_type == 'url' and value:
            url_validation_start = timezone.now()
            
            try:
                from council_finance.views.api import validate_url_api
                
                # Create a mock request for URL validation
                mock_request = type('MockRequest', (), {
                    'body': json.dumps({'url': value, 'field_slug': field_slug}).encode(),
                    'method': 'POST'
                })()
                
                validation_response = validate_url_api(mock_request)
                validation_data = json.loads(validation_response.content)
                
                url_validation_time = (timezone.now() - url_validation_start).total_seconds()
                
                if not validation_data.get('valid', False):
                    log_council_edit_event(
                        request, 'warning', 'data_validation',
                        'URL Validation Failed in Council Edit',
                        f'Invalid URL submitted for {field.name}: {validation_data.get("message", "Unknown validation error")}',
                        details={
                            'council_slug': council_slug,
                            'field_slug': field_slug,
                            'submitted_url': value,
                            'validation_message': validation_data.get('message'),
                            'validation_time_seconds': url_validation_time
                        }
                    )
                    return JsonResponse({
                        'success': False,
                        'error': validation_data.get('message', 'URL validation failed')
                    }, status=400)
                else:
                    # Log successful URL validation if it took a long time
                    if url_validation_time > 3.0:
                        log_council_edit_event(
                            request, 'info', 'performance',
                            'Slow URL Validation in Council Edit',
                            f'URL validation took {url_validation_time:.2f}s for {field.name}',
                            details={
                                'council_slug': council_slug,
                                'field_slug': field_slug,
                                'url': value,
                                'validation_time_seconds': url_validation_time
                            }
                        )
                        
            except Exception as url_error:
                log_council_edit_event(
                    request, 'error', 'integration',
                    'URL Validation Service Error',
                    f'URL validation service failed for {field.name}: {str(url_error)}',
                    details={
                        'council_slug': council_slug,
                        'field_slug': field_slug,
                        'submitted_url': value,
                        'error_type': type(url_error).__name__
                    }
                )
                # Continue with save - don't block on validation service failures
                logger.warning(f"URL validation failed, proceeding with save: {url_error}")
        
        db_operation_start = timezone.now()
        
        with transaction.atomic():
            try:
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
                    activity_type='update',  # Changed from 'data_edit' to 'update' to match story generator
                    description=f"Updated {field.name} for {council.name}",
                    related_council=council,
                    details={
                        'field_name': field.slug,  # Use field.slug for field_name as story generator expects slug
                        'field_display_name': field.name,  # Keep the human-readable name separately
                        'old_value': str(old_value) if old_value is not None else None,
                        'new_value': str(value),
                        'content_type': field.content_type,
                        'category': field.category
                    }
                )
                
                db_operation_time = (timezone.now() - db_operation_start).total_seconds()
                
                # Log successful database operation
                log_council_edit_event(
                    request, 'info', 'data_integrity',
                    'Council Characteristic Saved Successfully',
                    f'Updated {field.name} for {council.name}' + (' (created new)' if created else ' (updated existing)'),
                    details={
                        'council_slug': council_slug,
                        'field_slug': field_slug,
                        'field_name': field.name,
                        'old_value': str(old_value) if old_value is not None else None,
                        'new_value': str(value),
                        'created_new_record': created,
                        'db_operation_time_seconds': db_operation_time,
                        'content_type': field.content_type
                    }
                )
                
                # Log slow database operations
                if db_operation_time > 2.0:
                    log_council_edit_event(
                        request, 'warning', 'performance',
                        'Slow Database Operation in Council Edit',
                        f'Database save took {db_operation_time:.2f}s for {field.name}',
                        details={
                            'council_slug': council_slug,
                            'field_slug': field_slug,
                            'operation_duration_seconds': db_operation_time,
                            'operation_type': 'characteristic_save'
                        }
                    )
                
            except Exception as db_error:
                log_council_edit_event(
                    request, 'error', 'data_integrity',
                    'Database Save Failed in Council Edit',
                    f'Failed to save {field.name} for {council.name}: {str(db_error)}',
                    details={
                        'council_slug': council_slug,
                        'field_slug': field_slug,
                        'submitted_value': value,
                        'error_type': type(db_error).__name__,
                        'db_operation_time_seconds': (timezone.now() - db_operation_start).total_seconds()
                    }
                )
                raise
        
        # Invalidate counter cache for all years since characteristics can affect all calculations
        # This is done outside the transaction to ensure database changes are committed first
        cache_invalidation_start = timezone.now()
        cache_keys_to_invalidate = []
        
        try:
            from django.core.cache import cache
            from council_finance.models import FinancialYear
            
            for year in FinancialYear.objects.all():
                cache_key = f"counter_values:{council.slug}:{year.label}"
                cache_keys_to_invalidate.append(cache_key)
                cache.delete(cache_key)
            
            cache_invalidation_time = (timezone.now() - cache_invalidation_start).total_seconds()
            
            # Log cache invalidation success
            log_cache_operation(
                council_slug, 'invalidation', cache_keys_to_invalidate, 
                success=True,
                details={
                    'reason': 'characteristic_update',
                    'field_slug': field_slug,
                    'years_affected': len(cache_keys_to_invalidate),
                    'invalidation_time_seconds': cache_invalidation_time
                }
            )
            
            logger.info(f"Invalidated {len(cache_keys_to_invalidate)} counter cache keys for council {council.slug}")
            
        except Exception as cache_error:
            cache_invalidation_time = (timezone.now() - cache_invalidation_start).total_seconds()
            
            log_cache_operation(
                council_slug, 'invalidation', cache_keys_to_invalidate,
                success=False, error_message=str(cache_error),
                details={
                    'reason': 'characteristic_update',
                    'field_slug': field_slug,
                    'error_type': type(cache_error).__name__,
                    'invalidation_time_seconds': cache_invalidation_time
                }
            )
            
            # Don't fail the request on cache errors, but log for investigation
            logger.warning(f"Cache invalidation failed for {council_slug}: {cache_error}")
        
        # Calculate processing time
        total_processing_time = (timezone.now() - start_time).total_seconds()
        
        # Log overall performance
        if total_processing_time > 5.0:
            log_council_edit_event(
                request, 'warning', 'performance',
                'Slow Council Edit Operation',
                f'Total characteristic save took {total_processing_time:.2f}s for {council.name}',
                details={
                    'council_slug': council_slug,
                    'field_slug': field_slug,
                    'total_processing_time_seconds': total_processing_time,
                    'operation_type': 'save_council_characteristic'
                }
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
        
    except json.JSONDecodeError as json_error:
        log_council_edit_event(
            request, 'error', 'data_validation',
            'Invalid JSON in Council Edit Request',
            f'Failed to parse JSON for council {council_slug}: {str(json_error)}',
            details={
                'council_slug': council_slug,
                'error_type': 'JSONDecodeError',
                'request_body_length': len(request.body) if request.body else 0
            }
        )
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        total_processing_time = (timezone.now() - start_time).total_seconds()
        
        log_council_edit_event(
            request, 'error', 'system',
            'Council Characteristic Save Failed',
            f'Unexpected error saving characteristic for {council_slug}: {str(e)}',
            details={
                'council_slug': council_slug,
                'error_type': type(e).__name__,
                'total_processing_time_seconds': total_processing_time,
                'operation_type': 'save_council_characteristic'
            }
        )
        
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
        # Financial categories: balance_sheet, income, spending (exclude calculated - these are auto-generated)
        # General categories: general
        temporal_data_qs = FinancialFigure.objects.filter(
            council=council,
            year=year,
            field__category__in=['general', 'balance_sheet', 'income', 'spending']
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
            elif figure.field.category in ['balance_sheet', 'income', 'spending']:
                financial_data[figure.field.slug] = figure_value
        
        # Get available fields for this temporal data (exclude calculated fields - they're auto-generated)
        general_fields = DataField.objects.filter(category='general')
        financial_fields = DataField.objects.filter(category__in=['balance_sheet', 'income', 'spending'])
        
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
    start_time = timezone.now()
    
    try:
        council = get_object_or_404(Council, slug=council_slug)
        year = get_object_or_404(FinancialYear, id=year_id)
        
        # Parse request data
        data = json.loads(request.body)
        field_slug = data.get('field')
        value = data.get('value', '').strip()
        category = data.get('category')
        
        if not field_slug or not category:
            log_council_edit_event(
                request, 'warning', 'data_validation',
                'Missing Required Fields in Temporal Data Save',
                f'User attempted to save temporal data for {council.name} ({year.label}) without required fields',
                details={
                    'council_slug': council_slug,
                    'year_id': year_id,
                    'year_label': year.label,
                    'submitted_data': data,
                    'missing_field_slug': not field_slug,
                    'missing_category': not category
                }
            )
            return JsonResponse({
                'success': False,
                'error': 'Field slug and category are required'
            }, status=400)
        
        if category not in ['general', 'financial']:
            log_council_edit_event(
                request, 'warning', 'data_validation',
                'Invalid Category in Temporal Data Save',
                f'Invalid category "{category}" submitted for {council.name} ({year.label})',
                details={
                    'council_slug': council_slug,
                    'year_id': year_id,
                    'year_label': year.label,
                    'field_slug': field_slug,
                    'invalid_category': category,
                    'valid_categories': ['general', 'financial']
                }
            )
            return JsonResponse({
                'success': False,
                'error': 'Category must be general or financial'
            }, status=400)
        
        # Get the field - map frontend categories to database categories
        try:
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
                
        except Exception as field_error:
            # This is a critical point where Birmingham data issues could occur
            log_council_edit_event(
                request, 'error', 'data_integrity',
                'Field Resolution Failed in Temporal Data Save',
                f'Field {field_slug} not found for category {category}: {str(field_error)}',
                details={
                    'council_slug': council_slug,
                    'year_id': year_id,
                    'year_label': year.label,
                    'field_slug': field_slug,
                    'category_requested': category,
                    'database_categories_expected': ['balance_sheet', 'income', 'spending', 'calculated'] if category == 'financial' else [category],
                    'error_type': type(field_error).__name__
                }
            )
            raise
        
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
        
        db_operation_start = timezone.now()
        
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
                    
                    # Log numeric data conversion for Birmingham issue debugging
                    log_council_edit_event(
                        request, 'info', 'data_processing',
                        'Numeric Data Conversion in Temporal Save',
                        f'Converted "{value}" to {numeric_value} for {field.name} ({council.name}, {year.label})',
                        details={
                            'council_slug': council_slug,
                            'year_label': year.label,
                            'field_slug': field_slug,
                            'field_content_type': field.content_type,
                            'original_value': value,
                            'converted_value': str(numeric_value),
                            'is_numeric_field': True
                        }
                    )
                    
                except (ValueError, TypeError) as conversion_error:
                    log_council_edit_event(
                        request, 'error', 'data_validation',
                        'Numeric Conversion Failed in Temporal Save',
                        f'Failed to convert "{value}" to numeric for {field.name}: {str(conversion_error)}',
                        details={
                            'council_slug': council_slug,
                            'year_label': year.label,
                            'field_slug': field_slug,
                            'field_content_type': field.content_type,
                            'invalid_value': value,
                            'error_type': type(conversion_error).__name__
                        }
                    )
                    return JsonResponse({
                        'success': False,
                        'error': f'Invalid numeric value: {value}'
                    }, status=400)
            else:
                numeric_value = None
                
                # Log text data for debugging
                if value:
                    log_council_edit_event(
                        request, 'info', 'data_processing',
                        'Text Data Save in Temporal Save',
                        f'Saving text value for {field.name} ({council.name}, {year.label})',
                        details={
                            'council_slug': council_slug,
                            'year_label': year.label,
                            'field_slug': field_slug,
                            'field_content_type': field.content_type,
                            'text_value_length': len(value),
                            'is_numeric_field': False
                        }
                    )
            
            # Create or update financial figure - critical for Birmingham data issue debugging
            try:
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
                        
                    # Log successful numeric FinancialFigure save
                    log_council_edit_event(
                        request, 'info', 'data_integrity',
                        'Financial Figure Saved (Numeric)',
                        f'{"Created" if created else "Updated"} {field.name} for {council.name} ({year.label}): {numeric_value}',
                        details={
                            'council_slug': council_slug,
                            'year_label': year.label,
                            'field_slug': field_slug,
                            'field_category': field.category,
                            'old_value': str(old_value) if old_value is not None else None,
                            'new_value': str(numeric_value),
                            'created_new_record': created,
                            'data_type': 'numeric'
                        }
                    )
                    
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
                        
                    # Log successful text FinancialFigure save
                    log_council_edit_event(
                        request, 'info', 'data_integrity',
                        'Financial Figure Saved (Text)',
                        f'{"Created" if created else "Updated"} {field.name} for {council.name} ({year.label})',
                        details={
                            'council_slug': council_slug,
                            'year_label': year.label,
                            'field_slug': field_slug,
                            'field_category': field.category,
                            'old_value': str(old_value) if old_value is not None else None,
                            'new_value': value,
                            'created_new_record': created,
                            'data_type': 'text'
                        }
                    )
                    
            except Exception as figure_error:
                # Critical error logging for Birmingham data issues
                log_council_edit_event(
                    request, 'error', 'data_integrity',
                    'Financial Figure Save Failed',
                    f'Failed to save {field.name} for {council.name} ({year.label}): {str(figure_error)}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year.label,
                        'field_slug': field_slug,
                        'field_category': field.category,
                        'submitted_value': value,
                        'is_numeric': is_numeric,
                        'converted_numeric_value': str(numeric_value) if numeric_value is not None else None,
                        'error_type': type(figure_error).__name__
                    }
                )
                raise
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='update',  # Changed from 'data_edit' to 'update' to match story generator
                description=f"Updated {field.name} for {council.name} ({year.label})",
                related_council=council,
                details={
                    'field_name': field.slug,  # Use field.slug for field_name as story generator expects slug
                    'field_display_name': field.name,  # Keep the human-readable name separately
                    'old_value': str(old_value) if old_value is not None else None,
                    'new_value': str(value),
                    'year': year.label,  # Add year for story generator
                    'content_type': field.content_type,
                    'category': field.category
                }
            )
        
        # Invalidate counter cache so updated figures are immediately visible
        # This is done outside the transaction to ensure database changes are committed first
        # This is CRITICAL for Birmingham data visibility issue
        cache_invalidation_start = timezone.now()
        
        try:
            from django.core.cache import cache
            cache_key_current = f"counter_values:{council.slug}:{year.label}"
            cache.delete(cache_key_current)
            
            cache_invalidation_time = (timezone.now() - cache_invalidation_start).total_seconds()
            
            # Log successful cache invalidation for Birmingham debugging
            log_cache_operation(
                council_slug, 'invalidation', [cache_key_current],
                success=True,
                details={
                    'reason': 'temporal_data_update',
                    'field_slug': field_slug,
                    'year_label': year.label,
                    'category': category,
                    'invalidation_time_seconds': cache_invalidation_time
                }
            )
            
            logger.info(f"Invalidated counter cache: {cache_key_current}")
            
        except Exception as cache_error:
            cache_invalidation_time = (timezone.now() - cache_invalidation_start).total_seconds()
            
            # Critical cache error logging - this could cause Birmingham "no data" issue
            log_cache_operation(
                council_slug, 'invalidation', [f"counter_values:{council.slug}:{year.label}"],
                success=False, error_message=str(cache_error),
                details={
                    'reason': 'temporal_data_update',
                    'field_slug': field_slug,
                    'year_label': year.label,
                    'category': category,
                    'error_type': type(cache_error).__name__,
                    'invalidation_time_seconds': cache_invalidation_time
                }
            )
            
            # Don't fail the request on cache errors, but log for investigation
            logger.warning(f"Cache invalidation failed for {council_slug}/{year.label}: {cache_error}")
        
        # Calculate processing time
        total_processing_time = (timezone.now() - start_time).total_seconds()
        
        # Log performance issues
        if total_processing_time > 5.0:
            log_council_edit_event(
                request, 'warning', 'performance',
                'Slow Temporal Data Save Operation',
                f'Total temporal data save took {total_processing_time:.2f}s for {council.name} ({year.label})',
                details={
                    'council_slug': council_slug,
                    'year_label': year.label,
                    'field_slug': field_slug,
                    'total_processing_time_seconds': total_processing_time,
                    'operation_type': 'save_temporal_data'
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
        
    except json.JSONDecodeError as json_error:
        log_council_edit_event(
            request, 'error', 'data_validation',
            'Invalid JSON in Temporal Data Save Request',
            f'Failed to parse JSON for council {council_slug}/{year_id}: {str(json_error)}',
            details={
                'council_slug': council_slug,
                'year_id': year_id,
                'error_type': 'JSONDecodeError',
                'request_body_length': len(request.body) if request.body else 0
            }
        )
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        total_processing_time = (timezone.now() - start_time).total_seconds()
        
        log_council_edit_event(
            request, 'error', 'system',
            'Temporal Data Save Failed',
            f'Unexpected error saving temporal data for {council_slug}/{year_id}: {str(e)}',
            details={
                'council_slug': council_slug,
                'year_id': year_id,
                'error_type': type(e).__name__,
                'total_processing_time_seconds': total_processing_time,
                'operation_type': 'save_temporal_data'
            }
        )
        
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


@require_http_methods(['GET'])
def council_completion_percentage_api(request, council_slug, year_id=None):
    """
    Calculate accurate completion percentages for council data using database queries.
    
    Returns:
    {
        "success": true,
        "completion": {
            "overall": {
                "total_fields": 45,
                "complete": 23, 
                "percentage": 51
            },
            "by_category": {
                "characteristics": {"total": 8, "complete": 6, "percentage": 75},
                "financial": {"total": 32, "complete": 15, "percentage": 47},
                "general": {"total": 5, "complete": 2, "percentage": 40}
            }
        }
    }
    """
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # If year_id provided, get the specific year; otherwise get current year
        if year_id:
            year = get_object_or_404(FinancialYear, id=year_id)
        else:
            # Get current financial year (or most recent if no current year)
            year = FinancialYear.objects.filter(is_current=True).first()
            if not year:
                year = FinancialYear.objects.order_by('-start_date').first()
                
        if not year:
            return JsonResponse({
                'success': False,
                'error': 'No financial years available'
            }, status=400)
        
        # Debug logging to identify None values
        if council is None:
            logger.error(f"Council is None for slug: {council_slug}")
            raise ValueError("Council is None")
        if year is None:
            logger.error(f"Year is None for year_id: {year_id}")
            raise ValueError("Year is None")
        
        completion_data = {}
        
        # Calculate characteristics completion (non-temporal data)
        characteristics_fields = DataField.objects.filter(category='characteristic')  # Fixed: singular 'characteristic'
        characteristics_with_data = CouncilCharacteristic.objects.filter(
            council=council,
            field__in=characteristics_fields
        ).values_list('field_id', flat=True)
        
        characteristics_stats = {
            'total': characteristics_fields.count(),
            'complete': len(set(characteristics_with_data)),
        }
        characteristics_stats['percentage'] = (
            round((characteristics_stats['complete'] / characteristics_stats['total']) * 100)
            if characteristics_stats['total'] > 0 else 0
        )
        
        # Calculate financial data completion (temporal data) - FOCUS ON CURRENT YEAR ONLY
        financial_fields = DataField.objects.filter(
            category__in=['balance_sheet', 'income', 'spending']  # Exclude calculated fields
        )
        financial_with_data = FinancialFigure.objects.filter(
            council=council,
            year=year,
            field__in=financial_fields
        ).values_list('field_id', flat=True)
        
        financial_stats = {
            'total': financial_fields.count(),
            'complete': len(set(financial_with_data)),
        }
        financial_stats['percentage'] = (
            round((financial_stats['complete'] / financial_stats['total']) * 100)
            if financial_stats['total'] > 0 else 0
        )
        
        # Focus on current year financial data only
        focus_year = year
        focus_year_label = f"{financial_stats['percentage']}% complete for {year.label}"
        
        # Calculate general data completion (temporal data)
        general_fields = DataField.objects.filter(category='general')
        general_with_data = FinancialFigure.objects.filter(
            council=council,
            year=year,
            field__in=general_fields
        ).values_list('field_id', flat=True)
        
        general_stats = {
            'total': general_fields.count(),
            'complete': len(set(general_with_data)),
        }
        general_stats['percentage'] = (
            round((general_stats['complete'] / general_stats['total']) * 100)
            if general_stats['total'] > 0 else 0
        )
        
        # Calculate overall completion
        total_fields = characteristics_stats['total'] + financial_stats['total'] + general_stats['total']
        total_complete = characteristics_stats['complete'] + financial_stats['complete'] + general_stats['complete']
        overall_percentage = round((total_complete / total_fields) * 100) if total_fields > 0 else 0
        
        overall_stats = {
            'total_fields': total_fields,
            'complete': total_complete,
            'percentage': overall_percentage
        }
        
        completion_data = {
            'overall': {
                'total_fields': financial_stats['total'],  # Focus on financial fields only
                'complete': financial_stats['complete'],
                'percentage': financial_stats['percentage']
            },
            'by_category': {
                'characteristics': characteristics_stats,
                'financial': financial_stats,
                'general': general_stats
            },
            'year': {
                'id': focus_year.id,  # Use focus year (current or previous)
                'label': focus_year.label,
                'display': getattr(focus_year, 'display', None) or focus_year.label.replace('/', '-')
            },
            'focus': {
                'year_label': focus_year_label,  # e.g., "100% complete for 2024/25" or "2024/25 complete, 20% complete for 2023/24"
                'is_current_year': focus_year.id == year.id,
                'financial_progress': financial_stats['percentage']
            }
        }
        
        # Log completion calculation for debugging
        log_council_edit_event(
            request, 'info', 'performance',
            'Completion Percentage Calculated',
            f'Calculated completion for {council.name}: {focus_year_label}',
            details={
                'council_slug': council_slug,
                'focus_year_label': focus_year_label,
                'focus_year_id': focus_year.id,
                'requested_year': year.label,
                'financial_percentage': financial_stats['percentage'],
                'financial_fields': f"{financial_stats['complete']}/{financial_stats['total']}",
                'is_current_year_focus': focus_year.id == year.id
            }
        )
        
        return JsonResponse({
            'success': True,
            'completion': completion_data
        })
        
    except Exception as e:
        logger.error(f"Error calculating completion percentage for {council_slug}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to calculate completion percentage'
        }, status=500)



@login_required
@require_http_methods(['POST'])
def process_pdf_api(request):
    """
    Process PDF financial statements using Apache Tika and OpenAI
    
    Body (multipart/form-data):
    {
        "council_slug": "birmingham",
        "year_id": 1,
        "pdf_file": <file>,  // OR
        "pdf_url": "https://example.com/statement.pdf",
        "source_type": "upload" | "url"
    }
    
    Returns:
    {
        "success": true,
        "extracted_data": {
            "total-debt": {
                "value": 1500000000,
                "field_name": "Total Debt",
                "source_text": "Total borrowing £1.5bn as at March 2024...",
                "page_number": 12
            }
        },
        "confidence_scores": {
            "total-debt": 0.95,
            "current-liabilities": 0.87
        },
        "processing_stats": {
            "fields_found": 15,
            "processing_time": 23.4,
            "pages_processed": 45
        }
    }
    """
    start_time = timezone.now()
    
    try:
        # Parse request data
        council_slug = request.POST.get('council_slug')
        year_id = request.POST.get('year_id')
        source_type = request.POST.get('source_type')
        
        if not all([council_slug, year_id, source_type]):
            return JsonResponse({
                'success': False,
                'error': 'council_slug, year_id, and source_type are required'
            }, status=400)
        
        # Get council and year
        council = get_object_or_404(Council, slug=council_slug)
        year = get_object_or_404(FinancialYear, id=year_id)
        
        # Log PDF processing attempt
        log_council_edit_event(
            request, 'info', 'data_processing',
            'PDF Processing Started',
            f'Starting PDF processing for {council.name} ({year.label})',
            details={
                'council_slug': council_slug,
                'year_id': year_id,
                'year_label': year.label,
                'source_type': source_type,
                'user_tier': getattr(request.user, 'tier', None)
            }
        )
        
        # Get PDF content
        pdf_path = None
        cleanup_file = False
        
        try:
            if source_type == 'upload':
                pdf_file = request.FILES.get('pdf_file')
                if not pdf_file:
                    return JsonResponse({
                        'success': False,
                        'error': 'PDF file is required for upload'
                    }, status=400)
                
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    for chunk in pdf_file.chunks():
                        temp_file.write(chunk)
                    pdf_path = temp_file.name
                    cleanup_file = True
                    
            elif source_type == 'url':
                pdf_url = request.POST.get('pdf_url')
                if not pdf_url:
                    return JsonResponse({
                        'success': False,
                        'error': 'PDF URL is required for URL source'
                    }, status=400)
                
                # Download PDF from URL
                try:
                    response = requests.get(pdf_url, timeout=60)
                    response.raise_for_status()
                    
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                        temp_file.write(response.content)
                        pdf_path = temp_file.name
                        cleanup_file = True
                        
                except requests.RequestException as e:
                    return JsonResponse({
                        'success': False,
                        'error': f'Failed to download PDF: {str(e)}'
                    }, status=400)
            
            # Extract text using Apache Tika
            tika_start = timezone.now()
            try:
                try:
                    from tika import parser
                except ImportError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Apache Tika is not installed. Please install python-tika to use PDF processing.'
                    }, status=500)
                
                parsed_pdf = parser.from_file(pdf_path)
                pdf_text = parsed_pdf['content'] or ''
                
                tika_time = (timezone.now() - tika_start).total_seconds()
                
                if not pdf_text.strip():
                    return JsonResponse({
                        'success': False,
                        'error': 'Could not extract text from PDF'
                    }, status=400)
                    
            except Exception as tika_error:
                log_council_edit_event(
                    request, 'error', 'integration',
                    'PDF Text Extraction Failed',
                    f'Apache Tika failed to extract text: {str(tika_error)}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year.label,
                        'error_type': type(tika_error).__name__,
                        'file_size': os.path.getsize(pdf_path) if pdf_path else 0
                    }
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to extract text from PDF'
                }, status=500)
            
            # AI analysis using OpenAI
            ai_start = timezone.now()
            try:
                # Get financial field definitions for the AI prompt
                financial_fields = DataField.objects.filter(
                    category__in=['balance_sheet', 'income', 'spending']
                ).values('slug', 'name', 'explanation')
                
                field_definitions = {}
                for field in financial_fields:
                    field_definitions[field['slug']] = {
                        'name': field['name'],
                        'description': field['explanation'] or ''
                    }
                
                # Import OpenAI here to avoid import issues if not installed
                try:
                    import openai
                    from django.conf import settings
                    
                    if not hasattr(settings, 'OPENAI_API_KEY'):
                        return JsonResponse({
                            'success': False,
                            'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY in settings.'
                        }, status=500)
                    
                    openai.api_key = settings.OPENAI_API_KEY
                except ImportError:
                    return JsonResponse({
                        'success': False,
                        'error': 'OpenAI library is not installed. Please install openai to use AI PDF processing.'
                    }, status=500)
                
                # Construct AI prompt
                prompt = f"""
You are a financial data extraction specialist. Extract financial figures from this council financial statement for {council.name} ({year.label}).

Find values for these specific fields (amounts in £, return as integers):
{json.dumps(field_definitions, indent=2)}

PDF Content:
{pdf_text[:8000]}  # Limit text to avoid token limits

Return ONLY valid JSON in this exact format:
{{
  "extracted_data": {{
    "field-slug": {{
      "value": 1500000000,
      "field_name": "Field Name",
      "source_text": "relevant text excerpt",
      "page_number": 1
    }}
  }},
  "confidence_scores": {{
    "field-slug": 0.95
  }}
}}

Rules:
- Only include fields you find clear numeric values for
- Convert all amounts to integers (£1.5m becomes 1500000)
- Confidence 0.0-1.0 based on text clarity
- Include relevant source text excerpt
- Skip fields you cannot find or are unsure about
"""
                
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                ai_time = (timezone.now() - ai_start).total_seconds()
                
                # Parse AI response
                ai_content = response.choices[0].message.content.strip()
                
                # Extract JSON from response (handle cases where AI adds explanatory text)
                import re
                json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if json_match:
                    ai_content = json_match.group(0)
                
                ai_result = json.loads(ai_content)
                extracted_data = ai_result.get('extracted_data', {})
                confidence_scores = ai_result.get('confidence_scores', {})
                
            except Exception as ai_error:
                log_council_edit_event(
                    request, 'error', 'integration',
                    'AI Analysis Failed',
                    f'OpenAI API failed: {str(ai_error)}',
                    details={
                        'council_slug': council_slug,
                        'year_label': year.label,
                        'error_type': type(ai_error).__name__,
                        'text_length': len(pdf_text) if 'pdf_text' in locals() else 0
                    }
                )
                return JsonResponse({
                    'success': False,
                    'error': 'AI analysis failed. Please try manual entry.'
                }, status=500)
                
        finally:
            # Clean up temporary file
            if cleanup_file and pdf_path and os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
        
        # Calculate processing stats
        total_processing_time = (timezone.now() - start_time).total_seconds()
        
        processing_stats = {
            'fields_found': len(extracted_data),
            'processing_time': total_processing_time,
            'tika_time': tika_time if 'tika_time' in locals() else 0,
            'ai_time': ai_time if 'ai_time' in locals() else 0,
            'pages_processed': pdf_text.count('\f') + 1 if 'pdf_text' in locals() else 0
        }
        
        # Log successful processing
        log_council_edit_event(
            request, 'info', 'data_processing',
            'PDF Processing Completed',
            f'Successfully processed PDF for {council.name} ({year.label}): {len(extracted_data)} fields found',
            details={
                'council_slug': council_slug,
                'year_label': year.label,
                'fields_found': len(extracted_data),
                'processing_time_seconds': total_processing_time,
                'source_type': source_type,
                'avg_confidence': sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
            }
        )
        
        return JsonResponse({
            'success': True,
            'extracted_data': extracted_data,
            'confidence_scores': confidence_scores,
            'processing_stats': processing_stats
        })
        
    except Exception as e:
        total_processing_time = (timezone.now() - start_time).total_seconds()
        
        log_council_edit_event(
            request, 'error', 'system',
            'PDF Processing Failed',
            f'Unexpected error processing PDF: {str(e)}',
            details={
                'council_slug': council_slug if 'council_slug' in locals() else None,
                'year_id': year_id if 'year_id' in locals() else None,
                'error_type': type(e).__name__,
                'processing_time_seconds': total_processing_time
            }
        )
        
        logger.error(f"Error processing PDF: {e}")
        return JsonResponse({
            'success': False,
            'error': 'PDF processing failed. Please try again or use manual entry.'
        }, status=500)