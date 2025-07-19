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

from council_finance.models import (
    Council, FinancialYear, FigureSubmission, 
    UserProfile, ActivityLog, CounterDefinition, SiteCounter,
    CouncilCounter, SiteSetting
)
from council_finance.agents.counter_agent import CounterAgent
from council_finance.factoids import get_factoids

# Import utility functions we'll need
from .general import log_activity, current_financial_year_label


def council_list(request):
    """Display list of all councils."""
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Base queryset
    councils = Council.objects.all()
    
    # Apply search filter
    if search_query:
        councils = councils.filter(
            Q(name__icontains=search_query) |
            Q(slug__icontains=search_query) |
            Q(council_type__icontains=search_query)
        )
    
    # Get filter parameters
    council_type = request.GET.get('type', '')
    if council_type:
        councils = councils.filter(council_type=council_type)
    
    # Order by name
    councils = councils.order_by('name')
    
    # Paginate results
    paginator = Paginator(councils, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get council types for filter dropdown
    council_types = Council.objects.values_list(
        'council_type', flat=True
    ).distinct().order_by('council_type')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'council_type': council_type,
        'council_types': council_types,
        'total_councils': councils.count(),
    }
    
    return render(request, 'council_finance/council_list.html', context)


def council_detail(request, slug):
    """Display detailed information about a council."""
    council = get_object_or_404(Council, slug=slug)
    
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
    
    # Get recent figure submissions
    recent_submissions = FigureSubmission.objects.filter(
        council=council
    ).order_by('-id')[:10]
    
    # Get factoids for this council
    factoids = get_factoids(counter_slug="council", context={"council_name": council.name})
    
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
        ).exists()

    # Get meta values (characteristics) for this council
    meta_values = []
    if council_year:
        meta_values = FigureSubmission.objects.filter(
            council=council,
            year=council_year
        ).select_related('field')[:10]  # Limit to prevent too many results
    
    # Log page view
    log_activity(
        request,
        council=council,
        activity=f"Viewed council detail page",
        extra=f"Council: {council.name}"
    )
    
    # Get default counter slugs for JavaScript
    default_counter_slugs = [counter['counter'].slug for counter in counters]
    
    context = {
        'council': council,
        'council_year': council_year,
        'current_year': current_year,
        'years': years,
        'selected_year': selected_year,
        'recent_submissions': recent_submissions,
        'factoids': factoids,
        'counters': counters,
        'meta_values': meta_values,
        'is_following': is_following,
        'default_counter_slugs': default_counter_slugs,
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
    from council_finance.models import DataField
    data_fields = DataField.objects.all().order_by('category', 'name')
    
    # Get existing figure submissions for this council and year
    existing_submissions = {}
    submissions = FigureSubmission.objects.filter(
        council=council,
        year=council_year
    ).select_related('field')
    
    for submission in submissions:
        existing_submissions[submission.field.slug] = submission
    
    # Group fields by category
    field_categories = {}
    for field in data_fields:
        category = field.category or 'Other'
        if category not in field_categories:
            field_categories[category] = []
        
        field_data = {
            'field': field,
            'submission': existing_submissions.get(field.slug),
            'value': existing_submissions.get(field.slug).value if existing_submissions.get(field.slug) else None,
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
def generate_share_link(request):
    """Generate shareable link for a council."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        council_slug = data.get('council_slug')
        
        if not council_slug:
            return JsonResponse({'error': 'Council slug is required'}, status=400)
        
        council = get_object_or_404(Council, slug=council_slug)
        
        # Generate shareable URL
        share_url = request.build_absolute_uri(
            reverse('council_detail', kwargs={'slug': council.slug})
        )
        
        # Log the share action
        log_activity(
            request,
            council=council,
            activity=f"Generated share link",
            extra=f"Council: {council.name}"
        )
        
        return JsonResponse({
            'success': True,
            'share_url': share_url,
            'council_name': council.name,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def leaderboards(request):
    """Display council leaderboards."""
    # Get the current financial year
    current_year = current_financial_year_label()
    
    # Get the FinancialYear object
    try:
        financial_year = FinancialYear.objects.get(label=current_year)
    except FinancialYear.DoesNotExist:
        financial_year = None
    
    # Get leaderboard type
    leaderboard_type = request.GET.get('type', 'total_debt')
    
    # Get councils with data for the current year
    councils = Council.objects.filter(
        figuresubmission__year__label=current_year
    ).distinct()
    
    # Calculate leaderboard data based on type
    leaderboard_data = []
    
    if leaderboard_type == 'total_debt':
        # Calculate total debt for each council
        for council in councils:
            try:
                debt_total = FigureSubmission.objects.filter(
                    council=council,
                    year=financial_year,
                    field__category='Debt'
                ).aggregate(
                    total=Sum('value')
                )['total'] or 0
                
                leaderboard_data.append({
                    'council': council,
                    'value': debt_total,
                    'formatted_value': f"£{debt_total:,.2f}" if debt_total else '£0.00',
                })
            except Exception:
                continue
    
    elif leaderboard_type == 'total_assets':
        # Calculate total assets for each council
        for council in councils:
            try:
                assets_total = FigureSubmission.objects.filter(
                    council=council,
                    year=financial_year,
                    field__category='Assets'
                ).aggregate(
                    total=Sum('value')
                )['total'] or 0
                
                leaderboard_data.append({
                    'council': council,
                    'value': assets_total,
                    'formatted_value': f"£{assets_total:,.2f}" if assets_total else '£0.00',
                })
            except Exception:
                continue
    
    # Sort leaderboard data
    leaderboard_data.sort(key=lambda x: x['value'], reverse=True)
    
    # Add rankings
    for i, item in enumerate(leaderboard_data, 1):
        item['rank'] = i
    
    # Paginate results
    paginator = Paginator(leaderboard_data, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'leaderboard_type': leaderboard_type,
        'current_year': current_year,
        'total_councils': len(leaderboard_data),
        'leaderboard_types': [
            ('total_debt', 'Total Debt'),
            ('total_assets', 'Total Assets'),
            ('council_tax', 'Council Tax'),
        ],
    }
    
    return render(request, 'council_finance/leaderboards.html', context)
