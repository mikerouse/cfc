"""
Static pages and informational views for Council Finance Counters.
This module handles about, terms, privacy, and other static content.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
import random
from django.db.models import Q

from council_finance.models import Council, UserProfile, ActivityLog, DataField

# Import utility functions we'll need
from .general import log_activity, current_financial_year_label


def contribute_redirect(request):
    """
    Redirect page for old contribute system.
    Informs users about the new flagging system.
    """
    return render(request, 'council_finance/contribute_redirect.html', {
        'page_title': 'Data Contribution Has Changed',
        'show_flagging_help': True,
    })


def home(request):
    """Main homepage view."""
    # Get the current financial year
    current_year = current_financial_year_label()
      # Get featured councils (top 10 by data completeness or activity)
    featured_councils = Council.objects.filter(
        Q(financial_figures__year__label=current_year) | Q(characteristics__isnull=False)
    ).distinct()[:10]
    
    # Get total statistics
    total_councils = Council.objects.count()
    total_users = UserProfile.objects.count()
    
    # Get recent activity
    recent_activity = ActivityLog.objects.filter(
        activity_type__in=['create', 'update', 'contribution', 'data_correction']
    ).order_by('-created')[:5]
    
    # Check if user is logged in and get their profile
    user_profile = None
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            pass
    
    # Log page view
    log_activity(
        request,
        activity="Viewed homepage",
        extra=f"Year: {current_year}"
    )
    
    context = {
        'featured_councils': featured_councils,
        'current_year': current_year,
        'total_councils': total_councils,
        'total_users': total_users,
        'recent_activity': recent_activity,
        'user_profile': user_profile,
    }
    
    return render(request, 'council_finance/home.html', context)


def about(request):
    """About page explaining the project, its goals, and how to contribute."""
    from council_finance.services.github_stats import GitHubStatsService
    from council_finance.models import FinancialYear, UserFollow
    
    # Initialize GitHub service
    github_service = GitHubStatsService()
    
    # Prepare context with all required variables
    context = {
        'page_title': 'About - Council Finance Counters',
        
        # Basic statistics
        'total_councils': Council.objects.count(),
        'total_data_fields': DataField.objects.count(),
        'total_contributions': ActivityLog.objects.filter(activity_type='update').count(),
        'latest_year': FinancialYear.objects.order_by('-start_date').first(),
        
        # GitHub data
        'github_repo_url': 'https://github.com/mikerouse/cfc',
        'github_stats': github_service.get_repository_stats() or {
            'stars': 0,
            'forks': 0,
            'open_issues': 0,
            'commits': 0,
            'pull_requests': 0,
            'closed_issues': 0,
        },
        'contributors': github_service.get_contributors() or [],
        
        # Technology stack
        'tech_stack': [
            {'name': 'Django', 'description': 'Python web framework for robust backend'},
            {'name': 'PostgreSQL', 'description': 'Powerful open-source database'},
            {'name': 'Tailwind CSS', 'description': 'Utility-first CSS framework'},
            {'name': 'Alpine.js', 'description': 'Lightweight JavaScript framework'},
            {'name': 'Chart.js', 'description': 'Flexible charting library'},
            {'name': 'OpenAI API', 'description': 'AI-powered insights and analysis'},
        ],
        
        # Legacy stats dict for compatibility
        'stats': {
            'total_councils': Council.objects.count(),
            'total_users': UserProfile.objects.count(),
            'total_contributions': ActivityLog.objects.count(),
            'current_year': current_financial_year_label(),
        },
    }
    
    return render(request, 'council_finance/about.html', context)


def terms_of_use(request):
    """Terms of use page."""
    return render(request, 'council_finance/terms_of_use.html')


def privacy_cookies(request):
    """Privacy and cookies policy page."""
    return render(request, 'council_finance/privacy_cookies.html')


def corrections(request):
    """Corrections and data accuracy page."""
    # Get recent corrections/updates
    recent_corrections = ActivityLog.objects.filter(
        activity_type='correction',
        public=True
    ).order_by('-created_at')[:10]
    
    context = {
        'recent_corrections': recent_corrections,
    }
    
    return render(request, 'council_finance/corrections.html', context)


@login_required
def dashboard(request):
    """User dashboard - personalized homepage for logged-in users."""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get user's recent activity
    recent_activity = ActivityLog.objects.filter(
        user=request.user
    ).order_by('-created')[:10]
    
    # Get user's contributions
    from council_finance.models import Contribution
    recent_contributions = Contribution.objects.filter(
        user=request.user
    ).order_by('-created')[:5]
    
    # Get councils the user is following
    from council_finance.models import CouncilFollow
    following_councils = CouncilFollow.objects.filter(
        user=request.user
    ).select_related('council')[:5]
    
      # Get user stats
    stats = {
        'total_contributions': Contribution.objects.filter(user=request.user).count(),
        'councils_following': CouncilFollow.objects.filter(user=request.user).count(),
        'trust_tier': user_profile.tier.level,
        'member_since': user_profile.user.date_joined,
    }
    
    context = {
        'user_profile': user_profile,
        'recent_activity': recent_activity,
        'recent_contributions': recent_contributions,
        'following_councils': following_councils,
        'stats': stats,
    }
    
    return render(request, 'accounts/dashboard.html', context)


def help_center(request):
    """Help center and documentation."""
    # Get help topics
    help_topics = [
        {
            'title': 'Getting Started',
            'description': 'Learn how to use Council Finance Counters',
            'url': '/help/getting-started/',
        },
        {
            'title': 'Contributing Data',
            'description': 'How to contribute financial data for councils',
            'url': '/help/contributing/',
        },
        {
            'title': 'Understanding the Data',
            'description': 'Learn about the financial data and what it means',
            'url': '/help/understanding-data/',
        },
        {
            'title': 'Trust Tiers',
            'description': 'Understanding user trust levels and permissions',
            'url': '/help/trust-tiers/',
        },
    ]
    
    context = {
        'help_topics': help_topics,
    }
    
    return render(request, 'pages/help_center.html', context)


def contact(request):
    """Contact page."""
    return render(request, 'pages/contact.html')


def features(request):
    """Features page highlighting platform capabilities."""
    features_list = [
        {
            'title': 'Comprehensive Data',
            'description': 'Access financial data from councils across the UK',
            'icon': 'fas fa-database',
        },
        {
            'title': 'Community Driven',
            'description': 'User-contributed data with community validation',
            'icon': 'fas fa-users',
        },
        {
            'title': 'Real-time Updates',
            'description': 'Get notifications when new data is available',
            'icon': 'fas fa-bell',
        },
        {
            'title': 'Powerful Analytics',
            'description': 'Compare councils and track trends over time',
            'icon': 'fas fa-chart-line',
        },
    ]
    
    context = {
        'features': features_list,
    }
    
    return render(request, 'pages/features.html', context)


def api_documentation(request):
    """API documentation page."""
    api_endpoints = [
        {
            'endpoint': '/api/councils/search/',
            'method': 'GET',
            'description': 'Search for councils by name or slug',
            'parameters': [
                {'name': 'q', 'type': 'string', 'description': 'Search query'},
            ],
        },
        {
            'endpoint': '/api/field/{field_slug}/info/',
            'method': 'GET',
            'description': 'Get information about a specific data field',
            'parameters': [
                {'name': 'field_slug', 'type': 'string', 'description': 'Field slug identifier'},
            ],
        },
        {
            'endpoint': '/api/council/{council_slug}/recent-activity/',
            'method': 'GET',
            'description': 'Get recent activity for a specific council',
            'parameters': [
                {'name': 'council_slug', 'type': 'string', 'description': 'Council slug identifier'},
            ],
        },
    ]
    
    context = {
        'api_endpoints': api_endpoints,
    }
    
    return render(request, 'pages/api_documentation.html', context)
