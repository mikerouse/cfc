"""
Real-time Factoid API Views

This module provides REST API endpoints for the React factoid builder,
including real-time field discovery, template validation, and live preview.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.utils import timezone
import json
import logging

from ..models.factoid import (
    FactoidTemplate,
    FactoidInstance,
    FactoidFieldDependency,
)
from ..models.field import DataField
from ..models.council import Council, FinancialYear
from ..models.counter import CounterDefinition
from ..services.factoid_engine import FactoidEngine
from ..serializers.factoid_serializers import (
    FactoidTemplateSerializer,
    DataFieldSerializer,
    FactoidInstanceSerializer,
)

logger = logging.getLogger(__name__)

def _log_api_activity(request, endpoint, action, status='completed', extra_data=None, error=None):
    """Helper function for consistent API logging"""
    from ..activity_logging import log_activity
    
    log_data = {
        'endpoint': endpoint,
        'method': request.method,
        'user_authenticated': getattr(request, 'user', None) and request.user.is_authenticated,
        'user_id': request.user.id if getattr(request, 'user', None) and request.user.is_authenticated else None,
        'session_id': request.session.session_key if hasattr(request, 'session') else None,
        'ip_address': request.META.get('REMOTE_ADDR', 'unknown'),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'request_path': request.path,
        'timestamp': timezone.now().isoformat(),
    }
    
    if extra_data:
        log_data.update(extra_data)
        
    if error:
        log_data.update({
            'error_type': type(error).__name__,
            'error_message': str(error),
        })
    
    activity_type = "system" if error else "contribution"
    activity_name = f"factoid_api_{action}"
    if error:
        activity_name += "_error"
    
    try:
        log_activity(
            request,
            activity=activity_name,
            log_type="system" if error else "user",
            action=action,
            extra=log_data
        )
    except Exception as log_error:
        logger.error(f"Failed to log API activity: {log_error}", exc_info=True)


class FactoidAPIViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for factoid templates with real-time features
    """
    queryset = FactoidTemplate.objects.all()
    serializer_class = FactoidTemplateSerializer
    permission_classes = []  # Temporarily disabled for UI testing
    
    def get_queryset(self):
        """Filter based on user permissions"""
        queryset = super().get_queryset()
        
        # Add any user-specific filtering here
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set creator when creating template"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def discover_fields(self, request):
        """
        Discover all available fields for drag-and-drop
        """
        start_time = timezone.now()
        
        try:
            # Get all data fields ordered by category and name
            fields = DataField.objects.all().order_by('category', 'name')
            
            # Group by category
            field_groups = {}
            for field in fields:
                category = field.category
                if category not in field_groups:
                    field_groups[category] = []
                
                field_data = {
                    'id': field.id,
                    'name': field.name,
                    'variable_name': field.slug,  # Use slug as variable name
                    'description': field.explanation,
                    'data_type': field.content_type,  # Map to content_type field
                    'sample_value': getattr(field, 'sample_value', None),
                    'formatting_options': self._get_formatting_options(field.content_type),
                }
                
                field_groups[category].append(field_data)
            
            # Add computed fields
            field_groups['computed'] = [
                {
                    'id': 'council_name',
                    'name': 'Council Name',
                    'variable_name': 'council_name',
                    'description': 'Name of the council',
                    'data_type': 'text',
                    'sample_value': 'Worcestershire County Council',
                    'formatting_options': ['default'],
                },
                {
                    'id': 'year_label',
                    'name': 'Financial Year',
                    'variable_name': 'year_label',
                    'description': 'Financial year label',
                    'data_type': 'text',
                    'sample_value': '2023-24',
                    'formatting_options': ['default'],
                },
                {
                    'id': 'council_type',
                    'name': 'Council Type',
                    'variable_name': 'council_type',
                    'description': 'Type of council',
                    'data_type': 'text',
                    'sample_value': 'County Council',
                    'formatting_options': ['default'],
                },
            ]
            
            total_fields = sum(len(group) for group in field_groups.values())
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log successful field discovery
            _log_api_activity(
                request, 
                'discover_fields', 
                'field_discovery',
                extra_data={
                    'total_fields_discovered': total_fields,
                    'field_categories': list(field_groups.keys()),
                    'execution_time_seconds': execution_time,
                    'db_fields_count': fields.count(),
                    'computed_fields_count': len(field_groups.get('computed', [])),
                }
            )
            
            return Response({
                'success': True,
                'field_groups': field_groups,
                'total_fields': total_fields,
            })
            
        except Exception as e:
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log field discovery error
            _log_api_activity(
                request, 
                'discover_fields', 
                'field_discovery_failed',
                error=e,
                extra_data={
                    'execution_time_seconds': execution_time,
                }
            )
            
            logger.error(f"Error discovering fields: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_formatting_options(self, content_type):
        """Get available formatting options for a content type"""
        if content_type in ['monetary', 'integer']:
            return ['default', 'currency', 'number', 'percentage']
        elif content_type == 'text':
            return ['default']
        elif content_type == 'url':
            return ['default', 'link']
        elif content_type == 'list':
            return ['default', 'list']
        else:
            return ['default']
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Generate live preview of factoid template
        """
        start_time = timezone.now()
        
        try:
            template = self.get_object()
            
            # Get sample council and year for preview
            council_slug = request.data.get('council_slug')
            year_slug = request.data.get('year_slug', '2023-24')
            counter_slug = request.data.get('counter_slug')
            template_text = request.data.get('template_text', template.template_text)
            
            # Use provided council or default to first available
            if council_slug:
                council = Council.objects.filter(slug=council_slug).first()
            else:
                council = Council.objects.filter(is_live=True).first()
            
            if not council:
                _log_api_activity(
                    request, 
                    'preview_template', 
                    'preview_failed_no_council',
                    extra_data={
                        'template_id': pk,
                        'council_slug_requested': council_slug,
                        'year_slug': year_slug,
                    }
                )
                return Response({
                    'success': False,
                    'error': 'No council available for preview'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get or create year
            year_parts = year_slug.split('-')
            if len(year_parts) == 2:
                start_year = int(year_parts[0])
            else:
                start_year = int(year_slug)
            
            year, _ = FinancialYear.objects.get_or_create(
                year=start_year,
                defaults={'year': start_year}
            )
            
            # Get counter if specified
            counter = None
            if counter_slug:
                counter = CounterDefinition.objects.filter(slug=counter_slug).first()
            
            # Generate preview using factoid engine
            engine = FactoidEngine()
            context_data = engine.build_context_data(council, year, counter)
            
            # Create temporary template for preview
            preview_template = FactoidTemplate(
                template_text=template_text,
                factoid_type=template.factoid_type,
                emoji=template.emoji,
                color_scheme=template.color_scheme,
            )
            preview_template.extract_referenced_fields()
            
            # Render preview
            rendered_text = engine.render_template(preview_template, context_data)
            
            # Validate references
            validation_errors = []
            for field_name in preview_template.referenced_fields:
                if field_name not in context_data:
                    validation_errors.append(f"Field '{field_name}' not found in context")
            
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log successful preview generation
            _log_api_activity(
                request, 
                'preview_template', 
                'preview_generated',
                extra_data={
                    'template_id': pk,
                    'council_slug': council.slug,
                    'council_name': council.name,
                    'year_slug': year_slug,
                    'counter_slug': counter_slug,
                    'template_text_length': len(template_text),
                    'referenced_fields_count': len(preview_template.referenced_fields),
                    'referenced_fields': preview_template.referenced_fields,
                    'validation_errors_count': len(validation_errors),
                    'context_data_keys_count': len(context_data),
                    'rendered_text_length': len(rendered_text),
                    'execution_time_seconds': execution_time,
                }
            )
            
            return Response({
                'success': True,
                'preview': {
                    'rendered_text': rendered_text,
                    'context_data': context_data,
                    'referenced_fields': preview_template.referenced_fields,
                    'validation_errors': validation_errors,
                    'council_name': council.name,
                    'year_label': str(year.year),
                }
            })
            
        except Exception as e:
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log preview generation error
            _log_api_activity(
                request, 
                'preview_template', 
                'preview_failed',
                error=e,
                extra_data={
                    'template_id': pk,
                    'council_slug': request.data.get('council_slug'),
                    'year_slug': request.data.get('year_slug', '2023-24'),
                    'template_text_length': len(request.data.get('template_text', '')),
                    'execution_time_seconds': execution_time,
                }
            )
            
            logger.error(f"Error generating preview: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'preview': {
                    'rendered_text': 'Preview error',
                    'validation_errors': [str(e)],
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def validate_template(self, request, pk=None):
        """
        Validate template syntax and field references
        """
        start_time = timezone.now()
        
        try:
            template = self.get_object()
            original_text = template.template_text
            
            # Update template text if provided
            if 'template_text' in request.data:
                template.template_text = request.data['template_text']
                template.extract_referenced_fields()
            
            # Run validation
            is_valid = template.validate_template()
            
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log successful validation
            _log_api_activity(
                request, 
                'validate_template', 
                'validation_completed',
                extra_data={
                    'template_id': pk,
                    'is_valid': is_valid,
                    'referenced_fields_count': len(template.referenced_fields),
                    'referenced_fields': template.referenced_fields,
                    'validation_errors_count': len(template.validation_errors),
                    'validation_errors': template.validation_errors,
                    'template_text_changed': request.data.get('template_text') != original_text,
                    'template_text_length': len(template.template_text),
                    'execution_time_seconds': execution_time,
                }
            )
            
            return Response({
                'success': True,
                'is_valid': is_valid,
                'referenced_fields': template.referenced_fields,
                'validation_errors': template.validation_errors,
            })
            
        except Exception as e:
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log validation error
            _log_api_activity(
                request, 
                'validate_template', 
                'validation_failed',
                error=e,
                extra_data={
                    'template_id': pk,
                    'template_text_length': len(request.data.get('template_text', '')),
                    'execution_time_seconds': execution_time,
                }
            )
            
            logger.error(f"Error validating template: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def sample_councils(self, request):
        """
        Get sample councils for preview testing
        """
        start_time = timezone.now()
        
        try:
            councils = Council.objects.filter(is_live=True)[:10]
            
            council_data = []
            for council in councils:
                council_data.append({
                    'slug': council.slug,
                    'name': council.name,
                    'type': council.council_type.name if council.council_type else 'Unknown',
                })
            
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log successful sample councils retrieval
            _log_api_activity(
                request, 
                'sample_councils', 
                'councils_retrieved',
                extra_data={
                    'councils_count': len(council_data),
                    'execution_time_seconds': execution_time,
                }
            )
            
            return Response({
                'success': True,
                'councils': council_data,
            })
            
        except Exception as e:
            execution_time = (timezone.now() - start_time).total_seconds()
            
            # Log sample councils error
            _log_api_activity(
                request, 
                'sample_councils', 
                'councils_retrieval_failed',
                error=e,
                extra_data={
                    'execution_time_seconds': execution_time,
                }
            )
            
            logger.error(f"Error getting sample councils: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@method_decorator(csrf_exempt)
def realtime_field_search(request):
    """
    Real-time field search for autocomplete
    """
    start_time = timezone.now()
    
    if request.method != 'GET':
        _log_api_activity(
            request, 
            'realtime_field_search', 
            'method_not_allowed',
            extra_data={'method_used': request.method}
        )
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 50)
        
        if len(query) < 2:
            execution_time = (timezone.now() - start_time).total_seconds()
            _log_api_activity(
                request, 
                'realtime_field_search', 
                'query_too_short',
                extra_data={
                    'query': query,
                    'query_length': len(query),
                    'execution_time_seconds': execution_time,
                }
            )
            return JsonResponse({
                'success': True,
                'fields': [],
                'message': 'Enter at least 2 characters to search'
            })
        
        # Search fields by name or slug
        fields = DataField.objects.filter(
            Q(name__icontains=query) | 
            Q(slug__icontains=query) |
            Q(explanation__icontains=query)
        )[:limit]
        
        field_results = []
        for field in fields:
            field_results.append({
                'id': field.id,
                'name': field.name,
                'variable_name': field.slug,
                'description': field.explanation[:100],
                'category': field.category,
                'data_type': field.content_type,
            })
        
        execution_time = (timezone.now() - start_time).total_seconds()
        
        # Log successful field search
        _log_api_activity(
            request, 
            'realtime_field_search', 
            'search_completed',
            extra_data={
                'query': query,
                'query_length': len(query),
                'limit': limit,
                'results_count': len(field_results),
                'execution_time_seconds': execution_time,
            }
        )
        
        return JsonResponse({
            'success': True,
            'fields': field_results,
            'total': len(field_results),
        })
        
    except Exception as e:
        execution_time = (timezone.now() - start_time).total_seconds()
        
        # Log field search error
        _log_api_activity(
            request, 
            'realtime_field_search', 
            'search_failed',
            error=e,
            extra_data={
                'query': request.GET.get('q', ''),
                'limit': request.GET.get('limit', 20),
                'execution_time_seconds': execution_time,
            }
        )
        
        logger.error(f"Error in realtime field search: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def quick_template_validation(request):
    """
    Quick template validation for real-time feedback
    """
    start_time = timezone.now()
    
    if request.method != 'POST':
        _log_api_activity(
            request, 
            'quick_template_validation', 
            'method_not_allowed',
            extra_data={'method_used': request.method}
        )
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        template_text = data.get('template_text', '')
        
        if not template_text:
            execution_time = (timezone.now() - start_time).total_seconds()
            _log_api_activity(
                request, 
                'quick_template_validation', 
                'empty_template',
                extra_data={
                    'execution_time_seconds': execution_time,
                }
            )
            return JsonResponse({
                'success': True,
                'is_valid': False,
                'errors': ['Template text is required']
            })
        
        # Create temporary template for validation
        temp_template = FactoidTemplate(template_text=template_text)
        temp_template.extract_referenced_fields()
        is_valid = temp_template.validate_template()
        
        execution_time = (timezone.now() - start_time).total_seconds()
        
        # Log successful quick validation
        _log_api_activity(
            request, 
            'quick_template_validation', 
            'validation_completed',
            extra_data={
                'template_text_length': len(template_text),
                'is_valid': is_valid,
                'referenced_fields_count': len(temp_template.referenced_fields),
                'referenced_fields': temp_template.referenced_fields,
                'validation_errors_count': len(temp_template.validation_errors),
                'validation_errors': temp_template.validation_errors,
                'execution_time_seconds': execution_time,
            }
        )
        
        return JsonResponse({
            'success': True,
            'is_valid': is_valid,
            'referenced_fields': temp_template.referenced_fields,
            'validation_errors': temp_template.validation_errors,
        })
        
    except json.JSONDecodeError as e:
        execution_time = (timezone.now() - start_time).total_seconds()
        _log_api_activity(
            request, 
            'quick_template_validation', 
            'json_decode_error',
            error=e,
            extra_data={
                'execution_time_seconds': execution_time,
                'request_body_length': len(request.body) if request.body else 0,
            }
        )
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        execution_time = (timezone.now() - start_time).total_seconds()
        
        # Log quick validation error
        _log_api_activity(
            request, 
            'quick_template_validation', 
            'validation_failed',
            error=e,
            extra_data={
                'execution_time_seconds': execution_time,
                'request_body_length': len(request.body) if request.body else 0,
            }
        )
        
        logger.error(f"Error in quick validation: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def quick_template_preview(request):
    """
    Quick template preview for real-time feedback without requiring existing template
    """
    start_time = timezone.now()
    
    if request.method != 'POST':
        _log_api_activity(
            request, 
            'quick_template_preview', 
            'method_not_allowed',
            extra_data={'method_used': request.method}
        )
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        template_text = data.get('template_text', '')
        
        if not template_text:
            execution_time = (timezone.now() - start_time).total_seconds()
            _log_api_activity(
                request, 
                'quick_template_preview', 
                'empty_template',
                extra_data={
                    'execution_time_seconds': execution_time,
                }
            )
            return JsonResponse({
                'success': False,
                'error': 'Template text is required'
            })
        
        # Get sample council and year for preview
        council_slug = data.get('council_slug')
        year_slug = data.get('year_slug', '2023-24')
        counter_slug = data.get('counter_slug')
        
        # Use provided council or default to first available
        if council_slug:
            council = Council.objects.filter(slug=council_slug).first()
        else:
            council = Council.objects.filter(is_live=True).first()
        
        if not council:
            execution_time = (timezone.now() - start_time).total_seconds()
            _log_api_activity(
                request, 
                'quick_template_preview', 
                'no_council_available',
                extra_data={
                    'council_slug_requested': council_slug,
                    'year_slug': year_slug,
                    'execution_time_seconds': execution_time,
                }
            )
            return JsonResponse({
                'success': False,
                'error': 'No council available for preview'
            }, status=400)
        
        # Get or create year
        year_parts = year_slug.split('-')
        if len(year_parts) == 2:
            start_year = int(year_parts[0])
        else:
            start_year = int(year_slug)
        
        year, _ = FinancialYear.objects.get_or_create(
            year=start_year,
            defaults={'year': start_year}
        )
        
        # Get counter if specified
        counter = None
        if counter_slug:
            counter = CounterDefinition.objects.filter(slug=counter_slug).first()
        
        # Generate preview using factoid engine
        engine = FactoidEngine()
        context_data = engine.build_context_data(council, year, counter)
        
        # Create temporary template for preview
        preview_template = FactoidTemplate(
            template_text=template_text,
            factoid_type='context',
            emoji='📊',
            color_scheme='blue',
        )
        preview_template.extract_referenced_fields()
        
        # Render preview
        rendered_text = engine.render_template(preview_template, context_data)
        
        # Validate references
        validation_errors = []
        for field_name in preview_template.referenced_fields:
            if field_name not in context_data:
                validation_errors.append(f"Field '{field_name}' not found in context")
        
        execution_time = (timezone.now() - start_time).total_seconds()
        
        # Log successful quick preview
        _log_api_activity(
            request, 
            'quick_template_preview', 
            'preview_generated',
            extra_data={
                'template_text_length': len(template_text),
                'council_slug': council.slug,
                'council_name': council.name,
                'year_slug': year_slug,
                'counter_slug': counter_slug,
                'referenced_fields_count': len(preview_template.referenced_fields),
                'referenced_fields': preview_template.referenced_fields,
                'validation_errors_count': len(validation_errors),
                'context_data_keys_count': len(context_data),
                'rendered_text_length': len(rendered_text),
                'execution_time_seconds': execution_time,
            }
        )
        
        return JsonResponse({
            'success': True,
            'preview': {
                'rendered_text': rendered_text,
                'context_data': context_data,
                'referenced_fields': preview_template.referenced_fields,
                'validation_errors': validation_errors,
                'council_name': council.name,
                'year_label': str(year.year),
            }
        })
        
    except json.JSONDecodeError as e:
        execution_time = (timezone.now() - start_time).total_seconds()
        _log_api_activity(
            request, 
            'quick_template_preview', 
            'json_decode_error',
            error=e,
            extra_data={
                'execution_time_seconds': execution_time,
                'request_body_length': len(request.body) if request.body else 0,
            }
        )
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        execution_time = (timezone.now() - start_time).total_seconds()
        
        # Log quick preview error
        _log_api_activity(
            request, 
            'quick_template_preview', 
            'preview_failed',
            error=e,
            extra_data={
                'template_text_length': len(data.get('template_text', '')) if 'data' in locals() else 0,
                'council_slug': data.get('council_slug') if 'data' in locals() else None,
                'year_slug': data.get('year_slug', '2023-24') if 'data' in locals() else '2023-24',
                'execution_time_seconds': execution_time,
            }
        )
        
        logger.error(f"Error in quick preview: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
            'preview': {
                'rendered_text': 'Preview error',
                'validation_errors': [str(e)],
            }
        }, status=500)
