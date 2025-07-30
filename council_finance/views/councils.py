"""
Council-specific views for Council Finance Counters.
This module handles council pages, details, counters, and related functionality.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
import json
import urllib.parse
from django.http import JsonResponse
from uuid import uuid4

from council_finance.models import (
    Council, FinancialYear, 
    UserProfile, ActivityLog, CounterDefinition, SiteCounter,
    CouncilCounter, SiteSetting, DataField,
    CouncilCharacteristic, FinancialFigure, FinancialFigureHistory,
    CouncilCharacteristicHistory, CouncilFollow, Contribution,
    CouncilType, CouncilNation
)
from council_finance.agents.counter_agent import CounterAgent

# Import utility functions we'll need
from .general import log_activity, current_financial_year_label


def council_list(request):
    """Enhanced list of all councils with filtering, sorting, and quick actions."""
    # Get parameters
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name')
    sort_order = request.GET.get('order', 'asc')
    council_type_filter = request.GET.get('type', '')
    nation_filter = request.GET.get('nation', '')
    try:
        page_size = int(request.GET.get('per_page', '24'))
        if page_size not in [12, 24, 48, 96]:
            page_size = 24
    except (ValueError, TypeError):
        page_size = 24
    
    # Base queryset - start simple
    councils = Council.objects.all()
    
    # Apply search filter
    if search_query:
        councils = councils.filter(
            Q(name__icontains=search_query) |
            Q(slug__icontains=search_query)
        )
    
    # Apply basic ordering
    councils = councils.order_by('name')
    
    # Get totals before pagination
    total_councils = councils.count()
    
    # Paginate results
    paginator = Paginator(councils, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get filter options (empty for now)
    council_types = []
    nations = []
    
    # Simple council data
    enhanced_councils = []
    for council in page_obj:
        enhanced_councils.append({
            'council': council,
            'population': getattr(council, 'latest_population', None),
            'debt_total': 0,
            'completion_percentage': 50,
            'is_following': False,
        })
    
    # Page size options
    page_size_options = [12, 24, 48, 96]
    
    context = {
        'councils': enhanced_councils,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'council_type_filter': council_type_filter,
        'nation_filter': nation_filter,
        'page_size': page_size,
        'page_size_options': page_size_options,
        'council_types': council_types,
        'nations': nations,
        'total_councils': total_councils,
        'start_index': page_obj.start_index() if page_obj else 0,
        'end_index': page_obj.end_index() if page_obj else 0,
        'following_councils': set(),
    }
    
    return render(request, 'council_finance/council_list.html', context)


def council_detail(request, slug):
    """Display detailed information about a council."""
    council = get_object_or_404(Council, slug=slug)
    
    # Handle share link parameters
    share_data = None
    share_id = request.GET.get('share')
    if share_id and 'share_links' in request.session:
        share_data = request.session['share_links'].get(share_id)
    
    # Get the current financial year
    current_year = current_financial_year_label()
    
    # Get financial data for the council
    try:
        council_year = FinancialYear.objects.get(
            label=current_year
        )
    except FinancialYear.DoesNotExist:
        council_year = None
      # Get all available financial years for the dropdown
    years = FinancialYear.objects.all().order_by('-label')
    selected_year = council_year or (years.first() if years.exists() else None)
    
    # If no financial year exists, create a default one
    if not years.exists():
        default_year = FinancialYear.objects.create(
            label=current_year
        )
        years = [default_year]
        selected_year = default_year
        council_year = default_year
    
    # Annotate display labels so the template can show the current year as
    # "Current Year to Date" without storing a separate field in the DB.
    current_label = current_financial_year_label()
    for y in years:
        y.display = "Current Year to Date" if y.label == current_label else y.label
      # Get recent council updates (combination of characteristic and financial changes)
    recent_characteristic_changes = CouncilCharacteristicHistory.objects.filter(
        council=council
    ).order_by('-changed_at')[:5]
    
    recent_financial_changes = FinancialFigureHistory.objects.filter(
        council=council
    ).order_by('-changed_at')[:5]
    
    # Combine and sort by most recent
    recent_submissions = list(recent_characteristic_changes) + list(recent_financial_changes)
    recent_submissions.sort(key=lambda x: getattr(x, 'changed_at', getattr(x, 'created', timezone.now())), reverse=True)
    recent_submissions = recent_submissions[:10]
    
    # Get counters for this council
    counter_definitions = CounterDefinition.objects.filter(
        show_by_default=True
    ).order_by('name')
    
    # Calculate counter values using the CounterAgent
    counters = []
    if counter_definitions:
        counter_agent = CounterAgent()
        
        # Get all counter results for this council and year
        try:
            if council_year:
                counter_results = counter_agent.run(
                    council_slug=council.slug,
                    year_label=current_year
                )
            else:
                counter_results = {}
            
            # Create combined data structure for template
            for counter_def in counter_definitions:
                counter_data = {
                    'counter': counter_def,
                    'value': None,
                    'formatted': 'No data',
                    'error': None,
                    'factoids': []
                }
                
                # Get the calculated result if available
                if counter_def.slug in counter_results:
                    result = counter_results[counter_def.slug]
                    if isinstance(result, dict):
                        counter_data.update(result)
                    else:
                        counter_data['value'] = result
                        counter_data['formatted'] = counter_def.format_value(result) if hasattr(counter_def, 'format_value') else str(result)
                
                counters.append(counter_data)
                
        except Exception as e:
            # If counter calculation fails, still show counters without values
            for counter_def in counter_definitions:
                counters.append({
                    'counter': counter_def,
                    'value': None,
                    'formatted': 'No data',
                    'error': str(e),
                    'factoids': []
                })
    
    # Check if user is following this council
    is_following = False
    if request.user.is_authenticated:
        from council_finance.models import CouncilFollow
        is_following = CouncilFollow.objects.filter(
            user=request.user,
            council=council
        ).exists()    # Get council characteristics (meta values) for this council
    meta_values = []
    if council:
        meta_values = CouncilCharacteristic.objects.filter(
            council=council
        ).select_related('field')[:10]  # Limit to prevent too many results
      # Log page view
    log_activity(
        request,
        council=council,
        activity=f"Viewed council detail page",
        extra=f"Council: {council.name}"
    )
    
    # Handle tab parameter for edit interface
    tab = request.GET.get('tab', 'view')
    
    # Get pending contributions for edit interface
    pending_slugs = []
    characteristic_fields = []
    if tab == 'edit':
        from council_finance.models import Contribution
        pending_contributions = Contribution.objects.filter(
            council=council,
            status='pending'
        ).values_list('field__slug', flat=True)
        pending_slugs = list(pending_contributions)
        
        # Get all characteristic fields for dynamic rendering
        from council_finance.models import DataField, CouncilCharacteristic
        characteristic_fields = []
        for field in DataField.objects.filter(category='characteristic').order_by('name'):
            # Get current value if exists
            current_value = None
            try:
                char = CouncilCharacteristic.objects.get(council=council, field=field)
                current_value = char.value
            except CouncilCharacteristic.DoesNotExist:
                pass
            
            characteristic_fields.append({
                'field': field,
                'slug': field.slug,
                'name': field.name,
                'required': field.required,
                'current_value': current_value,
                'has_value': current_value is not None,
                'is_pending': field.slug in pending_slugs
            })
    
    # Get default counter slugs for JavaScript
    default_counter_slugs = [counter['counter'].slug for counter in counters]
    
    context = {
        'council': council,
        'council_year': council_year,
        'current_year': current_year,
        'years': years,
        'selected_year': selected_year,
        'recent_submissions': recent_submissions,
        'counters': counters,
        'meta_values': meta_values,
        'is_following': is_following,
        'default_counter_slugs': default_counter_slugs,
        'share_data': share_data,
        'tab': tab,
        'edit_years': years,
        'edit_selected_year': selected_year,
        'pending_slugs': pending_slugs,
        'characteristic_fields': characteristic_fields,
    }
    
    return render(request, 'council_finance/council_detail.html', context)


def council_counters(request, slug):
    """Display counters for a specific council as JSON or HTML."""
    council = get_object_or_404(Council, slug=slug)
    
    # Get the selected year from request or use default
    years = list(FinancialYear.objects.order_by("-label").exclude(label__iexact="general"))
    default_label = SiteSetting.get("default_financial_year", getattr(settings, 'DEFAULT_FINANCIAL_YEAR', current_financial_year_label()))
    selected_year = next(
        (y for y in years if y.label == default_label), years[0] if years else None
    )
    
    year_param = request.GET.get("year")
    if year_param:
        for y in years:
            if y.label == year_param:
                selected_year = y
                break
    
    counters = []
    if selected_year:
        from council_finance.agents.counter_agent import CounterAgent
        agent = CounterAgent()
        
        # Compute all counter values for this council/year using the agent
        values = agent.run(council_slug=slug, year_label=selected_year.label)
        
        # Build a lookup of overrides so we know which counters are enabled or disabled
        override_map = {
            cc.counter_id: cc.enabled
            for cc in CouncilCounter.objects.filter(council=council)
        }
        
        # Get counters based on council type
        counters_qs = CounterDefinition.objects.all()
        if council.council_type_id:
            counters_qs = counters_qs.filter(
                Q(council_types__isnull=True) | Q(council_types=council.council_type)
            )
        else:
            counters_qs = counters_qs.filter(council_types__isnull=True)
        
        head_list = []
        other_list = []
        for counter in counters_qs.distinct():
            # Check if this counter should be displayed
            enabled = override_map.get(counter.id, counter.show_by_default)
            if not enabled:
                continue
                
            value_data = values.get(counter.slug, {})
            counter_info = {
                "counter": counter,
                "value": value_data.get("value"),
                "formatted": value_data.get("formatted", "No data"),
                "error": value_data.get("error"),
                "slug": counter.slug,
                "name": counter.name,
                "description": counter.explanation,
                "duration": counter.duration,
                "precision": counter.precision,
                "show_currency": counter.show_currency,
                "friendly_format": counter.friendly_format,            }
            
            if counter.headline:
                head_list.append(counter_info)
            else:
                other_list.append(counter_info)
        
        counters = head_list + other_list
    
    # Return JSON if requested via AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "counters": {
                c["slug"]: {
                    "name": c["name"],
                    "description": c["description"],
                    "value": c["value"],
                    "formatted": c["formatted"],
                    "error": c["error"],
                    "duration": c["duration"],
                    "precision": c["precision"],
                    "show_currency": c["show_currency"],
                    "friendly_format": c["friendly_format"],
                }
                for c in counters
            },
            "year": selected_year.label if selected_year else None,
        })
    
    # Return HTML template
    context = {
        "council": council,
        "counters": counters,
        "selected_year": selected_year,
        "years": years,
    }
    return render(request, "council_finance/council_counters.html", context)


def council_change_log(request, slug):
    """Display change log for a council."""
    council = get_object_or_404(Council, slug=slug)
    
    # Get activity logs for this council
    logs = ActivityLog.objects.filter(
        related_council=council
    ).order_by('-created')
    
    # Filter by type if specified
    log_type = request.GET.get('type', '')
    if log_type:
        logs = logs.filter(activity_type=log_type)
    
    # Paginate results
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available log types for filter
    log_types = ActivityLog.objects.filter(
        council=council
    ).values_list('activity_type', flat=True).distinct()
    
    context = {
        'council': council,
        'page_obj': page_obj,
        'log_type': log_type,
        'log_types': log_types,
        'total_logs': logs.count(),
    }
    
    return render(request, 'council_finance/council_log.html', context)


@login_required
def edit_figures_table(request, slug):
    """Display enhanced inline editing interface for council figures."""
    council = get_object_or_404(Council, slug=slug)
    
    # Check if user has permission to edit
    # Allow superusers (God Mode) to bypass permission check
    if not request.user.is_superuser:
        profile = get_object_or_404(UserProfile, user=request.user)
        if profile.tier.level < 2:  # Minimum trust tier for editing
            # If this is an AJAX request, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'permission_denied',
                    'message': 'You do not have permission to edit council figures.'
                }, status=403)
            # For regular requests, redirect with an error message
            messages.error(request, 'You do not have permission to edit council figures.')
            return redirect('council_detail', slug=slug)
      # Get the requested year from URL parameters, fallback to current year
    requested_year = request.GET.get('year')
    if requested_year:
        try:
            council_year = FinancialYear.objects.get(label=requested_year)
        except FinancialYear.DoesNotExist:
            # If requested year doesn't exist, fall back to current year
            current_year = current_financial_year_label()
            council_year, created = FinancialYear.objects.get_or_create(
                label=current_year
            )
    else:
        # Default to current financial year
        current_year = current_financial_year_label()
        council_year, created = FinancialYear.objects.get_or_create(
            label=current_year
        )
      # Get all available data fields
    data_fields = DataField.objects.all().order_by('category', 'name')
    
    # Get existing data for this council
    existing_data = {}
    
    # Get characteristics (non-year specific)
    characteristics = CouncilCharacteristic.objects.filter(
        council=council
    ).select_related('field')
    
    for char in characteristics:
        existing_data[char.field.slug] = char
    
    # Get financial figures for the specified year
    financial_figures = FinancialFigure.objects.filter(
        council=council,
        year=council_year
    ).select_related('field')
    
    for figure in financial_figures:
        existing_data[figure.field.slug] = figure
    
    # Group fields by category
    field_categories = {}
    for field in data_fields:        
        category = field.category or 'Other'
        if category not in field_categories:
            field_categories[category] = []
            
        field_data = {
            'field': field,
            'submission': existing_data.get(field.slug),
            'value': existing_data.get(field.slug).value if existing_data.get(field.slug) else None,
        }
        field_categories[category].append(field_data)
    
    # Log page view
    log_activity(
        request,
        council=council,
        activity=f"Viewed figures editing interface",
        extra=f"Council: {council.name}, Year: {council_year.label}"
    )
    
    context = {
        'council': council,
        'council_year': council_year,
        'current_year': council_year.label,
        'field_categories': field_categories,
        'total_fields': len(data_fields),
    }
    
    return render(request, 'council_finance/enhanced_edit_figures_table.html', context)


@login_required
def financial_data_api(request, slug):
    """API endpoint for financial data used by spreadsheet interface."""
    council = get_object_or_404(Council, slug=slug)
    
    # Check if user has permission to view edit interface
    if not request.user.is_superuser:
        try:
            profile = get_object_or_404(UserProfile, user=request.user)
            if profile.tier.level < 2:  # Minimum trust tier for editing
                return JsonResponse({
                    'error': 'permission_denied',
                    'message': 'You do not have permission to view this data.'
                }, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'error': 'permission_denied',
                'message': 'User profile not found.'
            }, status=403)
    
    # Get the requested year
    requested_year = request.GET.get('year')
    if requested_year:
        try:
            council_year = FinancialYear.objects.get(label=requested_year)
        except FinancialYear.DoesNotExist:
            return JsonResponse({'error': 'Year not found'}, status=404)
    else:
        # Default to current financial year
        current_year = current_financial_year_label()
        council_year, created = FinancialYear.objects.get_or_create(
            label=current_year
        )
    
    # Get financial data fields organized by category
    financial_categories = ['balance_sheet', 'cash_flow', 'income', 'spending']
    financial_fields = DataField.objects.filter(
        category__in=financial_categories
    ).order_by('category', 'name')
    
    # Get existing financial figures for this council and year
    existing_figures = FinancialFigure.objects.filter(
        council=council,
        year=council_year
    ).select_related('field')
    
    # Create a mapping of field slug to figure
    figures_by_field = {figure.field.slug: figure for figure in existing_figures}
    
    # Get pending contributions for this council
    pending_contributions = Contribution.objects.filter(
        council=council,
        year=council_year,
        status='pending'
    ).values_list('field__slug', flat=True)
      # Build response data organized by category
    fields_by_category = {}
    for field in financial_fields:
        figure = figures_by_field.get(field.slug)
        
        field_data = {
            'slug': field.slug,
            'name': field.name,
            'description': field.explanation,
            'data_type': field.content_type or 'text',
            'category': field.category,
            'value': figure.value if figure else None,
            'source': figure.source_document if figure else None,
            'last_updated': figure.updated.isoformat() if figure else None,
            'is_pending': field.slug in pending_contributions
        }
        
        if field.category not in fields_by_category:
            fields_by_category[field.category] = []
        fields_by_category[field.category].append(field_data)
    
    return JsonResponse({
        'fields_by_category': fields_by_category,
        'categories': financial_categories,        'year': {
            'id': council_year.id,
            'label': council_year.label,
            'display': council_year.label  # Use label as display since no display field exists
        },
        'council': {
            'slug': council.slug,
            'name': council.name
        }
    })


@login_required
def field_options_api(request, field_slug):
    """API endpoint for field options and metadata."""
    try:
        field = DataField.objects.get(slug=field_slug)
    except DataField.DoesNotExist:
        return JsonResponse({'error': 'Field not found'}, status=404)
    
    response_data = {
        'field_type': 'text',  # default
        'placeholder': f'Enter {field.name.lower()}...',
        'options': []
    }
    
    # Handle special field types
    if field.slug == 'council_type':
        response_data['field_type'] = 'select'
        response_data['options'] = [
            {'value': ct.slug, 'label': ct.name}
            for ct in CouncilType.objects.all().order_by('name')
        ]
    elif field.slug == 'council_nation':
        response_data['field_type'] = 'select'
        response_data['options'] = [
            {'value': cn.slug, 'label': cn.name}
            for cn in CouncilNation.objects.all().order_by('name')
        ]
    elif field.data_type == 'currency':
        response_data['placeholder'] = 'Enter amount in £ (e.g., 1000000 for £1M)'
    elif field.data_type == 'percentage':
        response_data['placeholder'] = 'Enter percentage (e.g., 15.5 for 15.5%)'
    elif field.data_type == 'url':
        response_data['placeholder'] = 'Enter full URL (e.g., https://example.com)'
    
    return JsonResponse(response_data)


@login_required
def contribute_api(request):
    """API endpoint for submitting contributions from spreadsheet interface."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    
    try:
        # Get form data
        field_slug = request.POST.get('field')
        year_id = request.POST.get('year')
        value = request.POST.get('value', '').strip()
        source = request.POST.get('source', '').strip()
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Contribute API called with: field={field_slug}, year_id={year_id}, value={value}, source={source}')
        
        if not field_slug:
            return JsonResponse({'error': 'Field is required'}, status=400)
        
        # Allow empty values to clear/nullify fields
        if not value:
            value = None
        
        # Get field
        try:
            field = DataField.objects.get(slug=field_slug)
        except DataField.DoesNotExist:
            return JsonResponse({'error': 'Invalid field'}, status=400)
        
        # Get council from referrer or session
        council_slug = None
        referer = request.META.get('HTTP_REFERER', '')
        logger.info(f'Referer URL: {referer}')
        
        if '/councils/' in referer:
            try:
                # Extract council slug from URL
                parts = referer.split('/councils/')[1].split('/')
                council_slug = parts[0]
                logger.info(f'Extracted council slug: {council_slug}')
            except (IndexError, AttributeError) as e:
                logger.error(f'Error extracting council slug: {str(e)}')
                pass
        
        if not council_slug:
            logger.error(f'Could not determine council from referer: {referer}')
            return JsonResponse({'error': 'Could not determine council'}, status=400)
        
        try:
            council = Council.objects.get(slug=council_slug)
        except Council.DoesNotExist:
            return JsonResponse({'error': 'Invalid council'}, status=400)
        
        # Get year if provided
        year = None
        if year_id:
            logger.info(f'Looking up year with ID: {year_id}')
            try:
                year = FinancialYear.objects.get(id=year_id)
                logger.info(f'Found year: {year.label}')
            except FinancialYear.DoesNotExist:
                logger.error(f'FinancialYear with ID {year_id} not found')
                return JsonResponse({'error': 'Invalid year'}, status=400)
        
        # Check for existing pending contribution
        from council_finance.models import Contribution
        existing = Contribution.objects.filter(
            user=request.user,
            council=council,
            field=field,
            year=year,
            status='pending'
        ).first()
        
        if existing:
            return JsonResponse({
                'error': 'You already have a pending contribution for this field'
            }, status=400)
        
        # Handle different field types
        logger.info(f'Field category: {field.category}, slug: {field.slug}')
        if field.category == 'characteristic':
            # Council characteristics
            if field.slug == 'council_type':
                try:
                    council_type = CouncilType.objects.get(slug=value)
                    council.council_type = council_type
                    council.save()
                    points_awarded = 3
                    
                    # Remove any DataIssue for this field
                    from council_finance.models import DataIssue
                    DataIssue.objects.filter(
                        council=council,
                        field=field,
                        issue_type='missing'
                    ).delete()
                except CouncilType.DoesNotExist:
                    return JsonResponse({'error': 'Invalid council type'}, status=400)
            elif field.slug == 'council_nation':
                try:
                    council_nation = CouncilNation.objects.get(slug=value)
                    council.council_nation = council_nation
                    council.save()
                    points_awarded = 3
                    
                    # Remove any DataIssue for this field
                    from council_finance.models import DataIssue
                    DataIssue.objects.filter(
                        council=council,
                        field=field,
                        issue_type='missing'
                    ).delete()
                except CouncilNation.DoesNotExist:
                    return JsonResponse({'error': 'Invalid council nation'}, status=400)
            elif field.slug == 'council_website':
                council.website = value
                council.save()
                points_awarded = 3
                
                # Remove any DataIssue for this field
                from council_finance.models import DataIssue
                DataIssue.objects.filter(
                    council=council,
                    field=field,
                    issue_type='missing'
                ).delete()
            else:
                # Other characteristics - create or update
                characteristic, created = CouncilCharacteristic.objects.update_or_create(
                    council=council,
                    field=field,
                    defaults={'value': value}
                )
                points_awarded = 3
                
                # Remove any DataIssue for this characteristic field
                from council_finance.models import DataIssue
                DataIssue.objects.filter(
                    council=council,
                    field=field,
                    issue_type='missing'
                ).delete()
        else:
            # Financial data
            if not year:
                return JsonResponse({'error': 'Year is required for financial data'}, status=400)
            
            figure, created = FinancialFigure.objects.update_or_create(
                council=council,
                field=field,
                year=year,
                defaults={'value': value, 'source_document': source}
            )
            points_awarded = 2
            
            # Remove any DataIssue for this financial field/year
            from council_finance.models import DataIssue
            DataIssue.objects.filter(
                council=council,
                field=field,
                year=year,
                issue_type='missing'
            ).delete()
        
        # Award points to user
        try:
            profile = UserProfile.objects.get(user=request.user)
            profile.points += points_awarded
            profile.save()
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = UserProfile.objects.create(user=request.user, points=points_awarded)
        
        # Log the activity
        log_activity(
            request,
            council=council,
            activity='data_contribution',
            action=f'Updated {field.name} via spreadsheet interface',
            extra={
                'field_slug': field_slug,
                'year_label': year.label if year else None,
                'value': value,
                'points_awarded': points_awarded,
                'interface': 'spreadsheet'
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Data saved successfully! {points_awarded} points awarded.',
            'points_awarded': points_awarded,
            'user_points': profile.points,
            'field': field.slug,
            'value': value
        })
        
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f'Error in contribute_api: {str(e)}')
        logger.error(f'Traceback: {traceback.format_exc()}')
        return JsonResponse({
            'error': f'An error occurred while saving your contribution: {str(e)}'
        }, status=500)


def generate_share_link(request, slug):
    """
    Generate a shareable link for council page with specific view settings
    """
    try:
        council = get_object_or_404(Council, slug=slug)
        
        # Extract parameters from the request
        share_data = {
            'year': request.GET.get('year'),
            'counters': request.GET.get('counters'),
            'precision': request.GET.get('precision'),
            'thousands': request.GET.get('thousands'),
            'friendly': request.GET.get('friendly'),
            'show_currency': request.GET.get('show_currency', 'true'),
        }
        
        # Remove None values
        share_data = {k: v for k, v in share_data.items() if v is not None}
        
        # Generate a unique share identifier
        share_id = str(uuid4())[:8]
        
        # Store the share data in session or cache (using session for simplicity)
        if 'share_links' not in request.session:
            request.session['share_links'] = {}
        
        request.session['share_links'][share_id] = share_data
        request.session.modified = True
        
        # Generate the shareable URL
        base_url = request.build_absolute_uri(f'/councils/{slug}/')
        share_url = f"{base_url}?share={share_id}"
        
        return JsonResponse({
            'url': share_url,
            'share_id': share_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
