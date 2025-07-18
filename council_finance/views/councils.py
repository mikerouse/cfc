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
import json

from council_finance.models import (
    Council, FinancialYear, FigureSubmission, 
    UserProfile, ActivityLog, CounterDefinition, SiteCounter
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
    
    return render(request, 'councils/council_list.html', context)


def council_detail(request, slug):
    """Display detailed information about a council."""
    council = get_object_or_404(Council, slug=slug)
    
    # Get the current financial year
    current_year = current_financial_year_label()
    
    # Get financial data for the council
    try:
        council_year = FinancialYear.objects.get(
            council=council,
            year=current_year
        )
    except FinancialYear.DoesNotExist:
        council_year = None
    
    # Get recent figure submissions
    recent_submissions = FigureSubmission.objects.filter(
        council=council
    ).order_by('-created_at')[:10]
    
    # Get factoids for this council
    factoids = get_factoids(council=council)
    
    # Get counters for this council
    counters = CounterDefinition.objects.filter(
        active=True
    ).order_by('name')
    
    counter_values = {}
    if counters:
        counter_agent = CounterAgent()
        for counter in counters:
            try:
                value = counter_agent.calculate_counter_value(
                    counter=counter,
                    council=council,
                    year=current_year
                )
                counter_values[counter.slug] = value
            except Exception as e:
                counter_values[counter.slug] = None
    
    # Check if user is following this council
    is_following = False
    if request.user.is_authenticated:
        from council_finance.models import CouncilFollow
        is_following = CouncilFollow.objects.filter(
            user=request.user,
            council=council
        ).exists()
    
    # Log page view
    log_activity(
        request,
        council=council,
        activity=f"Viewed council detail page",
        details=f"Council: {council.name}"
    )
    
    context = {
        'council': council,
        'council_year': council_year,
        'current_year': current_year,
        'recent_submissions': recent_submissions,
        'factoids': factoids,
        'counters': counters,
        'counter_values': counter_values,
        'is_following': is_following,
    }
    
    return render(request, 'councils/council_detail.html', context)


def council_counters(request, slug):
    """Display counters for a specific council."""
    council = get_object_or_404(Council, slug=slug)
    
    # Get the current financial year
    current_year = current_financial_year_label()
    
    # Get all active counters
    counters = CounterDefinition.objects.filter(
        active=True
    ).order_by('category', 'name')
    
    # Calculate counter values
    counter_agent = CounterAgent()
    counter_results = []
    
    for counter in counters:
        try:
            value = counter_agent.calculate_counter_value(
                counter=counter,
                council=council,
                year=current_year
            )
            
            result = {
                'counter': counter,
                'value': value,
                'formatted_value': counter_agent.format_counter_value(value, counter.unit),
                'error': None
            }
        except Exception as e:
            result = {
                'counter': counter,
                'value': None,
                'formatted_value': 'Error',
                'error': str(e)
            }
        
        counter_results.append(result)
    
    # Group counters by category
    counter_categories = {}
    for result in counter_results:
        category = result['counter'].category or 'Other'
        if category not in counter_categories:
            counter_categories[category] = []
        counter_categories[category].append(result)
    
    # Log page view
    log_activity(
        request,
        council=council,
        activity=f"Viewed council counters",
        details=f"Council: {council.name}, Year: {current_year}"
    )
    
    context = {
        'council': council,
        'current_year': current_year,
        'counter_categories': counter_categories,
        'total_counters': len(counter_results),
    }
    
    return render(request, 'councils/council_counters.html', context)


def council_change_log(request, slug):
    """Display change log for a council."""
    council = get_object_or_404(Council, slug=slug)
    
    # Get activity logs for this council
    logs = ActivityLog.objects.filter(
        council=council
    ).order_by('-created_at')
    
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
    
    return render(request, 'councils/council_change_log.html', context)


@login_required
def edit_figures_table(request, slug):
    """Display enhanced inline editing interface for council figures."""
    council = get_object_or_404(Council, slug=slug)
    
    # Check if user has permission to edit
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.trust_tier < 2:  # Minimum trust tier for editing
        messages.error(request, 'You do not have permission to edit council figures.')
        return redirect('council_detail', slug=slug)
    
    # Get the current financial year
    current_year = current_financial_year_label()
    
    # Get or create council year
    council_year, created = FinancialYear.objects.get_or_create(
        council=council,
        year=current_year
    )
    
    # Get all available data fields
    from council_finance.models import DataField
    data_fields = DataField.objects.filter(
        active=True
    ).order_by('category', 'name')
    
    # Get existing figure submissions for this council and year
    existing_submissions = {}
    submissions = FigureSubmission.objects.filter(
        council=council,
        year=current_year
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
        details=f"Council: {council.name}, Year: {current_year}"
    )
    
    context = {
        'council': council,
        'council_year': council_year,
        'current_year': current_year,
        'field_categories': field_categories,
        'total_fields': len(data_fields),
    }
    
    return render(request, 'councils/enhanced_edit_figures_table.html', context)


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
            details=f"Council: {council.name}"
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
                    year=current_year,
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
                    year=current_year,
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
    
    return render(request, 'councils/leaderboards.html', context)
