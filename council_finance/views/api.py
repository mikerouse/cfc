"""
API views for Council Finance Counters.
This module handles all API endpoints and AJAX requests.
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db.models import Q
import json
import logging

logger = logging.getLogger(__name__)

from council_finance.models import (
    Council, DataField, ActivityLog, CounterDefinition, 
    FinancialYear
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
        # Get latest population if available
        population = None
        if hasattr(council, 'latest_population') and council.latest_population:
            population = council.latest_population
        
        results.append({
            'id': council.id,
            'name': council.name,
            'slug': council.slug,
            'type': council.council_type.name if council.council_type else 'Council',
            'region': council.council_nation.name if council.council_nation else 'Unknown region',
            'population': population,
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
            'description': field.explanation or '',
            'content_type': field.content_type,
            'category': field.category,
            'required': field.required,
        })
        
    except DataField.DoesNotExist:
        return JsonResponse({'error': 'Field not found'}, status=404)


@require_http_methods(['POST'])
def validate_url_api(request):
    """API endpoint to validate URLs for security and accessibility."""
    import json
    import requests
    from urllib.parse import urlparse
    from django.conf import settings
    from council_finance.models import DataField
    
    try:
        data = json.loads(request.body)
        url = data.get('url', '').strip()
        field_slug = data.get('field_slug', '')
        
        if not url:
            return JsonResponse({
                'valid': False,
                'message': 'URL is required'
            })
        
        # Get field-specific validation settings
        field_settings = {}
        if field_slug:
            try:
                field = DataField.objects.get(slug=field_slug)
                field_settings = {
                    'validation_enabled': field.url_validation_enabled,
                    'allow_redirects': field.url_allow_redirects,
                    'require_https': field.url_require_https,
                    'blocked_domains': [d.strip().lower() for d in field.url_blocked_domains.split(',') if d.strip()],
                    'allowed_domains': [d.strip().lower() for d in field.url_allowed_domains.split(',') if d.strip()]
                }
            except DataField.DoesNotExist:
                pass
        
        # Use defaults if no field-specific settings
        validation_enabled = field_settings.get('validation_enabled', True)
        allow_redirects = field_settings.get('allow_redirects', True)
        require_https = field_settings.get('require_https', False)
        blocked_domains = field_settings.get('blocked_domains', [])
        allowed_domains = field_settings.get('allowed_domains', [])
        
        # Skip validation if disabled for this field
        if not validation_enabled:
            return JsonResponse({
                'valid': True,
                'message': 'URL validation is disabled for this field'
            })
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            return JsonResponse({
                'valid': False,
                'message': 'Invalid URL format'
            })
        
        # Protocol validation
        allowed_protocols = ['https'] if require_https else ['http', 'https']
        if parsed.scheme not in allowed_protocols:
            message = 'Only HTTPS URLs are allowed' if require_https else 'Only HTTP and HTTPS URLs are allowed'
            return JsonResponse({
                'valid': False,
                'message': message
            })
        
        # Domain validation
        domain = parsed.hostname.lower() if parsed.hostname else ''
        
        # Check allowed domains first (if specified)
        if allowed_domains:
            if not any(allowed_domain in domain for allowed_domain in allowed_domains):
                return JsonResponse({
                    'valid': False,
                    'message': f'URLs are only allowed from these domains: {", ".join(allowed_domains)}'
                })
        
        # Default blocked domains (merged with field-specific ones)
        default_blocked = [
            'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly',
            'localhost', '127.0.0.1', '0.0.0.0', '::1'
        ]
        all_blocked_domains = list(set(default_blocked + blocked_domains))
        
        if any(blocked in domain for blocked in all_blocked_domains):
            return JsonResponse({
                'valid': False,
                'message': 'This domain is blocked for security reasons'
            })
        
        # Check for private IP ranges
        import ipaddress
        try:
            ip = ipaddress.ip_address(domain)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return JsonResponse({
                    'valid': False,
                    'message': 'Private, loopback, and link-local IP addresses are not allowed'
                })
        except ValueError:
            # Not an IP address, that's fine
            pass
        
        # Basic connectivity test with timeout
        try:
            response = requests.head(
                url, 
                timeout=5,
                allow_redirects=True,
                headers={'User-Agent': 'Council Finance Counters URL Validator'}
            )
            
            if response.status_code >= 400:
                return JsonResponse({
                    'valid': False,
                    'message': f'URL returned error status: {response.status_code}'
                })
            
            # Check content type for reasonable expectations
            content_type = response.headers.get('content-type', '').lower()
            if 'application/octet-stream' in content_type and not any(ext in url.lower() for ext in ['.pdf', '.doc', '.docx']):
                return JsonResponse({
                    'valid': False,
                    'message': 'URL appears to serve binary content which may not be appropriate for a financial statement link'
                })
            
            return JsonResponse({
                'valid': True,
                'message': 'URL is valid and accessible',
                'status_code': response.status_code,
                'content_type': content_type
            })
            
        except requests.RequestException as e:
            return JsonResponse({
                'valid': False,
                'message': f'URL is not accessible: {str(e)}'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': f'Validation error: {str(e)}'
        }, status=500)


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


# Legacy AI analysis API removed - now using AI factoids instead
# DEPRECATED: council_ai_analysis_api function removed - replaced by AI factoids system


# DEPRECATED: ai_analysis_status_api function removed - replaced by AI factoids system


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


@require_POST
def emergency_cache_warming(request):
    """
    Emergency API endpoint to detect and fix £0 counters on the home page.
    Triggered automatically by JavaScript when £0 counters are detected.
    Also sends email alerts to administrators.
    
    Security measures:
    - Rate limiting per IP
    - Request validation and sanitization  
    - Limited response data
    - Distributed lock to prevent concurrent execution
    """
    try:
        # Import required modules
        from council_finance.agents.site_totals_agent import SiteTotalsAgent
        from council_finance.models import SiteCounter, GroupCounter
        from council_finance.utils.email_alerts import email_alert_service
        from django.core.cache import cache
        import json
        import time
        import hashlib
        
        # Security: Get client IP for rate limiting
        def get_client_ip(request):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[0].strip()
            return request.META.get('REMOTE_ADDR', 'unknown')
        
        client_ip = get_client_ip(request)
        
        # Security: Rate limiting (max 3 requests per 5 minutes per IP)
        rate_limit_key = f"emergency_cache_warming_rate_limit:{hashlib.md5(client_ip.encode()).hexdigest()}"
        current_requests = cache.get(rate_limit_key, 0)
        
        if current_requests >= 3:
            return JsonResponse({
                'success': False,
                'error': 'Rate limit exceeded. Please wait before trying again.',
                'retry_after': 300  # 5 minutes
            }, status=429)
        
        # Increment rate limit counter
        cache.set(rate_limit_key, current_requests + 1, 300)  # 5 minutes TTL
        
        # Security: Distributed lock to prevent concurrent warming
        lock_key = "emergency_cache_warming_lock"
        if cache.get(lock_key):
            return JsonResponse({
                'success': False,
                'error': 'Cache warming already in progress. Please wait.',
                'message': 'Another emergency warming operation is currently running.'
            }, status=409)
        
        # Set lock with 60 second timeout
        cache.set(lock_key, True, 60)
        
        # Security: Parse and validate request data
        try:
            data = json.loads(request.body)
            
            # Validate and sanitize zero_counters data
            raw_zero_counters = data.get('zero_counters', [])
            zero_counters = []
            
            # Security: Limit to max 20 reported counters to prevent abuse
            if len(raw_zero_counters) > 20:
                return JsonResponse({
                    'success': False,
                    'error': 'Too many counters reported. Maximum 20 allowed.'
                }, status=400)
            
            # Validate each counter entry
            for counter_data in raw_zero_counters[:20]:  # Hard limit
                if isinstance(counter_data, dict):
                    # Sanitize counter data - only keep safe fields
                    sanitized = {
                        'name': str(counter_data.get('name', 'Unknown'))[:100],  # Limit length
                        'index': int(counter_data.get('index', 0)) if str(counter_data.get('index', 0)).isdigit() else 0,
                        'displayText': str(counter_data.get('displayText', ''))[:50]  # Limit length
                    }
                    zero_counters.append(sanitized)
            
            # Validate timestamp if provided
            timestamp = data.get('timestamp')
            if timestamp:
                try:
                    from datetime import datetime
                    parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    # Security: Reject timestamps more than 1 hour in future or past
                    time_diff = abs((datetime.now().timestamp() - parsed_time.timestamp()))
                    if time_diff > 3600:  # 1 hour
                        return JsonResponse({
                            'success': False,
                            'error': 'Invalid timestamp provided.'
                        }, status=400)
                except (ValueError, AttributeError):
                    pass  # Ignore invalid timestamps
            
            user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]  # Limit length
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data provided.'
            }, status=400)
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request data format.'
            }, status=400)
        
        # Log the detection
        print(f"EMERGENCY: £0 counters detected on home page from {client_ip}")
        print(f"Zero counters reported: {zero_counters}")
        
        # Get current cache status before warming
        site_counters = list(SiteCounter.objects.all())
        group_counters = list(GroupCounter.objects.all())
        all_counters = site_counters + group_counters
        
        cache_status_before = {}
        for counter in all_counters:
            year_label = counter.year.label if counter.year else "all"
            cache_key = f"counter_total:{counter.slug}:{year_label}"
            cached_value = cache.get(cache_key)
            cache_status_before[counter.slug] = {
                'cached': cached_value is not None,
                'value': cached_value,
                'counter_name': counter.name
            }
        
        # Run emergency cache warming
        start_time = time.time()
        agent = SiteTotalsAgent()
        agent.run()
        warming_duration = time.time() - start_time
        
        # Check cache status after warming
        cache_status_after = {}
        fixed_counters = []
        for counter in all_counters:
            year_label = counter.year.label if counter.year else "all"
            cache_key = f"counter_total:{counter.slug}:{year_label}"
            cached_value = cache.get(cache_key)
            cache_status_after[counter.slug] = {
                'cached': cached_value is not None,
                'value': cached_value,
                'counter_name': counter.name
            }
            
            # Check if this counter was fixed
            before = cache_status_before.get(counter.slug, {})
            after = cache_status_after.get(counter.slug, {})
            
            was_zero_or_missing = (
                not before.get('cached') or 
                before.get('value') == 0 or 
                before.get('value') is None
            )
            is_now_nonzero = (
                after.get('cached') and 
                after.get('value') is not None and 
                after.get('value') != 0
            )
            
            if was_zero_or_missing and is_now_nonzero:
                fixed_counters.append({
                    'slug': counter.slug,
                    'name': counter.name,
                    'before_value': before.get('value'),
                    'after_value': after.get('value')
                })
        
        # Log to Event Viewer
        from event_viewer.models import SystemEvent
        
        # Determine severity based on number of zero counters
        if len(zero_counters) > 5:
            level = 'error'
        elif len(zero_counters) > 2:
            level = 'warning'
        else:
            level = 'info'
        
        # Create SystemEvent for monitoring
        SystemEvent.objects.create(
            source='api',
            level=level,
            category='data_quality',
            title='£0 Counters Detected on Home Page',
            message=f"Detected {len(zero_counters)} counters showing £0. Fixed {len(fixed_counters)} counters after cache warming.",
            user=request.user if request.user.is_authenticated else None,
            request_path=request.path,
            request_method=request.method,
            details={
                'zero_counters_reported': zero_counters,
                'fixed_counters': fixed_counters,
                'total_counters_checked': len(all_counters),
                'cache_warming_duration': warming_duration,
                'client_ip': client_ip,
                'user_agent': user_agent,
                'counters_before_after': {
                    counter['slug']: {
                        'before': counter['before_value'],
                        'after': counter['after_value']
                    } for counter in fixed_counters
                }
            },
            tags=['zero-counter-detection', 'cache-warming', 'data-quality'],
            fingerprint=f'zero_counters_home_page_{len(zero_counters)}'
        )
        
        # Send email alert to administrators
        alert_context = {
            'alert_type': 'Emergency £0 Counter Detection',
            'zero_counters_reported': zero_counters,
            'total_counters_checked': len(all_counters),
            'fixed_counters': fixed_counters,
            'cache_warming_duration': f"{warming_duration:.2f} seconds",
            'request_ip': client_ip,
            'user_agent': user_agent,
            'cache_status_before': cache_status_before,
            'cache_status_after': cache_status_after,
            'suggested_action': 'Monitor for recurring £0 counter issues. Check SiteTotalsAgent performance.'
        }
        
        exception = Exception(
            f"£0 counters detected on home page. Fixed {len(fixed_counters)} counters. "
            f"Zero counters reported: {zero_counters}"
        )
        
        email_sent = email_alert_service.send_error_alert(
            exception, 
            request, 
            alert_context
        )
        
        # Security: Prepare minimal response data (don't expose internal details)
        success_response = {
            'success': True,
            'message': 'Emergency cache warming completed',
            'fixed_counters': len(fixed_counters),
            'warming_duration': f"{warming_duration:.1f}s",
            'timestamp': time.time()
        }
        
        # Release the lock
        cache.delete(lock_key)
        
        return JsonResponse(success_response)
        
    except Exception as e:
        # Security: Release lock in case of error
        try:
            cache.delete(lock_key)
        except:
            pass
        
        # Log the error (don't expose internal details)
        print(f"ERROR in emergency cache warming: {e}")
        
        # Try to send error alert
        try:
            error_context = {
                'alert_type': 'Emergency Cache Warming Failure',
                'client_ip': client_ip,
                'user_agent': user_agent if 'user_agent' in locals() else 'Unknown'
            }
            email_alert_service.send_error_alert(e, request, error_context)
        except:
            pass  # Don't let email failure prevent error response
        
        # Security: Return generic error message
        return JsonResponse({
            'success': False,
            'error': 'Internal server error during cache warming',
            'message': 'Please try again or contact support if the issue persists'
        }, status=500)


