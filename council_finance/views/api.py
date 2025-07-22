"""
API views for Council Finance Counters.
This module handles all API endpoints and AJAX requests.
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db.models import Q
import json

from council_finance.models import (
    Council, DataField, ActivityLog, CounterDefinition, 
    FinancialYear, FactoidTemplate, FactoidPlaylist,
    CouncilAIAnalysis, AIAnalysisConfiguration
)
from council_finance.forms import DataFieldForm

# Import utility functions we'll need
from .general import log_activity, current_financial_year_label


def search_councils(request):
    """API endpoint to search councils by name."""
    query = request.GET.get('q', '')
    if len(query.strip()) < 2:
        return JsonResponse({'results': []})
    
    # Get councils with enhanced search including council type and nation
    councils = Council.objects.select_related('council_type', 'council_nation').filter(
        Q(name__icontains=query) | 
        Q(slug__icontains=query) |
        Q(council_type__name__icontains=query) |
        Q(council_nation__name__icontains=query)
    ).distinct()[:10]
    
    results = []
    for council in councils:
        results.append({
            'id': council.id,
            'name': council.name,
            'slug': council.slug,
            'type': council.council_type.name if council.council_type else 'Council',
            'region': council.council_nation.name if council.council_nation else 'Unknown region',
            'url': f'/councils/{council.slug}/',
        })
    
    return JsonResponse({'results': results})


def list_field_options(request, field_slug=None, slug=None):
    """API endpoint to get field options for a specific field."""
    # Use field_slug if provided, otherwise use slug for backward compatibility
    slug = field_slug or slug
    
    if not slug:
        return JsonResponse({'error': 'Field slug is required'}, status=400)
    
    try:
        field = get_object_or_404(DataField, slug=slug)
          # Get unique values for this field from both characteristics and financial figures
        from council_finance.models import CouncilCharacteristic, FinancialFigure
        
        characteristic_values = CouncilCharacteristic.objects.filter(
            field=field
        ).values_list('value', flat=True).distinct()
        
        financial_values = FinancialFigure.objects.filter(
            field=field
        ).values_list('value', flat=True).distinct()
        
        # Combine and filter out None/empty values
        all_values = list(characteristic_values) + [str(v) for v in financial_values if v is not None]
        options = sorted(list(set([v for v in all_values if v is not None and v != ''])))
        
        return JsonResponse({
            'field_name': field.name,
            'field_slug': field.slug,
            'options': options[:50]  # Limit to first 50 options
        })
        
    except DataField.DoesNotExist:
        return JsonResponse({'error': 'Field not found'}, status=404)


def field_info_api(request, field_slug):
    """API endpoint to get detailed information about a field."""
    try:
        field = get_object_or_404(DataField, slug=field_slug)
        
        return JsonResponse({
            'name': field.name,
            'slug': field.slug,
            'description': field.description or '',
            'data_type': field.data_type,
            'unit': field.unit or '',
            'help_text': field.help_text or '',
        })
        
    except DataField.DoesNotExist:
        return JsonResponse({'error': 'Field not found'}, status=404)


def council_recent_activity_api(request, council_slug):
    """API endpoint to get recent activity for a council."""
    try:
        council = get_object_or_404(Council, slug=council_slug)
          # Get recent activity logs for this council
        activities = ActivityLog.objects.filter(
            related_council=council
        ).order_by('-created')[:10]
        
        activity_data = []
        for activity in activities:
            activity_data.append({
                'id': activity.id,
                'description': activity.description,
                'created_at': activity.created.isoformat(),
                'user': activity.user.username if activity.user else 'System',
            })
        
        return JsonResponse({
            'council': council.name,
            'activities': activity_data
        })
        
    except Council.DoesNotExist:
        return JsonResponse({'error': 'Council not found'}, status=404)


def field_recent_activity_api(request, council_slug, field_slug):
    """API endpoint to get recent activity for a specific field in a council."""
    try:
        council = get_object_or_404(Council, slug=council_slug)
        field = get_object_or_404(DataField, slug=field_slug)          # Get recent activity logs for this council and field
        activities = ActivityLog.objects.filter(
            related_council=council,
            field=field
        ).order_by('-created')[:10]
        
        activity_data = []
        for activity in activities:
            activity_data.append({
                'id': activity.id,
                'description': activity.description,
                'created_at': activity.created.isoformat(),
                'user': activity.user.username if activity.user else 'System',
                'old_value': activity.old_value,
                'new_value': activity.new_value,
            })
        
        return JsonResponse({
            'council': council.name,
            'field': field.name,
            'activities': activity_data
        })
        
    except (Council.DoesNotExist, DataField.DoesNotExist):
        return JsonResponse({'error': 'Council or field not found'}, status=404)


@login_required
def user_preferences_ajax(request):
    """Handle user preferences updates via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        preference_key = data.get('key')
        preference_value = data.get('value')
        
        if not preference_key:
            return JsonResponse({'error': 'Preference key is required'}, status=400)
        
        # Update user preferences
        profile, created = request.user.userprofile_set.get_or_create()
        
        # Store preference in profile (assuming we have a preferences JSONField)
        if not hasattr(profile, 'preferences'):
            profile.preferences = {}
        
        profile.preferences[preference_key] = preference_value
        profile.save()
        
        log_activity(
            request,
            activity=f"Updated preference: {preference_key}",
            details=f"New value: {preference_value}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Preference updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def factoid_data_api(request, counter_slug, council_slug, year_label):
    """API endpoint to get factoid data for a specific counter/council/year combination."""
    try:
        counter = get_object_or_404(CounterDefinition, slug=counter_slug)
        council = None
        if council_slug != 'all-councils':
            council = get_object_or_404(Council, slug=council_slug)
        
        # Convert URL-safe year format back to database format (e.g., "2023-24" -> "2023/24")
        actual_year_label = year_label.replace('-', '/')
        year = get_object_or_404(FinancialYear, label=actual_year_label)
        
        # Use the FactoidEngine to generate factoids
        from council_finance.factoid_engine import FactoidEngine
        engine = FactoidEngine()
        
        # Check for force refresh parameter (useful for development/debugging)
        force_refresh = request.GET.get('force_refresh', '').lower() == 'true'
        
        factoids = engine.generate_factoid_playlist(counter_slug, council_slug, actual_year_label, force_refresh=force_refresh)
        
        return JsonResponse({
            'success': True,
            'counter': {
                'name': counter.name,
                'slug': counter.slug,
            },
            'council': {
                'name': council.name if council else 'All Councils',
                'slug': council.slug if council else 'all-councils',
            } if council else {
                'name': 'All Councils',
                'slug': 'all-councils',
            },
            'year': {
                'label': year.label,
            },
            'factoids': factoids,
            'count': len(factoids)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def factoid_playlist_api(request, counter_slug):
    """API endpoint to get all factoid playlists for a specific counter."""
    try:
        counter = get_object_or_404(CounterDefinition, slug=counter_slug)
        
        playlists = FactoidPlaylist.objects.filter(
            counter=counter
        ).select_related('council', 'year').prefetch_related('factoid_templates')
        
        # Apply filters
        council_slug = request.GET.get('council')
        if council_slug:
            playlists = playlists.filter(council__slug=council_slug)
        
        year_label = request.GET.get('year')
        if year_label:
            playlists = playlists.filter(year__label=year_label)
        
        auto_generate_only = request.GET.get('auto_generate', '').lower() == 'true'
        if auto_generate_only:
            playlists = playlists.filter(auto_generate=True)
        
        # Serialize playlist data
        playlist_data = []
        for playlist in playlists:
            playlist_data.append({
                'id': playlist.id,
                'counter': {
                    'name': playlist.counter.name,
                    'slug': playlist.counter.slug,
                },
                'council': {
                    'name': playlist.council.name if playlist.council else 'All Councils',
                    'slug': playlist.council.slug if playlist.council else None,
                } if playlist.council else None,
                'year': {
                    'label': playlist.year.label,
                },
                'auto_generate': playlist.auto_generate,
                'computed_factoids': playlist.computed_factoids,
                'last_computed': playlist.last_computed.isoformat() if playlist.last_computed else None,
                'template_count': playlist.factoid_templates.count(),
            })
        
        return JsonResponse({
            'success': True,
            'counter': {
                'name': counter.name,
                'slug': counter.slug,
            },
            'playlists': playlist_data,
            'count': len(playlist_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_POST
@csrf_exempt
def regenerate_factoid_playlist_api(request, playlist_id):
    """API endpoint to regenerate a factoid playlist."""
    try:
        playlist = get_object_or_404(FactoidPlaylist, id=playlist_id)
        
        # Use the FactoidEngine to regenerate factoids
        from council_finance.factoid_engine import FactoidEngine
        engine = FactoidEngine()
        
        factoids = engine.generate_factoid_playlist(
            playlist.counter.slug,
            playlist.council.slug if playlist.council else None,
            playlist.year.label
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Playlist regenerated with {len(factoids)} factoids',
            'factoids': factoids,
            'count': len(factoids),
            'regenerated_at': playlist.last_computed.isoformat() if playlist.last_computed else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET  
def factoid_template_preview_api(request, template_slug):
    """API endpoint to preview a factoid template with sample data."""
    try:
        template = get_object_or_404(FactoidTemplate, slug=template_slug)
        
        # Get sample council and counter for preview
        sample_council = request.GET.get('council_slug')
        sample_counter = request.GET.get('counter_slug')
        sample_year = request.GET.get('year_label')
        
        if sample_council and sample_counter and sample_year:
            from council_finance.factoid_engine import FactoidEngine
            engine = FactoidEngine()
            
            # Get real data for preview
            counter_obj = CounterDefinition.objects.get(slug=sample_counter)
            council_obj = Council.objects.get(slug=sample_council)
            year_obj = FinancialYear.objects.get(label=sample_year)
            
            counter_data = engine._get_counter_data(counter_obj, council_obj, year_obj)
            previous_data = engine._get_previous_year_data(counter_obj, council_obj, year_obj)
            
            factoid = engine._generate_factoid_from_template(template, counter_data, previous_data, council_obj)
        else:
            # Use mock data for preview
            factoid = {
                'type': template.factoid_type,
                'text': template.template_text.replace('{{value}}', '£1,234,567').replace('{{council_name}}', 'Sample Council'),
                'emoji': template.emoji or '📊',
                'color': template.color_scheme,
                'animation_duration': template.animation_duration,
                'flip_animation': template.flip_animation,
                'priority': template.priority,
                'template_id': template.id,
                'is_relevant': True
            }
        
        return JsonResponse({
            'success': True,
            'template': {
                'name': template.name,
                'slug': template.slug,
                'type': template.factoid_type,
                'template_text': template.template_text,
            },
            'preview': factoid
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def council_ai_analysis_api(request, council_slug, year_label):
    """API endpoint to get AI analysis for a council/year combination."""
    try:
        council = get_object_or_404(Council, slug=council_slug)
        
        # Convert URL-safe year format back to database format if needed
        actual_year_label = year_label.replace('-', '/')
        year = get_object_or_404(FinancialYear, label=actual_year_label)
        
        # Check for force refresh parameter
        force_refresh = request.GET.get('force_refresh', '').lower() == 'true'
        
        # Get AI analysis configuration (can be specified via parameter)
        config_id = request.GET.get('config_id')
        if config_id:
            try:
                configuration = AIAnalysisConfiguration.objects.get(
                    id=config_id, is_active=True
                )
            except AIAnalysisConfiguration.DoesNotExist:
                configuration = None
        else:
            configuration = AIAnalysisConfiguration.objects.filter(
                is_active=True, is_default=True
            ).first()
        
        if not configuration:
            return JsonResponse({
                'success': False,
                'error': 'No active AI analysis configuration found'
            }, status=404)
        
        # Import and use AI service
        from council_finance.services.ai_analysis_service import AIAnalysisService
        ai_service = AIAnalysisService()
        
        # Check if AI service is properly configured
        if not ai_service.openai_client:
            return JsonResponse({
                'success': False,
                'error': 'AI analysis service is not configured. Please contact administrator to set up OpenAI API key.'
            }, status=503)
        
        # Get or create analysis
        analysis = ai_service.get_or_create_analysis(
            council=council,
            year=year,
            configuration=configuration,
            force_refresh=force_refresh
        )
        
        if not analysis:
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate or retrieve AI analysis'
            }, status=500)
        
        # Prepare response data
        response_data = {
            'success': True,
            'council': {
                'name': council.name,
                'slug': council.slug,
                'type': council.council_type.name if council.council_type else None
            },
            'year': {
                'label': year.label,
            },
            'configuration': {
                'id': configuration.id,
                'name': configuration.name,
                'model': configuration.model.name
            },
            'analysis': {
                'id': analysis.id,
                'status': analysis.status,
                'summary': analysis.analysis_summary,
                'full_text': analysis.analysis_text,
                'key_insights': analysis.get_formatted_insights(),
                'risk_factors': analysis.risk_factors,
                'recommendations': analysis.recommendations,
                'created': analysis.created.isoformat(),
                'expires_at': analysis.expires_at.isoformat() if analysis.expires_at else None,
                'is_expired': analysis.is_expired,
            },
            'meta': {
                'tokens_used': analysis.tokens_used,
                'processing_time_ms': analysis.processing_time_ms,
                'cost_estimate': float(analysis.cost_estimate) if analysis.cost_estimate else None
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def ai_analysis_status_api(request, analysis_id):
    """API endpoint to check the status of a specific AI analysis."""
    try:
        analysis = get_object_or_404(CouncilAIAnalysis, id=analysis_id)
        
        return JsonResponse({
            'success': True,
            'analysis': {
                'id': analysis.id,
                'status': analysis.status,
                'council': analysis.council.name,
                'year': analysis.year.label,
                'created': analysis.created.isoformat(),
                'expires_at': analysis.expires_at.isoformat() if analysis.expires_at else None,
                'is_expired': analysis.is_expired,
                'error_message': analysis.error_message,
                'processing_time_ms': analysis.processing_time_ms
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def provider_models_api(request, provider_id):
    """API endpoint to fetch available models from an AI provider."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        from council_finance.models.ai_analysis import AIProvider
        
        provider = get_object_or_404(AIProvider, id=provider_id)
        models = []
        
        # Handle different providers
        if provider.slug == 'openai':
            models = _fetch_openai_models()
        elif provider.slug == 'anthropic':
            models = _fetch_anthropic_models()
        elif provider.slug == 'google':
            models = _fetch_google_models()
        else:
            # Return empty list for unsupported providers
            models = []
        
        return JsonResponse({
            'success': True,
            'provider': provider.name,
            'models': models
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _fetch_openai_models():
    """Fetch available models from OpenAI API."""
    try:
        from openai import OpenAI
        import os
        
        # Check if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return [{
                'id': 'gpt-4-turbo',
                'name': 'GPT-4 Turbo (API key not configured)',
                'available': False
            }]
        
        client = OpenAI(api_key=api_key)
        response = client.models.list()
        
        # Filter for relevant models and sort by name
        relevant_models = []
        model_names = {
            'gpt-4': 'GPT-4',
            'gpt-4-turbo': 'GPT-4 Turbo',
            'gpt-4-turbo-preview': 'GPT-4 Turbo Preview',
            'gpt-4o': 'GPT-4o',
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo',
            'gpt-3.5-turbo-16k': 'GPT-3.5 Turbo 16K'
        }
        
        for model in response.data:
            if model.id in model_names:
                relevant_models.append({
                    'id': model.id,
                    'name': model_names[model.id],
                    'available': True
                })
        
        # Sort by preference order
        model_order = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
        relevant_models.sort(key=lambda x: model_order.index(x['id']) if x['id'] in model_order else 999)
        
        return relevant_models
        
    except ImportError:
        return [{
            'id': 'gpt-4-turbo',
            'name': 'GPT-4 Turbo (OpenAI library not installed)',
            'available': False
        }]
    except Exception as e:
        return [{
            'id': 'error',
            'name': f'Error fetching models: {str(e)}',
            'available': False
        }]


def _fetch_anthropic_models():
    """Fetch available models from Anthropic (static list since they don't have a models API)."""
    return [
        {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet (Latest)', 'available': True},
        {'id': 'claude-3-5-sonnet-20240620', 'name': 'Claude 3.5 Sonnet (June)', 'available': True},
        {'id': 'claude-3-opus-20240229', 'name': 'Claude 3 Opus', 'available': True},
        {'id': 'claude-3-sonnet-20240229', 'name': 'Claude 3 Sonnet', 'available': True},
        {'id': 'claude-3-haiku-20240307', 'name': 'Claude 3 Haiku', 'available': True}
    ]


def _fetch_google_models():
    """Fetch available models from Google (static list)."""
    return [
        {'id': 'gemini-pro', 'name': 'Gemini Pro', 'available': True},
        {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro', 'available': True},
        {'id': 'gemini-1.5-flash', 'name': 'Gemini 1.5 Flash', 'available': True}
    ]
