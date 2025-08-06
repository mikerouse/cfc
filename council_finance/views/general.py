from django.shortcuts import render, get_object_or_404, redirect
import logging
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    Http404,
    HttpResponse,
)
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Cast
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth import login
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import reverse
from django.core import signing
from council_finance.services.github_stats import GitHubStatsService
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import models

import ast
import csv
import hashlib
import inspect
import json
import operator

# Brevo's Python SDK exposes ApiException from the `rest` module
from brevo_python.rest import ApiException

from council_finance.emails import send_confirmation_email, send_email
from council_finance.notifications import create_notification
from council_finance.decorators import comments_access_required

# Import the constant containing valid field names for counter formulas.
from council_finance.forms import (
    SignUpForm,
    CouncilListForm,
    CounterDefinitionForm,
    SiteCounterForm,
    GroupCounterForm,
    DataFieldForm,
    ProfileExtraForm,
    UpdateCommentForm,
)
from django.conf import settings

# Minimum trust tier level required to access management views.
MANAGEMENT_TIER = 4

# Logger used throughout this module for operational messages.
logger = logging.getLogger(__name__)

from council_finance.models import DataField
from council_finance.year_utils import previous_year_label
from council_finance.models import (
    Council,
    FinancialYear,
    UserProfile,
    UserFollow,
    PendingProfileChange,
    CouncilList,
    CounterDefinition,
    CouncilCounter,
    SiteCounter,
    DataField,
    CouncilCharacteristic,
    FinancialFigure,
    FinancialFigureHistory,
    CouncilCharacteristicHistory,
    GroupCounter,
    SiteSetting,
    TrustTier,
    Contribution,
    DataChangeLog,
    BlockedIP,
    # RejectionLog is used in the God Mode admin view for moderating
    # contribution rejections and IP blocks.
    RejectionLog,
    ActivityLog,
    ActivityLogComment,
    CouncilFollow,
    CouncilUpdate,
    CouncilUpdateLike,
    CouncilUpdateComment,
    FeedUpdate,
    FeedComment,
    UserFeedPreferences,
)

# Import new data models
try:
    from council_finance.models.new_data_model import (
        CouncilCharacteristic, 
        FinancialFigure, 
        ContributionV2,
        CouncilCharacteristicHistory,
        FinancialFigureHistory
    )
    NEW_DATA_MODEL_AVAILABLE = True
except ImportError:
    NEW_DATA_MODEL_AVAILABLE = False

from datetime import date


def log_activity(
    request,
    *,
    council=None,
    activity="",
    log_type="user",
    action="",
    request_data=None,
    response="",
    extra=None,
):
    """Helper to store troubleshooting events using the modern ActivityLog system."""
    import json
    import inspect

    # Build a dictionary describing the context of the call so that
    # downstream analysis tools can more easily pinpoint where the
    # action originated. This includes the calling module, function and
    # any class name if ``log_activity`` was called inside a method.
    if isinstance(extra, dict) or extra is None:
        extra_data = extra or {}
    else:
        # If a string was supplied, try to decode it as JSON; otherwise
        # store it under the ``note`` key.
        try:
            extra_data = json.loads(extra)
        except Exception:
            extra_data = {"note": str(extra)}

    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller = frame.f_back
        module = caller.f_globals.get("__name__")
        func = caller.f_code.co_name
        cls = None
        if "self" in caller.f_locals:
            cls = caller.f_locals["self"].__class__.__name__
        extra_data.update({
            "module": module,
            "function": func,
        })
        if cls:
            extra_data["class"] = cls

    # Request data defaults to the HTTP method for quick reference. The caller
    # can supply a short string or dict to capture more detail when needed.
    if request_data is None:
        request_data = request.method
    if isinstance(request_data, dict):
        request_data = json.dumps(request_data, ensure_ascii=False)
    elif request_data is None:
        request_data = ""

    # Map the legacy activity to modern activity types
    activity_type_mapping = {
        'field_delete': 'delete',
        'apply_contribution': 'contribution', 
        'submit_contribution': 'contribution',
        'review_contribution': 'moderation',
        'council_merge': 'council_merge',
        'financial_year': 'financial_year',
        'data_correction': 'data_correction',
    }
    
    modern_activity_type = activity_type_mapping.get(activity, 'system')
    
    # Create the activity log using the new enhanced model
    ActivityLog.log_activity(
        activity_type=modern_activity_type,
        description=f"{activity}: {action}" if action else activity or "Legacy activity",
        user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        related_council=council,
        status='completed',
        details={
            'legacy_data': extra_data,
            'request_method': request_data,
            'response': response,
            'page': request.path,
            'action': action,
        },
        request=request
    )


def current_financial_year_label() -> str:
    """Return label like ``2025/26`` for the current UK financial year."""
    today = date.today()
    if today.month < 4:
        start = today.year - 1
    else:
        start = today.year
    end = start + 1
    return f"{start}/{str(end)[-2:]}"


def search_councils(request):
    """Return councils matching a query for live search."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    results = Council.objects.filter(
        Q(name__icontains=query) | Q(slug__icontains=query)
    ).values("name", "slug")[:10]
    return JsonResponse(list(results), safe=False)


@require_GET
def list_field_options(request, field_slug=None, slug=None):
    """Return selectable options for a list type field."""
    # The contribution modal needs to populate a drop-down when a
    # characteristic is backed by another dataset (e.g. council type).
    # This small API provides the ID/name pairs used to build that menu.
    from council_finance.models import DataField

    # Handle both parameter names for backward compatibility
    field_slug = field_slug or slug
    
    try:
        field = DataField.objects.get(slug=field_slug)
    except DataField.DoesNotExist:
        return JsonResponse({"error": "Field not found"}, status=404)

    # Only list type fields should have selectable options
    if field.content_type != "list":
        return JsonResponse({"error": "Field is not a list type"}, status=400)
    
    # Check if the field has a dataset_type configured
    if not field.dataset_type:
        return JsonResponse({"error": "Field has no dataset configured"}, status=400)

    try:
        model = field.dataset_type.model_class()
        options = list(model.objects.values("id", "name"))
        return JsonResponse({"options": options})
    except Exception as e:
        logger.error(f"Error getting field options for {slug}: {str(e)}")
        return JsonResponse({"error": "Could not load field options"}, status=500)


def home(request):
    """Enhanced landing page with counters, featured content and widgets."""
    # Determine the latest financial year for which we have debt figures
    latest_year = FinancialYear.objects.order_by("-label").first()
    
    councils_with_debt_count = 0
    if latest_year:
        try:
            field = DataField.objects.filter(slug="total_debt").first()
            if field:
                # Get total debt and count of councils with non-zero debt data
                debt_figures = FinancialFigure.objects.filter(
                    field=field, 
                    year=latest_year
                ).exclude(value=0)
                
                total_debt = debt_figures.aggregate(total=Sum("value"))["total"] or 0
                councils_with_debt_count = debt_figures.values('council').distinct().count()
            else:
                logger.warning("DataField 'total_debt' not found in database")  
                total_debt = 0
        except Exception as e:
            logger.error(f"Error calculating total debt: {e}")
            total_debt = 0
    else:
        # Fallback when no figures are loaded
        total_debt = 0

    # Get total council count for hero section
    total_councils = Council.objects.count()
    
    # Calculate enhanced hero stats
    total_debt_billions = total_debt / 1_000_000_000 if total_debt else 0
    
    # Calculate completion percentage (cached to avoid expensive calculation)
    from django.core.cache import cache
    completion_cache_key = "home_completion_percentage"
    completion_percentage = cache.get(completion_cache_key)
    
    if completion_percentage is None:
        all_years = FinancialYear.objects.all()
        # Use a single query to get counts instead of multiple
        from django.db.models import Count
        counts = {
            'councils': total_councils,  # Already calculated above
            'fields': DataField.objects.count(),
            'years': all_years.count(),
            'characteristics': CouncilCharacteristic.objects.count(),
            'figures': FinancialFigure.objects.count()
        }
        
        expected_data_points = counts['councils'] * counts['fields'] * counts['years']
        actual_data_points = counts['characteristics'] + counts['figures']
        completion_percentage = (actual_data_points / expected_data_points * 100) if expected_data_points > 0 else 0
        
        # Cache completion percentage for 30 minutes (data doesn't change frequently)
        cache.set(completion_cache_key, completion_percentage, 1800)
    
    # Get all_years here for later use (reuse from cache calculation if available)
    if 'all_years' not in locals():
        all_years = FinancialYear.objects.all()
    
    # Get featured councils (mix of council of the day + random selection)
    featured_councils = []
    council_of_the_day = None
    if Council.objects.exists():
        # Get a deterministic "random" council based on today's date for council of the day
        import hashlib
        from datetime import date
        
        today_seed = hashlib.md5(str(date.today()).encode()).hexdigest()
        council_count = Council.objects.count()
        if council_count > 0:
            try:
                council_index = int(today_seed[:8], 16) % council_count
                council_of_the_day = Council.objects.all()[council_index]
            except (ValueError, IndexError) as e:
                logger.warning(f"Error selecting council of the day: {e}")
                council_of_the_day = Council.objects.first()  # Safe fallback
            
            # Get a few more featured councils (exclude council of the day)
            # Use a more efficient approach than order_by('?') which is expensive
            remaining_councils = Council.objects.exclude(id=council_of_the_day.id)
            council_count_remaining = remaining_councils.count()
            
            if council_count_remaining > 0:
                # Select councils using deterministic but varied approach
                import hashlib
                from datetime import date
                seed = hashlib.md5(f"{date.today()}_featured".encode()).hexdigest()
                selected_indices = []
                for i in range(min(5, council_count_remaining)):
                    index_seed = hashlib.md5(f"{seed}_{i}".encode()).hexdigest()
                    index = int(index_seed[:8], 16) % council_count_remaining
                    selected_indices.append(index)
                
                # Convert to list to enable indexing
                remaining_list = list(remaining_councils.all())
                # Validate indices are within bounds to prevent IndexError
                # Ensure we don't select the same council twice by using set
                selected_councils = set()
                featured_councils_raw = [council_of_the_day]  # Start with council of the day
                
                for i in selected_indices[:5]:
                    if 0 <= i < len(remaining_list):
                        council = remaining_list[i]
                        if council.id not in selected_councils and council.id != council_of_the_day.id:
                            featured_councils_raw.append(council)
                            selected_councils.add(council.id)
                            if len(featured_councils_raw) >= 6:  # Max 6 councils total
                                break
            else:
                featured_councils_raw = [council_of_the_day]
            
            # Enhance featured councils with financial data carousel
            # Use caching to avoid expensive CounterAgent calls on every page load
            from django.core.cache import cache
            import hashlib
            
            featured_councils = []
            councils_ids_str = ','.join([str(c.id) for c in featured_councils_raw])
            councils_cache_key = f"featured_councils_{hashlib.md5(councils_ids_str.encode()).hexdigest()}"
            cached_featured = cache.get(councils_cache_key)
            
            if cached_featured is not None:
                featured_councils = cached_featured
            else:
                # Only run expensive operations if not cached
                from council_finance.agents.counter_agent import CounterAgent
                agent = CounterAgent()
                
                for council in featured_councils_raw:
                    council_data = {'council': council, 'financial_years': []}
                    
                    # Get current liabilities data for available years (limited to reduce load)
                    for year in all_years[:2]:  # Reduced from 3 to 2 years for performance
                        # Check cache first for this specific council/year combination
                        council_year_key = f"council_data_{council.slug}_{year.label}"
                        cached_result = cache.get(council_year_key)
                        
                        if cached_result is not None:
                            result = cached_result
                        else:
                            try:
                                result = agent.run(council_slug=council.slug, year_label=year.label)
                                # Cache individual council/year results for 10 minutes
                                cache.set(council_year_key, result, 600)
                            except Exception as e:
                                logger.warning(f"CounterAgent failed for {council.slug}/{year.label}: {e}")
                                result = {}  # Provide fallback empty result
                        
                        current_liabilities = result.get('current-liabilities')
                        
                        if current_liabilities and current_liabilities.get('value') and current_liabilities.get('value') > 0:
                            # Use friendly format for carousel display
                            from council_finance.models.counter import CounterDefinition
                            counter_def = CounterDefinition.objects.filter(slug='current-liabilities').first()
                            if counter_def:
                                friendly_value = counter_def.format_value(current_liabilities['value'])
                                council_data['financial_years'].append({
                                    'year': year.label,
                                    'value': friendly_value,
                                    'raw_value': current_liabilities['value']
                                })
                    
                    featured_councils.append(council_data)
                
                # Cache featured councils for 15 minutes
                cache.set(councils_cache_key, featured_councils, 900)

    # Get recent activity for the homepage
    recent_contributions = Contribution.objects.filter(
        status='approved'
    ).select_related('user', 'council', 'field').order_by('-created')[:5]
    
    # Get top contributors this month
    from datetime import datetime, timedelta
    month_ago = datetime.now() - timedelta(days=30)
    from django.db.models import Count
    
    top_contributors = Contribution.objects.filter(
        status='approved',
        created__gte=month_ago
    ).values(
        'user__username'
    ).annotate(
        contribution_count=Count('id')
    ).order_by('-contribution_count')[:5]

    # Get interesting statistics
    missing_data_count = 0
    pending_contributions_count = Contribution.objects.filter(status='pending').count()
    
    # Calculate missing data points (simplified)
    from council_finance.models import DataIssue
    try:
        missing_data_count = DataIssue.objects.filter(
            issue_type='missing_characteristic'
        ).count() + DataIssue.objects.filter(
            issue_type='missing_financial'
        ).count()
    except (DataIssue.DoesNotExist, AttributeError, Exception) as e:
        logger.warning(f"Error calculating missing data count: {e}")
        missing_data_count = 0

    promoted = []
    # Import here to keep the view lightweight if the home page is cached.
    from council_finance.models import SiteCounter, GroupCounter
    from django.core.cache import cache
    from council_finance.agents.site_totals_agent import SiteTotalsAgent

    all_years = list(FinancialYear.objects.order_by("-label"))
    missing_cache = False

    # First pass to detect missing cache entries. The totals are normally
    # populated by ``SiteTotalsAgent`` via a scheduled task. When the cache is
    # cold (for example on a fresh install) we compute the values on demand so
    # visitors never see zeroed counters.
    # Site and group counters rely on cached totals generated by ``SiteTotalsAgent``.
    # The agent normally runs on a schedule so most requests simply read the
    # cached values. If any cache entry is missing ``None`` we recompute all
    # totals immediately to avoid empty counters.
    for sc in SiteCounter.objects.filter(promote_homepage=True):
        year_label = sc.year.label if sc.year else "all"
        key = f"counter_total:{sc.slug}:{year_label}"
        val = cache.get(key)
        if val is None:
            missing_cache = True
        elif val == 0 and (FinancialFigure.objects.exists() or CouncilCharacteristic.objects.exists()):
            # A zero total with actual figures likely means the cache was
            # populated before data was loaded. Trigger a refresh so visitors
            # see correct values without manual intervention.
            missing_cache = True
        if sc.year and cache.get(f"{key}:prev") is None:
            missing_cache = True

    for gc in GroupCounter.objects.filter(promote_homepage=True):
        year_label = gc.year.label if gc.year else "all"
        key = f"counter_total:{gc.slug}:{year_label}"
        # Group counters may be restricted to subsets of councils. We apply the
        # same logic as above to ensure the totals reflect loaded data.
        val = cache.get(key)
        if val is None:
            missing_cache = True
        elif val == 0 and (FinancialFigure.objects.exists() or CouncilCharacteristic.objects.exists()):
            missing_cache = True
        if gc.year and cache.get(f"{key}:prev") is None:
            missing_cache = True

    # When any counter total is missing, use fallback values instead of 
    # running expensive SiteTotalsAgent synchronously. The agent should be 
    # run via scheduled task or management command, not on page load.
    if missing_cache:
        # Log the issue for admin awareness but don't block page rendering
        logger.warning("Home page: Site counter cache is cold. Run 'python manage.py run_site_totals_agent' to populate cache.")
        # Don't run SiteTotalsAgent().run() here - it's too expensive!

    # Now build the list of promoted counters using the cached totals. This may
    # happen after the agent has populated the cache above.
    for sc in SiteCounter.objects.filter(promote_homepage=True):
        year_label = sc.year.label if sc.year else "all"
        value = cache.get(f"counter_total:{sc.slug}:{year_label}", 0)
        prev_value = 0
        if sc.year:
            prev_value = cache.get(f"counter_total:{sc.slug}:{year_label}:prev", 0)
        formatted = sc.counter.format_value(value)
        promoted.append({
            "slug": sc.slug,
            "counter_slug": sc.counter.slug,
            "year": sc.year.label if sc.year else None,
            "name": sc.name,
            "formatted": formatted,
            "raw": value,
            "duration": sc.duration,
            "precision": sc.precision,
            "show_currency": sc.show_currency,
            "friendly_format": sc.friendly_format,
            "explanation": sc.explanation,
            "columns": sc.columns,
        })

    # Group counters follow the same pattern but target a subset of councils.
    for gc in GroupCounter.objects.filter(promote_homepage=True):
        year_label = gc.year.label if gc.year else "all"
        value = cache.get(f"counter_total:{gc.slug}:{year_label}", 0)
        prev_value = 0
        if gc.year:
            prev_value = cache.get(f"counter_total:{gc.slug}:{year_label}:prev", 0)
        formatted = gc.counter.format_value(value)
        promoted.append({
            "slug": gc.slug,
            "name": gc.name,
            "formatted": formatted,
            "raw": value,
            "duration": gc.duration,
            "precision": gc.precision,
            "show_currency": gc.show_currency,
            "friendly_format": gc.friendly_format,
            "explanation": "",  # groups currently lack custom explanations
            "columns": 3,  # groups default to full width for now
        })

    context = {
        "total_debt": total_debt,
        "total_debt_billions": total_debt_billions,
        "total_councils": total_councils,
        "councils_with_debt_count": councils_with_debt_count,
        "completion_percentage": completion_percentage,
        "council_of_the_day": council_of_the_day,
        "featured_councils": featured_councils,
        "recent_contributions": recent_contributions,
        "top_contributors": top_contributors,
        "missing_data_count": missing_data_count,
        "pending_contributions_count": pending_contributions_count,
        "promoted_counters": promoted,
        "latest_year": latest_year,
        "current_year": latest_year.label if latest_year else "",
    }

    return render(request, "council_finance/home.html", context)


def council_list(request):
    """Display a list of councils with optional search by name or slug."""
    # Grab search term from query parameters if provided
    query = request.GET.get("q", "")

    # Base queryset of all councils
    councils = Council.objects.all()

    # Apply a simple case-insensitive name or slug filter when a query is present
    if query:
        councils = councils.filter(Q(name__icontains=query) | Q(slug__icontains=query))
    context = {
        "councils": councils,
        "query": query,
    }
    return render(request, "council_finance/council_list.html", context)


def council_detail(request, slug):
    """Show details for a single council."""
    # Fetch the council or return a 404 if the slug is unknown
    council = get_object_or_404(Council, slug=slug)
    tab = request.GET.get("tab") or "view"
    focus = request.GET.get("focus", "")
    
    # Redirect old edit tab to new React interface
    if tab == "edit":
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse('council_edit', args=[slug]))

    share_token = request.GET.get("share")
    share_data = None
    if share_token:
        try:
            share_data = signing.loads(share_token)
        except signing.BadSignature:
            share_data = None    # Get all characteristics for this council (non-year specific)
    characteristics = CouncilCharacteristic.objects.filter(council=council).select_related("field")
    if council.council_type_id:
        characteristics = characteristics.filter(
            Q(field__council_types__isnull=True)
            | Q(field__council_types=council.council_type)
        )
    else:
        characteristics = characteristics.filter(field__council_types__isnull=True)
    
    # Get all financial figures for this council (year specific)
    financial_figures = FinancialFigure.objects.filter(council=council).select_related(
        "year", "field"
    )
    if council.council_type_id:
        financial_figures = financial_figures.filter(
            Q(field__council_types__isnull=True)
            | Q(field__council_types=council.council_type)
        )
    else:
        financial_figures = financial_figures.filter(field__council_types__isnull=True)
    financial_figures = financial_figures.order_by("year__label", "field__slug").distinct()
      # Keep financial_figures as QuerySet for filtering, create figures list for template
    figures = list(financial_figures)

    years = list(
        FinancialYear.objects.order_by("-label").exclude(label__iexact="general")
    )
    default_label = SiteSetting.get(
        "default_financial_year", settings.DEFAULT_FINANCIAL_YEAR
    )
    selected_year = next(
        (y for y in years if y.label == default_label), years[0] if years else None
    )
    if share_data and share_data.get("year"):
        for y in years:
            if y.label == share_data["year"]:
                selected_year = y
                break
    # Annotate display labels so the template can show the current year as
    # "Current Year to Date" without storing a separate field in the DB.
    current_label = current_financial_year_label()
    for y in years:
        y.display = "Current Year to Date" if y.label == current_label else y.label

    # Edit tab uses a shorter list of years (last 25) so users can select
    # historical figures. The dropdown defaults to the latest year unless
    # the request specifies otherwise.
    edit_years = years[:25]
    edit_selected_year = edit_years[0] if edit_years else None
    req_year = request.GET.get("year") if tab == "edit" else None
    if req_year:
        for y in edit_years:
            if y.label == req_year:
                edit_selected_year = y
                break
    counters = []
    default_slugs = []
    if selected_year:
        from council_finance.agents.counter_agent import CounterAgent
        from django.core.cache import cache

        agent = CounterAgent()
        
        # Cache counter calculations for 10 minutes to improve performance
        cache_key_current = f"counter_values:{slug}:{selected_year.label}"
        values = cache.get(cache_key_current)
        
        if values is None:
            # Compute all counter values for this council/year using the agent
            values = agent.run(council_slug=slug, year_label=selected_year.label)
            cache.set(cache_key_current, values, 600)  # 10 minutes
        
        prev_values = {}
        prev_label = previous_year_label(selected_year.label)
        if prev_label:
            prev_year = FinancialYear.objects.filter(label=prev_label).first()
            if prev_year:
                cache_key_prev = f"counter_values:{slug}:{prev_year.label}"
                prev_values = cache.get(cache_key_prev)
                
                if prev_values is None:
                    prev_values = agent.run(council_slug=slug, year_label=prev_year.label)
                    cache.set(cache_key_prev, prev_values, 600)  # 10 minutes

        # Build a lookup of overrides so we know which counters are enabled or
        # disabled specifically for this council.
        override_map = {
            cc.counter_id: cc.enabled
            for cc in CouncilCounter.objects.filter(council=council)
        }

        # Loop over every defined counter and decide whether it should be
        # displayed. If the council has an explicit override we honour that,
        # otherwise we fall back to the counter's show_by_default flag.
        head_list = []
        other_list = []
        counters_qs = CounterDefinition.objects.all()
        if council.council_type_id:
            counters_qs = counters_qs.filter(
                Q(council_types__isnull=True) | Q(council_types=council.council_type)
            )
        else:
            counters_qs = counters_qs.filter(council_types__isnull=True)
        for counter in counters_qs.distinct():
            enabled = override_map.get(counter.id, counter.show_by_default)
            if not enabled:
                continue
            result = values.get(counter.slug, {})
            prev = prev_values.get(counter.slug, {}) if prev_values else {}
            item = {
                "counter": counter,
                "value": result.get("value"),
                "formatted": result.get("formatted"),
                "error": result.get("error"),
            }
            if counter.headline:
                head_list.append(item)
            else:
                other_list.append(item)
            if counter.show_by_default:
                default_slugs.append(counter.slug)
        counters = head_list + other_list

    # Old meta fields logic removed - now using dynamic meta fields system below

    is_following = False
    is_favourited = False
    if request.user.is_authenticated:
        from council_finance.models import CouncilFollow

        is_following = CouncilFollow.objects.filter(
            user=request.user, council=council
        ).exists()
        
        # Check if council is in user's favourites (default list)
        default_list = CouncilList.objects.filter(
            user=request.user, is_default=True
        ).first()
        if default_list:
            is_favourited = default_list.councils.filter(id=council.id).exists()
    
    # Check for recent merge or administrative actions
    recent_merge_activity = None
    recent_flag_activity = None
    administrative_messages = []
    
    if hasattr(council, 'activity_logs'):
        from django.utils import timezone
        from datetime import timedelta
        
        # Look for recent merge activities (last 30 days)
        recent_cutoff = timezone.now() - timedelta(days=30)
        merge_logs = council.activity_logs.filter(
            activity_type='council_merge',
            created__gte=recent_cutoff
        ).order_by('-created')
        
        if merge_logs.exists():
            recent_merge_activity = merge_logs.first()
            administrative_messages.append({
                'type': 'merge',
                'message': f"This council was merged from another authority on {recent_merge_activity.created.strftime('%B %d, %Y')}. {recent_merge_activity.description}",
                'timestamp': recent_merge_activity.created
            })
        
        # Look for recent flag/moderation activities
        flag_logs = council.activity_logs.filter(
            activity_type__in=['moderation', 'data_correction'],
            created__gte=recent_cutoff
        ).order_by('-created')
        
        if flag_logs.exists():
            recent_flag_activity = flag_logs.first()
            administrative_messages.append({
                'type': 'flag',
                'message': f"Recent data update: {recent_flag_activity.description}",
                'timestamp': recent_flag_activity.created
            })
    
    # Check if council is defunct
    if council.status == 'defunct':
        administrative_messages.append({
            'type': 'defunct',
            'message': 'This council is no longer active. It may have been merged with another authority or dissolved.',
            'timestamp': None
        })        
    # Use the QuerySet for filtering, not the list
    edit_figures = financial_figures.filter(year=edit_selected_year) if edit_selected_year else financial_figures.none()
    
    # For edit tab, we want to show ALL available fields, not just existing submissions
    if tab == "edit" and edit_selected_year:
        # Get all available data fields for this council type
        all_fields = DataField.objects.all()
        if council.council_type_id:
            all_fields = all_fields.filter(
                Q(council_types__isnull=True)
                | Q(council_types=council.council_type)
            )
        else:
            all_fields = all_fields.filter(council_types__isnull=True)
        
        # Create figure objects with existing submissions or None values
        edit_figures_list = []
        existing_figures = {
            f.field_id: f for f in edit_figures
        }
        
        for field in all_fields.order_by('name').distinct():
            if field.id in existing_figures:                # Use existing submission
                edit_figures_list.append(existing_figures[field.id])
            else:
                # Create a placeholder figure for editing
                if field.category == 'financial':
                    figure = FinancialFigure(
                        council=council,
                        field=field, 
                        year=edit_selected_year,
                        value=None
                    )
                else:
                    # For characteristics, create a placeholder
                    figure = CouncilCharacteristic(
                        council=council,
                        field=field,
                        value=None
                    )
                edit_figures_list.append(figure)
        
        edit_figures = edit_figures_list

    missing_characteristic_page = None
    missing_characteristic_paginator = None
    if tab == "edit":
        from council_finance.models import DataIssue
        from django.core.paginator import Paginator

        # Pull any missing characteristic data for this council so the edit
        # screen can reuse the generic table component.
        missing_qs = (
            DataIssue.objects.filter(
                council=council,
                field__category="characteristic",
                issue_type="missing",
            )
            .select_related("field")
            .order_by("field__name")
        )
        missing_characteristic_paginator = Paginator(missing_qs, 50)
        missing_characteristic_page = missing_characteristic_paginator.get_page(1)

    # Get characteristic fields for dynamic rendering (needed for updated template)
    characteristic_fields = []
    if tab == "edit":
        char_fields_qs = DataField.objects.filter(category='characteristic').order_by('name')
        
        # Get pending contribution slugs for this council  
        pending_slugs_list = list(Contribution.objects.filter(
            council=council, status="pending"
        ).values_list("field__slug", flat=True))
        
        for field in char_fields_qs:
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
                'is_pending': field.slug in pending_slugs_list
            })

    # Get meta fields for council detail header display (optimized with single query)
    meta_fields = []
    population_in_meta = False
    
    # Get fields configured to show in meta bar
    meta_data_fields = DataField.objects.filter(
        show_in_meta=True,
        category='characteristic'
    ).order_by('display_order', 'name')
    
    # Create a lookup map of characteristics for this council
    characteristics_map = {}
    characteristics_qs = CouncilCharacteristic.objects.filter(
        council=council,
        field__show_in_meta=True,
        field__category='characteristic'
    ).select_related('field')
    
    for characteristic in characteristics_qs:
        characteristics_map[characteristic.field.id] = characteristic
    
    # Process meta fields with the preloaded data
    for field in meta_data_fields:
        characteristic = characteristics_map.get(field.id)
        
        if characteristic and characteristic.value:
            # Format the value using the field's display format
            if field.meta_display_format and '{value}' in field.meta_display_format:
                if field.content_type == 'integer' and characteristic.value.isdigit():
                    # Format numbers with commas
                    formatted_value = field.meta_display_format.format(
                        value=f"{int(characteristic.value):,}"
                    )
                else:
                    formatted_value = field.meta_display_format.format(
                        value=characteristic.value
                    )
            else:
                formatted_value = characteristic.value
            
            meta_fields.append({
                'field': field,
                'value': characteristic.value,
                'formatted_value': formatted_value
            })
            
            # Track if population is in meta fields
            if field.slug == 'population':
                population_in_meta = True
        elif field.slug == 'population' and council.latest_population is not None:
            # Fallback to council.latest_population if no characteristic exists
            if field.meta_display_format and '{value}' in field.meta_display_format:
                formatted_value = field.meta_display_format.format(
                    value=f"{council.latest_population:,}"
                )
            else:
                formatted_value = f"{council.latest_population:,}"
                
            meta_fields.append({
                'field': field,
                'value': str(council.latest_population),
                'formatted_value': formatted_value
            })
            population_in_meta = True
    
    context = {
        "council": council,
        "figures": figures,
        "counters": counters,
        "years": years,
        "selected_year": selected_year,
        "default_counter_slugs": default_slugs,
        "tab": tab,
        "focus": focus,
        "edit_years": edit_years,
        "edit_selected_year": edit_selected_year,
        "edit_figures": edit_figures,
        "missing_characteristic_page": missing_characteristic_page,
        "missing_characteristic_paginator": missing_characteristic_paginator,
        "characteristic_fields": characteristic_fields,
        # Set of field slugs with pending contributions so the template
        # can show a "pending confirmation" notice in place of the form.
        "pending_slugs": set(
            Contribution.objects.filter(council=council, status="pending").values_list(
                "field__slug", flat=True
            )
        ),
        # Keys of the form "slug-year_id" indicating pending contributions
        # for specific figure/year pairs. This allows the edit interface to
        # disable inputs when a submission is awaiting moderation.
        "pending_pairs": set(
            f"{slug}-{year_id or 'none'}"
            for slug, year_id in Contribution.objects.filter(
                council=council, status="pending"
            ).values_list("field__slug", "year_id")
        ),
        "is_following": is_following,
        "is_favourited": is_favourited,
        "share_data": share_data,
        # Administrative messaging
        "administrative_messages": administrative_messages,
        "recent_merge_activity": recent_merge_activity,
        "recent_flag_activity": recent_flag_activity,
        # Dynamic meta fields for header display
        "meta_fields": meta_fields,
        "population_in_meta": population_in_meta,
    }

    # Handle AJAX POST requests for saving financial figures
    if request.method == "POST" and request.headers.get('Content-Type') == 'application/json':
        try:
            import json
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'save_figures':
                changes = data.get('changes', [])
                year_id = data.get('year')
                
                # Validate that user is authenticated (you may want stricter permissions)
                if not request.user.is_authenticated:
                    return JsonResponse({'success': False, 'error': 'Authentication required'})
                
                saved_count = 0
                errors = []
                
                for change in changes:
                    field_slug = change.get('field')
                    value = change.get('value')
                    data_type = change.get('type')
                    
                    try:
                        # Find the field
                        field = DataField.objects.get(slug=field_slug)
                        year = FinancialYear.objects.get(id=year_id)
                        
                        # Validate and convert value based on type
                        if data_type == 'monetary' or data_type == 'integer':
                            value = float(value) if value else 0
                        elif data_type == 'percentage':
                            value = float(value) if value else 0
                            if value > 100:
                                errors.append(f"{field.name}: Percentage cannot exceed 100%")
                                continue
                          # Create or update the financial figure
                        if field.category == 'financial':
                            figure, created = FinancialFigure.objects.get_or_create(
                                council=council,
                                field=field,
                                year=year,
                                defaults={'value': value}
                            )
                            
                            if not created:
                                figure.value = value
                                figure.save()
                        else:
                            # Handle characteristics (no year)
                            characteristic, created = CouncilCharacteristic.objects.get_or_create(
                                council=council,
                                field=field,
                                defaults={'value': str(value), 'updated_by': request.user}
                            )
                            
                            if not created:
                                characteristic.value = str(value)
                                characteristic.updated_by = request.user
                                characteristic.save()
                        
                        saved_count += 1
                        
                    except (DataField.DoesNotExist, FinancialYear.DoesNotExist) as e:
                        errors.append(f"Invalid field or year: {str(e)}")
                    except ValueError as e:
                        errors.append(f"Invalid value for {field_slug}: {str(e)}")
                    except Exception as e:
                        errors.append(f"Error saving {field_slug}: {str(e)}")
                
                # Invalidate counter cache for this council and year if any changes were saved
                if saved_count > 0:
                    from django.core.cache import cache
                    cache_key = f"counter_values:{council.slug}:{year.label}"
                    cache.delete(cache_key)
                    
                    # Also invalidate cache for characteristics changes (affects all years)
                    # Check if any characteristics were changed by looking at the changes
                    characteristic_changes = any(
                        DataField.objects.filter(slug=change.get('field')).first() and 
                        DataField.objects.filter(slug=change.get('field')).first().category == 'characteristic'
                        for change in changes
                    )
                    if characteristic_changes:
                        for year_obj in FinancialYear.objects.all():
                            cache_key_all = f"counter_values:{council.slug}:{year_obj.label}"
                            cache.delete(cache_key_all)
                
                return JsonResponse({
                    'success': len(errors) == 0,
                    'saved_count': saved_count,
                    'errors': errors,
                    'message': f"Saved {saved_count} changes" + (f" with {len(errors)} errors" if errors else "")
                })
            
            return JsonResponse({'success': False, 'error': 'Invalid action'})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})    # Always use the main council detail template, which handles tab switching internally
    template_name = "council_finance/council_detail.html"

    return render(request, template_name, context)


# ---------------------------------------------------------------------------
# Council change log view
# ---------------------------------------------------------------------------
def council_change_log(request, slug):
    """Show a paginated list of approved changes for this council."""
    council = get_object_or_404(Council, slug=slug)
    logs = (
        DataChangeLog.objects.filter(council=council)
        .select_related("contribution__user", "field", "year")
        .order_by("-created")
    )
    paginator = Paginator(logs, 20)
    page = paginator.get_page(request.GET.get("page"))
    context = {
        "council": council,
        "page_obj": page,
        "paginator": paginator,
        "tab": "log",
    }
    return render(request, "council_finance/council_log.html", context)


# Additional views for common site pages


def leaderboards(request):
    """Display leaderboards for both contributors and council financial metrics."""
    from council_finance.services.leaderboard_service import LeaderboardService
    from council_finance.services.export_service import ExportService
    
    # Handle export requests
    export_format = request.GET.get('export')
    if export_format:
        try:
            service = LeaderboardService()
            export_service = ExportService()
            
            category = request.GET.get('category', 'contributors')
            year = request.GET.get('year')
            per_capita = request.GET.get('per_capita', 'false') == 'true'
            reverse_sort = request.GET.get('reverse', 'false') == 'true'
            
            leaderboard_data = service.get_leaderboard(category, year, per_capita, reverse_sort=reverse_sort)
            if leaderboard_data:
                return export_service.export_leaderboard(
                    leaderboard_data.to_dict(),
                    export_format
                )
        except Exception as e:
            logger.error(f"Export failed: {e}")
            messages.error(request, f"Export failed: {str(e)}")
    
    # Get leaderboard data using the service
    service = LeaderboardService()
    
    # Get parameters
    category = request.GET.get('category', 'contributors')
    per_capita = request.GET.get('per_capita', 'false') == 'true'
    year_label = request.GET.get('year', None)
    reverse_sort = request.GET.get('reverse', 'false') == 'true'
    
    # Get leaderboard data
    leaderboard_data = service.get_leaderboard(category, year_label, per_capita, reverse_sort=reverse_sort)
    
    # Available financial years for dropdown
    available_years = FinancialYear.objects.order_by('-start_date').values('label', 'is_forecast')
    
    # Get export service capabilities
    export_service = ExportService()
    
    context = {
        'leaderboard_data': leaderboard_data,
        'categories': service.CATEGORIES,
        'current_category': category,
        'current_category_info': service.CATEGORIES.get(category, service.CATEGORIES['contributors']),
        'per_capita': per_capita,
        'year_label': year_label,
        'reverse_sort': reverse_sort,
        'available_years': list(available_years),
        'show_contributors': category == 'contributors',
        'supported_export_formats': export_service.supported_formats,
    }
    
    return render(request, "council_finance/leaderboards.html", context)




def following(request):
    """
    Feed page showing activity logs from councils.
    
    For authenticated users: Shows activity from councils they follow
    For anonymous users: Shows a sample feed with latest update from each council
    """
    from django.db.models import Count, Prefetch, Max
    import json
    
    # Import models we'll need
    from council_finance.models import ActivityLogComment
    from council_finance.services.activity_story_generator import ActivityStoryGenerator
    
    # Initialize story generator
    story_generator = ActivityStoryGenerator()
    
    # Initialize variables
    followed_councils = None
    follows_by_type = {'council': []}
    total_follows = 0
    is_sample_feed = False
    
    if request.user.is_authenticated:
        # Get user's followed councils using the existing CouncilFollow model
        followed_councils = CouncilFollow.objects.filter(user=request.user).select_related('council')
        
        # Group follows by type (only councils for now)
        follows_by_type = {
            'council': [
                {
                    'id': follow.id,
                    'object': follow.council,
                    'created_at': follow.created_at,
                }
                for follow in followed_councils
            ]
        }
        
        # Get basic statistics
        total_follows = followed_councils.count()
        
        # Get suggested councils (active councils user doesn't follow, ordered by most followed)
        followed_council_ids = followed_councils.values_list('council_id', flat=True)
        suggested_councils = Council.objects.filter(
            status='active'
        ).exclude(
            id__in=followed_council_ids
        ).annotate(
            follower_count=Count('followed_by')
        ).order_by('-follower_count')[:5]
    else:
        # For anonymous users, suggest popular councils
        suggested_councils = Council.objects.filter(
            status='active'
        ).annotate(
            follower_count=Count('followed_by')
        ).order_by('-follower_count')[:5]
    
    # Get ActivityLog entries
    feed_updates = []
    
    if request.user.is_authenticated:
        if followed_councils and followed_councils.exists():
            # Authenticated user with follows - show their personalized feed
            activity_logs = ActivityLog.objects.filter(
                related_council__in=followed_councils.values_list('council_id', flat=True)
            ).select_related(
                'related_council', 'user'
            ).prefetch_related(
                Prefetch(
                    'following_comments',
                    queryset=ActivityLogComment.objects.filter(
                        is_approved=True, parent=None
                    ).select_related('user').order_by('created_at')
                )
            ).annotate(
                comment_count=Count('following_comments', filter=models.Q(following_comments__is_approved=True))
            ).order_by('-created')[:50]  # Latest 50 activities
        else:
            # Authenticated user with no follows - show empty state, not sample feed
            activity_logs = ActivityLog.objects.none()
    else:
        # For anonymous users, get the latest activity from each council (sample feed)
        is_sample_feed = True
        # First, get the latest activity log ID for each council
        from django.db.models import Subquery, OuterRef
        
        latest_activities = ActivityLog.objects.filter(
            related_council=OuterRef('pk'),
            related_council__status='active'
        ).order_by('-created').values('id')[:1]
        
        councils_with_latest = Council.objects.filter(
            status='active'
        ).annotate(
            latest_activity_id=Subquery(latest_activities)
        ).exclude(
            latest_activity_id__isnull=True
        ).values_list('latest_activity_id', flat=True)[:20]  # Show sample from 20 councils
        
        # Get the actual activity logs
        activity_logs = ActivityLog.objects.filter(
            id__in=councils_with_latest
        ).select_related(
            'related_council', 'user'
        ).prefetch_related(
            Prefetch(
                'following_comments',
                queryset=ActivityLogComment.objects.filter(
                    is_approved=True, parent=None
                ).select_related('user').order_by('created_at')
            )
        ).annotate(
            comment_count=Count('following_comments', filter=models.Q(following_comments__is_approved=True))
        ).order_by('-created')
    
    # Transform ActivityLog entries into feed update format with AI stories
    for activity_log in activity_logs:
            # Generate AI story for this activity
            story_data = story_generator.generate_story(activity_log)
            
            feed_updates.append({
                'id': f'activity_{activity_log.id}',
                'activity_log_id': activity_log.id,  # Numeric ID for API calls
                'type': 'activity_log',
                'activity_log': activity_log,
                'title': story_data.get('title', f"{activity_log.get_activity_type_display()}: {activity_log.description}"),
                'story': story_data.get('story', activity_log.description),
                'summary': story_data.get('summary', activity_log.description),
                'field_name': story_data.get('field_name'),
                'field_slug': story_data.get('field_slug'),
                'value': story_data.get('value'),
                'context': story_data.get('context', {}),
                'year': story_data.get('year'),
                'council': activity_log.related_council,
                'user': activity_log.user,
                'created_at': activity_log.created,
                'comment_count': activity_log.comment_count,
                'activity_type': activity_log.activity_type,
                'description': activity_log.description,
                'details': activity_log.details,
            })
    
    # Calculate recent updates count
    recent_updates_count = len(feed_updates)
    
    # Create trending and priority data
    trending_councils = []  # No trending system yet
    trending_lists = []  # No trending system yet
    priority_stats = {'high': 0, 'medium': 0, 'low': 0}  # No priority system yet
    
    # Create minimal preferences for JavaScript
    preferences_data = {
        'algorithm': 'chronological',
        'show_financial_updates': True,
        'show_contributions': True,
        'show_council_news': True,
        'show_list_changes': True,
        'show_system_updates': False,
        'show_achievements': True,
    }
    
    # Prepare context
    context = {
        'feed_updates': feed_updates,
        'follows_by_type': follows_by_type,
        'trending_councils': trending_councils,
        'trending_lists': trending_lists,
        'suggested_councils': suggested_councils,
        'total_follows': total_follows,
        'priority_stats': priority_stats,
        'recent_updates_count': recent_updates_count,
        'current_algorithm': 'chronological',
        'current_filter': 'all',
        'algorithm_choices': [
            ('chronological', 'Chronological (Newest First)'),
            ('engagement', 'High Engagement First'),
            ('priority', 'Your Priorities First'),
            ('mixed', 'Smart Mix (Recommended)'),
        ],
        'filter_choices': [
            ('all', 'All Updates'),
            ('financial', 'Financial Updates'),
            ('contributions', 'Contributions'),
            ('councils', 'Council Updates'),
            ('lists', 'List Updates'),
        ],
        # For JavaScript compatibility
        'preferences_json': json.dumps(preferences_data),
        'is_sample_feed': is_sample_feed,  # Indicate if this is a sample feed for anonymous users
    }
    
    return render(request, "council_finance/following.html", context)


# Flagging System Views

@login_required
@require_POST
def flag_content(request):
    """Flag content for community review."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from django.contrib.contenttypes.models import ContentType
    from council_finance.models import Flag, Contribution, Council
    from council_finance.services.flagging_services import FlaggingService
    
    try:
        content_type_id = request.POST.get('content_type')
        object_id = request.POST.get('object_id')
        flag_type = request.POST.get('flag_type')
        description = request.POST.get('description', '').strip()
        priority = request.POST.get('priority', 'medium')
        
        if not all([content_type_id, object_id, flag_type, description]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required'
            }, status=400)
        
        # Get the content object
        content_type = get_object_or_404(ContentType, id=content_type_id)
        model_class = content_type.model_class()
        content_object = get_object_or_404(model_class, id=object_id)
        
        # Get user's IP address
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
        
        # Flag the content
        result = FlaggingService.flag_content(
            user=request.user,
            content_object=content_object,
            flag_type=flag_type,
            description=description,
            priority=priority,
            ip_address=ip_address
        )
        
        if result['success']:
            message = "Thank you for flagging this content. It will be reviewed by moderators."
            if result['auto_escalated']:
                message += " This content has been escalated for immediate review."
            
            return JsonResponse({
                'success': True,
                'message': message,
                'flag_id': result['flag'].id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error flagging content: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while submitting your flag'
        }, status=500)


@login_required
def flagged_content_list(request):
    """View flagged content for moderation."""
    from council_finance.services.flagging_services import FlaggingService
    from council_finance.models import FlaggedContent
    
    # Check permissions
    if not request.user.is_superuser and (not hasattr(request.user, 'profile') or request.user.profile.tier.level < 3):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    status_filter = request.GET.get('status', 'open')
    priority_filter = request.GET.get('priority')
    content_type_filter = request.GET.get('content_type')
    search_filter = request.GET.get('search')
    
    flagged_content = FlaggingService.get_flagged_content(
        status=status_filter,
        content_type=content_type_filter,
        limit=50
    )
    
    # Apply additional filters manually if the service doesn't support them
    if priority_filter:
        # Filter by priority from associated flags since FlaggedContent doesn't have priority directly
        filtered_content = []
        for item in flagged_content:
            # Get flags for this content to check priority
            flags = item.flags.all() if hasattr(item, 'flags') else []
            if any(flag.priority == priority_filter for flag in flags):
                filtered_content.append(item)
        flagged_content = filtered_content
    
    if search_filter:
        flagged_content = [item for item in flagged_content if search_filter.lower() in str(item.content_object).lower()]
    
    # Get counts for statistics (using correct field names)
    total_count = FlaggedContent.objects.count()
    open_count = FlaggedContent.objects.filter(is_resolved=False, is_under_review=False).count()
    resolved_count = FlaggedContent.objects.filter(is_resolved=True).count()
    
    # Critical count - need to count flags with critical priority
    from council_finance.models import Flag
    critical_count = Flag.objects.filter(priority='critical', status='open').values('content_type', 'object_id').distinct().count()
    
    context = {
        'flagged_content': flagged_content,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'content_type_filter': content_type_filter,
        'search_filter': search_filter,
        'total_count': total_count,
        'open_count': open_count,
        'resolved_count': resolved_count,
        'critical_count': critical_count,
        'moderation_stats': FlaggingService.get_moderation_stats()
    }
    
    return render(request, 'council_finance/flagged_content.html', context)


@login_required
@require_POST
def resolve_flag(request, flag_id):
    """Resolve a flag."""
    from council_finance.models import Flag
    from council_finance.services.flagging_services import FlaggingService
    
    # Check permissions
    if not request.user.is_superuser and (not hasattr(request.user, 'profile') or request.user.profile.tier.level < 3):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        flag = get_object_or_404(Flag, id=flag_id)
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'resolve':
            FlaggingService.resolve_flag(flag, request.user, notes)
            message = "Flag resolved successfully"
        elif action == 'dismiss':
            FlaggingService.dismiss_flag(flag, request.user, notes)
            message = "Flag dismissed successfully"
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error resolving flag: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error resolving flag'
        }, status=500)


@login_required
@require_POST
def take_content_action(request, flagged_content_id):
    """Take moderation action on flagged content (edit, remove, reinstate)."""
    from council_finance.models import FlaggedContent
    from council_finance.services.flagging_services import FlaggingService
    
    # Check permissions
    if not request.user.is_superuser and (not hasattr(request.user, 'profile') or request.user.profile.tier.level < 3):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        flagged_content = get_object_or_404(FlaggedContent, id=flagged_content_id)
        action = request.POST.get('action')
        
        if action not in ['edit', 'remove', 'reinstate']:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Prepare action parameters
        kwargs = {}
        if action == 'edit':
            kwargs['new_value'] = request.POST.get('new_value', '').strip()
            if not kwargs['new_value']:
                return JsonResponse({'error': 'New value is required for edit action'}, status=400)
        
        # Execute the action
        result = FlaggingService.take_content_action(
            flagged_content=flagged_content,
            action=action,
            moderator=request.user,
            **kwargs
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error taking content action: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error executing action'
        }, status=500)


@login_required
@require_POST
def take_user_action(request, user_id):
    """Take moderation action on a flagged user (release, restrict, suspend, ban)."""
    from django.contrib.auth.models import User
    from council_finance.services.flagging_services import FlaggingService
    
    # Check permissions
    if not request.user.is_superuser and (not hasattr(request.user, 'profile') or request.user.profile.tier.level < 4):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        target_user = get_object_or_404(User, id=user_id)
        action = request.POST.get('action')
        
        if action not in ['release', 'restrict', 'suspend', 'ban']:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Prepare action parameters
        kwargs = {}
        if action in ['restrict', 'suspend']:
            duration_days = request.POST.get('duration_days')
            if duration_days:
                try:
                    kwargs['duration_days'] = int(duration_days)
                except ValueError:
                    return JsonResponse({'error': 'Invalid duration'}, status=400)
        
        if action == 'ban':
            duration_days = request.POST.get('duration_days')
            if duration_days and duration_days != 'permanent':
                try:
                    kwargs['duration_days'] = int(duration_days)
                except ValueError:
                    return JsonResponse({'error': 'Invalid duration'}, status=400)
        
        kwargs['reason'] = request.POST.get('reason', '').strip()
        kwargs['notes'] = request.POST.get('notes', '').strip()
        
        if action == 'restrict':
            kwargs['restriction_type'] = request.POST.get('restriction_type', 'contribution_limit')
        
        # Execute the action
        result = FlaggingService.take_user_action(
            user=target_user,
            action=action,
            moderator=request.user,
            **kwargs
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error taking user action: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error executing action'
        }, status=500)


@login_required
def my_flags(request):
    """View user's own flags."""
    from council_finance.services.flagging_services import FlaggingService
    
    status_filter = request.GET.get('status')
    flags = FlaggingService.get_user_flags(request.user, status_filter)
    
    context = {
        'flags': flags,
        'status_filter': status_filter
    }
    
    return render(request, 'council_finance/my_flags.html', context)


# Following System API Endpoints

@csrf_exempt
@require_http_methods(["POST"])
def follow_item_api(request):
    """API endpoint to follow any item (Council, List, User, Field)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        import json
        from django.contrib.contenttypes.models import ContentType
        from council_finance.services.following_services import FollowService
        
        data = json.loads(request.body)
        content_type_id = data.get('content_type_id')
        object_id = data.get('object_id')
        priority = data.get('priority', 'normal')
        email_notifications = data.get('email_notifications', True)
        push_notifications = data.get('push_notifications', True)
        
        if not content_type_id or not object_id:
            return JsonResponse({"error": "Missing content_type_id or object_id"}, status=400)
        
        content_type = ContentType.objects.get(id=content_type_id)
        model_class = content_type.model_class()
        item = model_class.objects.get(id=object_id)
        
        follow = FollowService.follow_item(
            user=request.user,
            item=item,
            priority=priority,
            email_notifications=email_notifications,
            push_notifications=push_notifications
        )
        
        if follow:
            return JsonResponse({
                "status": "success",
                "message": f"Successfully following {item}",
                "follow_id": follow.id,
                "follower_count": FollowService.get_follower_count(item)
            })
        else:
            return JsonResponse({
                "status": "info",
                "message": "Already following this item"
            })
    
    except Exception as e:
        logger.error(f"Error in follow_item_api: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unfollow_item_api(request):
    """API endpoint to unfollow any item."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        import json
        from django.contrib.contenttypes.models import ContentType
        from council_finance.services.following_services import FollowService
        
        data = json.loads(request.body)
        content_type_id = data.get('content_type_id')
        object_id = data.get('object_id')
        
        if not content_type_id or not object_id:
            return JsonResponse({"error": "Missing content_type_id or object_id"}, status=400)
        
        content_type = ContentType.objects.get(id=content_type_id)
        model_class = content_type.model_class()
        item = model_class.objects.get(id=object_id)
        
        success = FollowService.unfollow_item(user=request.user, item=item)
        
        return JsonResponse({
            "status": "success" if success else "info",
            "message": "Successfully unfollowed" if success else "Was not following",
            "follower_count": FollowService.get_follower_count(item)
        })
    
    except Exception as e:
        logger.error(f"Error in unfollow_item_api: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def interact_with_update_api(request, update_id):
    """API endpoint for interacting with feed updates (like, share, etc.)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        import json
        from council_finance.models import FeedUpdate
        from council_finance.services.following_services import EngagementService
        
        data = json.loads(request.body)
        interaction_type = data.get('interaction_type')
        action = data.get('action', 'add')  # 'add' or 'remove'
        
        if interaction_type not in ['like', 'dislike', 'share', 'bookmark', 'flag']:
            return JsonResponse({"error": "Invalid interaction type"}, status=400)
        
        update = FeedUpdate.objects.get(id=update_id)
        update.increment_views()  # Track that user viewed this update
        
        if action == 'add':
            interaction = EngagementService.record_interaction(
                user=request.user,
                update=update,
                interaction_type=interaction_type,
                notes=data.get('notes', '')
            )
            message = f"Successfully {interaction_type}d update"
        else:
            success = EngagementService.remove_interaction(
                user=request.user,
                update=update,
                interaction_type=interaction_type
            )
            message = f"Removed {interaction_type}" if success else f"Was not {interaction_type}d"
        
        # Get updated counts
        update.refresh_from_db()
        
        return JsonResponse({
            "status": "success",
            "message": message,
            "counts": {
                "likes": update.like_count,
                "comments": update.comment_count,
                "shares": update.share_count,
                "views": update.view_count
            }
        })
    
    except FeedUpdate.DoesNotExist:
        return JsonResponse({"error": "Update not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in interact_with_update_api: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def comment_on_update_api(request, update_id):
    """API endpoint for commenting on feed updates."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        import json
        from council_finance.models import FeedUpdate, FeedComment
        
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')  # For replies
        
        if not content:
            return JsonResponse({"error": "Comment content is required"}, status=400)
        
        if len(content) > 1000:
            return JsonResponse({"error": "Comment too long (max 1000 characters)"}, status=400)
        
        update = FeedUpdate.objects.get(id=update_id)
        
        # Create comment
        comment = FeedComment.objects.create(
            update=update,
            user=request.user,
            content=content,
            parent_id=parent_id if parent_id else None
        )
        
        # Update comment count on the update
        FeedUpdate.objects.filter(id=update_id).update(comment_count=models.F('comment_count') + 1)
        
        return JsonResponse({
            "status": "success",
            "message": "Comment added successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "author": comment.user.get_full_name() or comment.user.username,
                "created_at": comment.created_at.isoformat(),
                "reply_count": 0
            },
            "comment_count": update.comment_count + 1
        })
    
    except FeedUpdate.DoesNotExist:
        return JsonResponse({"error": "Update not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in comment_on_update_api: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_feed_preferences_api(request):
    """API endpoint to update user's feed preferences."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        import json
        from council_finance.models import UserFeedPreferences
        
        data = json.loads(request.body)
        
        preferences, created = UserFeedPreferences.objects.get_or_create(
            user=request.user
        )
        
        # Update preferences
        if 'algorithm' in data:
            preferences.algorithm = data['algorithm']
        if 'show_financial_updates' in data:
            preferences.show_financial_updates = data['show_financial_updates']
        if 'show_contributions' in data:
            preferences.show_contributions = data['show_contributions']
        if 'show_council_news' in data:
            preferences.show_council_news = data['show_council_news']
        if 'show_list_changes' in data:
            preferences.show_list_changes = data['show_list_changes']
        if 'show_system_updates' in data:
            preferences.show_system_updates = data['show_system_updates']
        if 'show_achievements' in data:
            preferences.show_achievements = data['show_achievements']
        if 'email_notifications' in data:
            preferences.email_notifications = data['email_notifications']
        if 'push_notifications' in data:
            preferences.push_notifications = data['push_notifications']
        
        preferences.save()
        
        return JsonResponse({
            "status": "success",
            "message": "Preferences updated successfully"
        })
    
    except Exception as e:
        logger.error(f"Error in update_feed_preferences_api: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@require_http_methods(["GET"])
def get_feed_updates_api(request):
    """API endpoint to get feed updates with pagination."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        from council_finance.services.following_services import FeedService
        import json
        
        algorithm = request.GET.get('algorithm', 'mixed')
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        offset = (page - 1) * limit
        
        feed_updates = FeedService.get_personalized_feed(
            user=request.user,
            limit=limit + offset,
            algorithm=algorithm
        )[offset:offset + limit]
        
        updates_data = []
        for update in feed_updates:
            updates_data.append({
                "id": update.id,
                "title": update.title,
                "message": update.message,
                "update_type": update.update_type,
                "created_at": update.created_at.isoformat(),
                "author": update.author.get_full_name() if update.author else None,
                "source_object_name": update.get_related_object_name(),
                "counts": {
                    "likes": update.like_count,
                    "comments": update.comment_count,
                    "shares": update.share_count,
                    "views": update.view_count
                },
                "rich_content": update.rich_content
            })
        
        return JsonResponse({
            "status": "success",
            "updates": updates_data,
            "page": page,
            "has_more": len(feed_updates) == limit
        })
    
    except Exception as e:
        logger.error(f"Error in get_feed_updates_api: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def contribute(request):
    """Show a modern, real-time contribute interface with AJAX editing."""
    
    from council_finance.models import DataIssue, UserProfile, Contribution
    from council_finance.data_quality import assess_data_issues

    # God Mode: Mark DataIssue as invalid
    if request.method == "POST" and request.user.is_superuser and "mark_invalid" in request.POST:
        issue_id = request.POST.get("issue_id")
        DataIssue.objects.filter(id=issue_id).delete()
        return JsonResponse({"status": "ok", "message": "Issue marked invalid and removed."})

    # Get initial data for the page - only show active councils in contribution queues
    characteristic_qs = (
        DataIssue.objects.filter(issue_type="missing", field__category="characteristic", council__status="active")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )

    financial_qs = (
        DataIssue.objects.filter(issue_type="missing", council__status="active")
        .exclude(field__category="characteristic")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )

    # Use smaller page sizes for the initial load
    from django.core.paginator import Paginator
    char_paginator = Paginator(characteristic_qs, 25)
    char_page = char_paginator.get_page(1)

    financial_paginator = Paginator(financial_qs, 25)
    financial_page = financial_paginator.get_page(1)

    my_contribs = (
        Contribution.objects.filter(user=request.user).select_related("council", "field")
        if request.user.is_authenticated
        else []
    )

    points = None
    rank = None
    if request.user.is_authenticated:
        profile = request.user.profile
        points = profile.points
        rank = UserProfile.objects.filter(points__gt=points).count() + 1

    # Get financial years for the year filter dropdown
    financial_years = list(FinancialYear.objects.order_by('-label'))

    return render(
        request,
        "council_finance/contribute_new.html",
        {
            "page_obj": char_page,
            "paginator": char_paginator,
            "missing_financial_page": financial_page,
            "missing_financial_paginator": financial_paginator,
            "my_contribs": my_contribs,
            "points": points,
            "rank": rank,
            "financial_years": financial_years,
        },
    )


@require_GET
def contribute_stats(request):
    """Return statistics for the contribute page sidebar."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    
    from council_finance.models import DataIssue, Contribution
    
    # Get detailed breakdown of missing data by category - only for active councils
    # Show ALL missing data but with smart organization and prioritization
    missing_total = DataIssue.objects.filter(issue_type='missing', council__status='active').count()
    missing_characteristics = DataIssue.objects.filter(
        issue_type='missing', 
        field__category='characteristic',
        council__status='active'
    ).count()
    missing_financial = DataIssue.objects.filter(
        issue_type='missing',
        council__status='active'
    ).exclude(
        field__category='characteristic'
    ).count()
    
    # Get priority breakdown for enhanced user experience
    try:
        from council_finance.smart_data_quality import get_data_collection_priorities
        data_priorities = get_data_collection_priorities()
        relevant_year_ids = {y.id for y in data_priorities.get('relevant_years', [])}
        
        # Count high-priority financial data (current/relevant years)
        high_priority_financial = DataIssue.objects.filter(
            issue_type='missing',
            council__status='active',
            year_id__in=relevant_year_ids
        ).exclude(field__category='characteristic').count() if relevant_year_ids else 0
        
        # Calculate priority stats for enhanced UX
        priority_stats = {
            'high_priority_financial': high_priority_financial,
            'other_financial': missing_financial - high_priority_financial,
            'current_year_label': data_priorities.get('current_year', {}).get('label') if data_priorities.get('current_year') else None,
            'relevant_year_count': len(relevant_year_ids)
        }
    except Exception:
        # Fallback if smart system has issues
        priority_stats = {
            'high_priority_financial': 0,
            'other_financial': missing_financial,
            'current_year_label': None,
            'relevant_year_count': 0
        }
    
    stats = {
        'missing': missing_total,
        'missing_characteristics': missing_characteristics,
        'missing_financial': missing_financial,
        'pending': Contribution.objects.filter(status='pending').count(),
        'suspicious': DataIssue.objects.filter(issue_type='suspicious').count(),
        # Enhanced priority information
        'priority_stats': priority_stats,
    }
    
    return JsonResponse(stats)


@require_POST  
def contribute_submit(request):
    """Handle AJAX contribution submissions from the quick edit modal."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        # Extract form data
        council_id = request.POST.get("council")
        field_slug = request.POST.get("field") 
        year_id = request.POST.get("year")
        value = request.POST.get("value", "").strip()
        
        if not all([council_id, field_slug, value]):
            return JsonResponse({"error": "Missing required fields"}, status=400)
        
        # Validate council
        try:
            council = Council.objects.get(slug=council_id)
        except Council.DoesNotExist:
            return JsonResponse({"error": "Invalid council"}, status=400)
        
        # Validate field
        try:
            field = DataField.objects.get(slug=field_slug)
        except DataField.DoesNotExist:
            return JsonResponse({"error": "Invalid field"}, status=400)
        
        # Validate year (optional for characteristics)
        year = None
        if year_id:
            try:
                year = FinancialYear.objects.get(pk=year_id)
            except FinancialYear.DoesNotExist:
                return JsonResponse({"error": "Invalid year"}, status=400)
        
        # Check for existing pending contribution for this field/council/year
        existing = Contribution.objects.filter(
            user=request.user,
            council=council,
            field=field,
            year=year,
            status="pending"
        ).first()
        
        if existing:
            return JsonResponse({"error": "You already have a pending contribution for this data point"}, status=400)
        
        # Create the contribution
        contribution = Contribution.objects.create(
            user=request.user,
            council=council,
            field=field,
            year=year,
            value=value,
            ip_address=request.META.get('REMOTE_ADDR'),
            status="pending"
        )
        
        # Remove the corresponding DataIssue if it exists
        from council_finance.models import DataIssue
        DataIssue.objects.filter(
            council=council,
            field=field,
            year=year,
            issue_type="missing"
        ).delete()
        
        # Log the activity
        log_activity(
            request,
            council=council,
            activity="submit_contribution",
            action=f"submitted {field.name} for {council.name}",
            extra={
                "field_slug": field_slug,
                "year_label": year.label if year else None,
                "value": value,
                "contribution_id": contribution.id
            }
        )
        
        # Award points to user for contribution
        profile = request.user.profile
        profile.points += 5  # Base points for contribution
        profile.save()
        
        return JsonResponse({
            "message": f"Contribution submitted successfully for {field.name}",
            "status": "success",
            "contribution_id": contribution.id
        })
        
    except Exception as e:
        logger.error(f"Error in contribute_submit: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An error occurred while submitting your contribution"}, status=500)


def data_issues_table(request):
    """Return a page of data issues as HTML for the contribute tables."""
    try:
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return HttpResponseBadRequest("XHR required")

        from council_finance.models import DataIssue, Contribution
        from council_finance.data_quality import assess_data_issues

        issue_type = request.GET.get("type")
        
        # Handle frontend type mapping
        type_mapping = {
            "missing_characteristics": ("missing", "characteristic"),
            "missing_financial": ("missing", "financial"),
            "missing": ("missing", None),
            "suspicious": ("suspicious", None),
            "pending": ("pending", None),
        }
        
        if not issue_type:
            return HttpResponseBadRequest("missing type parameter")
            
        if issue_type not in type_mapping:
            return HttpResponseBadRequest(f"invalid type: {issue_type}")
        
        actual_type, auto_category = type_mapping[issue_type]

        search = request.GET.get("q", "").strip()
        category = request.GET.get("category") or auto_category
        order = request.GET.get("order", "council")
        direction = request.GET.get("dir", "asc")
        allowed = {"council": "council__name", "field": "field__name", "year": "year__label", "value": "value"}
        order_by = allowed.get(order, "council__name")
        if direction == "desc":
            order_by = f"-{order_by}"

        if request.GET.get("refresh"):
            assess_data_issues()
            
        if actual_type == "pending":
            qs = Contribution.objects.filter(status="pending").select_related("council", "field", "user", "year")
            if search:
                qs = qs.filter(Q(council__name__icontains=search) | Q(field__name__icontains=search))
            qs = qs.order_by(order_by)
        else:
            qs = DataIssue.objects.filter(issue_type=actual_type, council__status="active").select_related("council", "field", "year")
            if category == "characteristic":
                qs = qs.filter(field__category="characteristic")
            elif category == "financial":
                qs = qs.exclude(field__category="characteristic")
            if search:
                qs = qs.filter(Q(council__name__icontains=search) | Q(field__name__icontains=search))
            qs = qs.order_by(order_by)

        page_size = int(request.GET.get("page_size", 50))
        paginator = Paginator(qs, page_size)
        page = paginator.get_page(request.GET.get("page"))

        if actual_type == "pending":
            html = render_to_string(
                "council_finance/pending_table.html",
                {"page_obj": page, "paginator": paginator},
                request=request,
            )
        else:
            show_year = not (actual_type == "missing" and category == "characteristic")
            html = render_to_string(
                "council_finance/data_issues_table_enhanced.html",
                {
                    "page_obj": page,
                    "paginator": paginator,
                    "issue_type": actual_type,
                    "show_year": show_year,
                },
                request=request,
            )
        
        # Return additional pagination info for the enhanced UI
        return JsonResponse({
            "html": html,
            "total": paginator.count,
            "page": page.number,
            "page_size": page_size,
            "num_pages": paginator.num_pages
        })
        
    except Exception as e:
        import traceback
        return HttpResponseBadRequest(f"error: {str(e)}\n{traceback.format_exc()}")


def moderator_panel(request):
    """Admin god mode panel."""
    # TODO: Implement god mode
    return render(request, "council_finance/god_mode.html", {})


def activity_log_entries(request):
    """Get activity log entries."""
    from django.http import JsonResponse
    # TODO: Implement activity log
    return JsonResponse({"status": "success", "entries": []})


def activity_log_json(request, log_id):
    """Get activity log entry as JSON."""
    from django.http import JsonResponse
    # TODO: Implement activity log detail
    return JsonResponse({"status": "success", "log": {}})


def mark_issue_invalid(request, issue_id):
    """Mark a data issue as invalid."""
    from django.http import JsonResponse
    # TODO: Implement issue marking
    return JsonResponse({"status": "success", "message": "Issue marked invalid"})
def search_results(request):
    """Enhanced search results page that can also act as advanced search."""
    query = request.GET.get('q', '').strip()
    council_type = request.GET.get('type', '')
    nation = request.GET.get('nation', '')
    
    # Base queryset
    councils = Council.objects.select_related('council_type', 'council_nation').filter(status='active')
    
    # Apply search filters
    if query:
        councils = councils.filter(
            Q(name__icontains=query) | 
            Q(slug__icontains=query) |
            Q(council_type__name__icontains=query) |
            Q(council_nation__name__icontains=query)
        )
    
    if council_type:
        councils = councils.filter(council_type__name=council_type)
    
    if nation:
        councils = councils.filter(council_nation__name=nation)
    
    # Order by relevance (exact matches first, then partial matches)
    if query:
        from django.db.models import Case, When, Value, BooleanField
        from django.db.models.functions import Lower
        
        councils = councils.annotate(
            name_exact=Case(
                When(name__iexact=query, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ),
            name_starts=Case(
                When(name__istartswith=query, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        ).order_by('-name_exact', '-name_starts', 'name')
    else:
        councils = councils.order_by('name')
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(councils, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    available_types = Council.objects.values_list('council_type__name', flat=True).exclude(council_type__isnull=True).distinct().order_by('council_type__name')
    available_nations = Council.objects.values_list('council_nation__name', flat=True).exclude(council_nation__isnull=True).distinct().order_by('council_nation__name')
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'council_type': council_type,
        'nation': nation,
        'available_types': available_types,
        'available_nations': available_nations,
        'total_results': councils.count(),        'is_search_page': True,
    }
    
    return render(request, 'council_finance/search_results.html', context)




@csrf_exempt
@require_http_methods(["POST"])
def add_to_list(request, list_id):
    """Add a council to a specific list."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council_slug = request.POST.get('council')
        if not council_slug:
            return JsonResponse({"error": "Council slug required"}, status=400)
        
        council = Council.objects.get(slug=council_slug)
        council_list = request.user.council_lists.get(id=list_id)
        council_list.councils.add(council)
        
        return JsonResponse({"status": "success", "message": "Added to list"})
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except CouncilList.DoesNotExist:
        return JsonResponse({"error": "List not found"}, status=404)
    except Exception as e:
        logger.error(f"Error adding to list: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def remove_from_list(request, list_id):
    """Remove a council from a specific list."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council_slug = request.POST.get('council')
        if not council_slug:
            return JsonResponse({"error": "Council slug required"}, status=400)
        
        council = Council.objects.get(slug=council_slug)
        council_list = request.user.council_lists.get(id=list_id)
        council_list.councils.remove(council)
        
        return JsonResponse({"status": "success", "message": "Removed from list"})
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except CouncilList.DoesNotExist:
        return JsonResponse({"error": "List not found"}, status=404)
    except Exception as e:
        logger.error(f"Error removing from list: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def move_between_lists(request):
    """Move a council between lists."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council_slug = request.POST.get('council')
        source_list_id = request.POST.get('source_list')
        target_list_id = request.POST.get('target_list')
        
        if not all([council_slug, source_list_id, target_list_id]):
            return JsonResponse({"error": "Missing required parameters"}, status=400)
        
        council = Council.objects.get(slug=council_slug)
        source_list = request.user.council_lists.get(id=source_list_id)
        target_list = request.user.council_lists.get(id=target_list_id)
        
        source_list.councils.remove(council)
        target_list.councils.add(council)
        
        return JsonResponse({"status": "success", "message": "Moved between lists"})
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except CouncilList.DoesNotExist:
        return JsonResponse({"error": "List not found"}, status=404)
    except Exception as e:
        logger.error(f"Error moving between lists: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)



def add_to_compare(request, slug):
    """Add a council to the comparison basket."""
    try:
        council = Council.objects.get(slug=slug)
        compare_basket = request.session.get('compare_basket', [])
        
        if slug not in compare_basket:
            compare_basket.append(slug)
            request.session['compare_basket'] = compare_basket
            request.session.modified = True
        
        return JsonResponse({
            "status": "success",
            "message": "Added to comparison",
            "count": len(compare_basket)
        })
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except Exception as e:
        logger.error(f"Error adding to compare: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def remove_from_compare(request, slug):
    """Remove a council from the comparison basket."""
    try:
        compare_basket = request.session.get('compare_basket', [])
        
        if slug in compare_basket:
            compare_basket.remove(slug)
            request.session['compare_basket'] = compare_basket
            request.session.modified = True
        
        return JsonResponse({
            "status": "success",
            "message": "Removed from comparison",
            "count": len(compare_basket)
        })
    
    except Exception as e:
        logger.error(f"Error removing from compare: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def compare_row(request):
    """Get comparison row data for a specific field or council list."""
    try:
        field_slug = request.GET.get('field')
        year_filter = request.GET.get('year', '')  # Get year filter from request
        compare_basket = request.session.get('compare_basket', [])
        councils = Council.objects.filter(slug__in=compare_basket)
        
        if field_slug:
            # Return field comparison data as HTML for the detailed comparison table
            try:
                field = DataField.objects.get(slug=field_slug)
            except DataField.DoesNotExist:
                return JsonResponse({"error": "Field not found"}, status=404)
            
            # Get data for each council for this field
            values = []
            summary_data = {'total': 0, 'count': 0, 'highest': None, 'lowest': None, 'highest_council': '', 'lowest_council': ''}
            
            for council in councils:
                value = None
                display_value = "N/A"
                
                if field.category == 'characteristic':
                    # Get characteristic data
                    characteristic = CouncilCharacteristic.objects.filter(
                        council=council, field=field
                    ).first()
                    if characteristic:
                        value = characteristic.value
                        display_value = field.display_value(value)
                else:
                    # Get financial data with optional year filtering
                    financial_figures = FinancialFigure.objects.filter(
                        council=council, field=field
                    )
                    
                    # Apply year filter if specified
                    if year_filter:
                        financial_figures = financial_figures.filter(year__label=year_filter)
                    
                    financial_figure = financial_figures.order_by('-year__label').first()
                    
                    if financial_figure and financial_figure.value is not None:
                        value = financial_figure.value
                        display_value = field.display_value(str(value))
                        # Add year info to display if filtering by specific year
                        if year_filter:
                            display_value += f" ({financial_figure.year.label})"
                
                values.append(display_value)
                
                # Update summary for numeric fields
                if field.content_type in ['monetary', 'integer'] and value is not None:
                    try:
                        numeric_value = float(value)
                        summary_data['total'] += numeric_value
                        summary_data['count'] += 1
                        
                        if summary_data['highest'] is None or numeric_value > summary_data['highest']:
                            summary_data['highest'] = numeric_value
                            summary_data['highest_council'] = council.name
                        
                        if summary_data['lowest'] is None or numeric_value < summary_data['lowest']:
                            summary_data['lowest'] = numeric_value
                            summary_data['lowest_council'] = council.name
                    except (ValueError, TypeError):
                        pass
            
            # Format summary
            summary = None
            if summary_data['count'] > 0:
                if field.content_type == 'monetary':
                    summary = {
                        'total': f"£{summary_data['total']:,.0f}",
                        'average': f"£{summary_data['total']/summary_data['count']:,.0f}",
                        'highest': summary_data['highest_council'],
                        'lowest': summary_data['lowest_council']
                    }
                elif field.content_type == 'integer':
                    summary = {
                        'total': f"{summary_data['total']:,.0f}",
                        'average': f"{summary_data['total']/summary_data['count']:,.0f}",
                        'highest': summary_data['highest_council'],
                        'lowest': summary_data['lowest_council']
                    }
            
            # Render the row as HTML
            from django.template.loader import render_to_string
            html = render_to_string('council_finance/compare_row.html', {
                'field': field,
                'values': values,
                'summary': summary,
                'year_filter': year_filter
            }, request=request)
            
            response = HttpResponse(html)
            response['X-Field-Name'] = field.name
            return response
        
        else:
            # Return basic council data (legacy functionality)
            data = []
            for council in councils:
                data.append({
                    'slug': council.slug,
                    'name': council.name,
                    'type': council.council_type.name if council.council_type else '',
                    'nation': council.council_nation.name if council.council_nation else ''
                })
            
            return JsonResponse({
                "status": "success",
                "councils": data,
                "count": len(compare_basket)
            })
    
    except Exception as e:
        logger.error(f"Error getting compare row: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def compare_basket(request):
    """Show the comparison basket page."""
    compare_basket = request.session.get('compare_basket', [])
    councils = Council.objects.filter(slug__in=compare_basket)
    
    # Get all available fields for the dropdown
    all_fields = DataField.objects.all().order_by('category', 'name')
    
    # Get available financial years
    available_years = FinancialYear.objects.all().order_by('-label')
    
    context = {
        'councils': councils,
        'compare_basket': compare_basket,
        'field_choices': all_fields,
        'available_years': available_years,
        'rows': []
    }
    
    return render(request, 'council_finance/compare_basket.html', context)


def detailed_comparison(request):
    """Show detailed comparison table with field data for councils in basket."""
    compare_basket = request.session.get('compare_basket', [])
    councils = Council.objects.filter(slug__in=compare_basket)
    
    if not councils.exists():
        return redirect('compare_basket')
    
    # Handle saving as list if submitted
    if request.method == "POST" and request.POST.get('save_list'):
        if request.user.is_authenticated:
            list_name = request.POST.get('name', '').strip()
            if list_name:
                council_list = CouncilList.objects.create(
                    user=request.user,
                    name=list_name
                )
                council_list.councils.set(councils)
                return render(request, 'council_finance/comparison_basket.html', {
                    'councils': councils,
                    'save_success': True,
                    'list_name': list_name,
                    'field_choices': DataField.objects.all().order_by('category', 'name'),
                    'available_years': FinancialYear.objects.all().order_by('-label'),
                    'rows': []
                })
    
    # Get all available fields for the dropdown in the correct format
    all_fields = DataField.objects.all().order_by('category', 'name')
    
    # Get available financial years
    available_years = FinancialYear.objects.all().order_by('-label')
    
    context = {
        'councils': councils,
        'field_choices': all_fields,  # Template uses {% regroup field_choices by category %}
        'available_years': available_years,
        'rows': [],  # Rows will be loaded dynamically via AJAX
        'save_success': False
    }
    
    return render(request, 'council_finance/comparison_basket.html', context)


def clear_compare_basket(request):
    """Clear the comparison basket."""
    request.session['compare_basket'] = []
    request.session.modified = True
    
    return JsonResponse({
        "status": "success",
        "message": "Comparison basket cleared"
    })


@require_POST
def follow_council(request, slug):
    """Follow a council."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council = Council.objects.get(slug=slug)
        follow, created = CouncilFollow.objects.get_or_create(
            user=request.user,
            council=council
        )
        
        return JsonResponse({
            "status": "success",
            "message": "Following council",
            "following": True
        })
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except Exception as e:
        logger.error(f"Error following council: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@require_POST
def unfollow_council(request, slug):
    """Unfollow a council."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council = Council.objects.get(slug=slug)
        CouncilFollow.objects.filter(user=request.user, council=council).delete()
        
        return JsonResponse({
            "status": "success",
            "message": "Unfollowed council",
            "following": False
        })
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except Exception as e:
        logger.error(f"Error unfollowing council: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def like_update(request, update_id):
    """Like/unlike a council update."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        update = CouncilUpdate.objects.get(id=update_id)
        like, created = CouncilUpdateLike.objects.get_or_create(
            user=request.user,
            update=update
        )
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        
        # Update like count
        like_count = CouncilUpdateLike.objects.filter(update=update).count()
        
        return JsonResponse({
            "status": "success",
            "liked": liked,
            "like_count": like_count
        })
    
    except CouncilUpdate.DoesNotExist:
        return JsonResponse({"error": "Update not found"}, status=404)
    except Exception as e:
        logger.error(f"Error liking update: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def comment_update(request, update_id):
    """Comment on a council update."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    
    try:
        update = CouncilUpdate.objects.get(id=update_id)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({"error": "Comment content required"}, status=400)
        
        comment = CouncilUpdateComment.objects.create(
            user=request.user,
            update=update,
            content=content
        )
        
        return JsonResponse({
            "status": "success",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "author": comment.user.get_full_name() or comment.user.username,
                "created_at": comment.created_at.isoformat()
            }
        })
    
    except CouncilUpdate.DoesNotExist:
        return JsonResponse({"error": "Update not found"}, status=404)
    except Exception as e:
        logger.error(f"Error commenting on update: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


# @login_required  # Temporarily disabled for UI testing
def factoid_builder_react(request):
    """
    Serve the React-based Enhanced Factoid Builder interface
    """
    from council_finance.activity_logging import log_activity
    
    # Enhanced logging for factoid builder access
    try:
        log_activity(
            request, 
            activity="factoid_builder_access",
            log_type="user",
            action="page_load",
            extra={
                'session_id': request.session.session_key,
                'user_authenticated': request.user.is_authenticated,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
                'request_method': request.method,
                'request_path': request.path,
                'get_params': dict(request.GET),
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        context = {
            'page_title': 'Enhanced Factoid Builder',
            'page_description': 'Build dynamic factoids with real-time field integration',
            'api_base_url': '/api/factoid',
            'user': request.user,
        }
        
        logger.info(f"Factoid builder accessed by user {request.user.username if request.user.is_authenticated else 'anonymous'} from IP {request.META.get('REMOTE_ADDR', 'unknown')}")
        
        return render(request, 'council_finance/factoid_builder_react.html', context)
        
    except Exception as e:
        logger.error(f"Error in factoid_builder_react view: {str(e)}", exc_info=True)
        
        # Log the error for debugging
        log_activity(
            request,
            activity="factoid_builder_error", 
            log_type="system",
            action="view_error",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e),
                'user_id': request.user.id if request.user.is_authenticated else None,
                'session_id': request.session.session_key,
                'request_path': request.path,
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        # Still try to render the page
        context = {
            'page_title': 'Enhanced Factoid Builder',
            'page_description': 'Build dynamic factoids with real-time field integration',
            'api_base_url': '/api/factoid',
            'user': request.user,
        }
        return render(request, 'council_finance/factoid_builder_react.html', context)


# ============================================================================
# MY LISTS FUNCTIONALITY - Enhanced Phase 1 Implementation
# ============================================================================

@login_required
def my_lists(request):
    """Enhanced My Lists page with improved functionality and auto-created favourites."""
    user = request.user
    
    # Get or create the user's default favourites list
    default_list, created = CouncilList.get_or_create_default_list(user)
    
    # Handle new list creation
    if request.method == 'POST' and 'new_list' in request.POST:
        form = CouncilListForm(request.POST)
        if form.is_valid():
            new_list = form.save(commit=False)
            new_list.user = user
            new_list.save()
            messages.success(request, f'List "{new_list.name}" created successfully!')
            return redirect('my_lists')
    else:
        form = CouncilListForm()
    
    # Get all user's lists (default first due to ordering)
    lists = CouncilList.objects.filter(user=user).prefetch_related('councils')
    
    # Get favourites (councils in default list)
    favourites = default_list.councils.all() if default_list else []
    
    # Get financial years for year selector
    financial_years = FinancialYear.objects.all()
    # Get current year - use first year if no current is marked
    default_year = financial_years.filter(is_current=True).first() or financial_years.first()
    
    # Calculate populations for all councils
    population_data = {}
    try:
        population_field = DataField.objects.get(slug='population')
        
        # Try to import from new data model, fall back to original model
        try:
            if NEW_DATA_MODEL_AVAILABLE:
                from council_finance.models.new_data_model import CouncilCharacteristic as NewCouncilCharacteristic
                CharacteristicModel = NewCouncilCharacteristic
            else:
                CharacteristicModel = CouncilCharacteristic
        except ImportError:
            CharacteristicModel = CouncilCharacteristic
        
        for council_list in lists:
            councils_in_list = council_list.councils.all()
            if councils_in_list:
                # Get population data for councils in this list
                characteristics = CharacteristicModel.objects.filter(
                    council__in=councils_in_list,
                    field=population_field
                ).select_related('council')
                
                list_total = 0
                for char in characteristics:
                    try:
                        value = int(float(char.value)) if char.value else 0
                        population_data[char.council.id] = value
                        list_total += value
                    except (ValueError, TypeError):
                        population_data[char.council.id] = 0
                        
                population_data[f'list_{council_list.id}_total'] = list_total
                
    except (DataField.DoesNotExist, NameError):
        # Fallback if population field doesn't exist or models not available
        pass
    
    # Metric choices for financial data  
    metric_choices = [
        ('total-debt', 'Total Debt'),
        ('current-liabilities', 'Current Liabilities'),
        ('long-term-liabilities', 'Long-term Liabilities'),
        ('interest-paid', 'Interest Paid'),
    ]
    
    # Prepare list metadata for JavaScript
    list_meta = []
    for lst in lists:
        list_meta.append({
            'id': lst.id,
            'name': lst.name,
            'color': lst.color,
            'council_count': lst.get_council_count(),
            'is_default': lst.is_default
        })
    
    log_activity(
        request,
        activity="Viewed My Lists page", 
        extra=f"Lists: {lists.count()}, Favourites: {len(favourites)}"
    )
    
    context = {
        'form': form,
        'lists': lists,
        'favourites': favourites,
        'default_list': default_list,
        'years': financial_years,
        'default_year': default_year,
        'populations': population_data,
        'pop_totals': {lst.id: population_data.get(f'list_{lst.id}_total', 0) for lst in lists},
        'metric_choices': metric_choices,
        'default_metric': 'total_debt',
        'list_meta': list_meta,
        'page_title': 'My Lists',
    }
    
    return render(request, 'council_finance/my_lists_enhanced.html', context)


@login_required
@require_POST
def add_favourite(request):
    """Add a council to the user's favourites list."""
    # Handle both JSON and form data
    if request.content_type == 'application/json':
        import json
        try:
            data = json.loads(request.body)
            council_slug = data.get('council_slug')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    else:
        council_slug = request.POST.get('council')
    
    if not council_slug:
        return JsonResponse({'success': False, 'error': 'Council slug required'})
    
    try:
        council = Council.objects.get(slug=council_slug)
        default_list, created = CouncilList.get_or_create_default_list(request.user)
        
        # Add council to favourites if not already there
        if not default_list.councils.filter(id=council.id).exists():
            default_list.councils.add(council)
            log_activity(
                request,
                activity="Added council to favourites",
                extra=f"Council: {council.name}"
            )
            return JsonResponse({
                'success': True, 
                'message': f'{council.name} added to favourites',
                'council': {
                    'id': council.id,
                    'name': council.name,
                    'slug': council.slug,
                    'population': council.latest_population or 0,
                    'type': council.council_type.name if council.council_type else 'Unknown',
                    'nation': council.nation.name if council.nation else 'Unknown',
                    'logo_url': council.logo.url if hasattr(council, 'logo') and council.logo else None,
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Council already in favourites'})
            
    except Council.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Council not found'})
    except Exception as e:
        logger.error(f"Error adding favourite: {e}")
        return JsonResponse({'success': False, 'error': 'Server error occurred'})


@login_required
@require_POST  
def remove_favourite(request):
    """Remove a council from the user's favourites list."""
    # Handle both JSON and form data
    if request.content_type == 'application/json':
        import json
        try:
            data = json.loads(request.body)
            council_slug = data.get('council_slug')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    else:
        council_slug = request.POST.get('council')
    
    if not council_slug:
        return JsonResponse({'success': False, 'error': 'Council slug required'})
    
    try:
        council = Council.objects.get(slug=council_slug)
        default_list = CouncilList.objects.filter(user=request.user, is_default=True).first()
        
        if default_list and default_list.councils.filter(id=council.id).exists():
            default_list.councils.remove(council)
            log_activity(
                request,
                activity="Removed council from favourites",
                extra=f"Council: {council.name}"
            )
            return JsonResponse({'success': True, 'message': f'{council.name} removed from favourites'})
        else:
            return JsonResponse({'success': False, 'error': 'Council not in favourites'})
            
    except Council.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Council not found'})
    except Exception as e:
        logger.error(f"Error removing favourite: {e}")
        return JsonResponse({'success': False, 'error': 'Server error occurred'})


@login_required
@require_POST
def add_to_list(request, list_id):
    """Add a council to a specific list."""
    council_slug = request.POST.get('council')
    if not council_slug:
        return JsonResponse({'success': False, 'error': 'Council slug required'})
    
    try:
        council = Council.objects.get(slug=council_slug)
        council_list = get_object_or_404(CouncilList, id=list_id, user=request.user)
        
        # Add council to list if not already there
        if not council_list.councils.filter(id=council.id).exists():
            council_list.councils.add(council)
            log_activity(
                request,
                activity="Added council to list",
                extra=f"Council: {council.name}, List: {council_list.name}"
            )
            return JsonResponse({
                'success': True, 
                'message': f'{council.name} added to {council_list.name}',
                'list_id': list_id,
                'council_count': council_list.get_council_count(),
                'council': {
                    'id': council.id,
                    'name': council.name,
                    'slug': council.slug,
                    'population': council.latest_population or 0,
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Council already in this list'})
            
    except Council.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Council not found'})
    except Exception as e:
        logger.error(f"Error adding to list: {e}")
        return JsonResponse({'success': False, 'error': 'Server error occurred'})


@login_required
@require_POST
def remove_from_list(request, list_id):
    """Remove a council from a specific list."""
    council_slug = request.POST.get('council')
    if not council_slug:
        return JsonResponse({'success': False, 'error': 'Council slug required'})
    
    try:
        council = Council.objects.get(slug=council_slug)
        council_list = get_object_or_404(CouncilList, id=list_id, user=request.user)
        
        if council_list.councils.filter(id=council.id).exists():
            council_list.councils.remove(council)
            log_activity(
                request,
                activity="Removed council from list",
                extra=f"Council: {council.name}, List: {council_list.name}"
            )
            return JsonResponse({
                'success': True, 
                'message': f'{council.name} removed from {council_list.name}',
                'list_id': list_id,
                'council_count': council_list.get_council_count()
            })
        else:
            return JsonResponse({'success': False, 'error': 'Council not in this list'})
            
    except Council.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Council not found'})
    except Exception as e:
        logger.error(f"Error removing from list: {e}")
        return JsonResponse({'success': False, 'error': 'Server error occurred'})


@login_required
@require_POST
def move_between_lists(request):
    """Move a council from one list to another (for drag & drop functionality)."""
    council_slug = request.POST.get('council')
    from_list_id = request.POST.get('from')
    to_list_id = request.POST.get('to')
    
    if not all([council_slug, from_list_id, to_list_id]):
        return JsonResponse({'success': False, 'error': 'Missing required parameters'})
    
    try:
        council = Council.objects.get(slug=council_slug)
        from_list = get_object_or_404(CouncilList, id=from_list_id, user=request.user)
        to_list = get_object_or_404(CouncilList, id=to_list_id, user=request.user)
        
        # Remove from source list and add to destination list
        if from_list.councils.filter(id=council.id).exists():
            from_list.councils.remove(council)
            to_list.councils.add(council)
            
            log_activity(
                request,
                activity="Moved council between lists",
                extra=f"Council: {council.name}, From: {from_list.name}, To: {to_list.name}"
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{council.name} moved from {from_list.name} to {to_list.name}',
                'from_list_count': from_list.get_council_count(),
                'to_list_count': to_list.get_council_count(),
                'council': {
                    'id': council.id,
                    'name': council.name,
                    'slug': council.slug,
                    'population': council.latest_population or 0,
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Council not in source list'})
            
    except Council.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Council not found'})
    except Exception as e:
        logger.error(f"Error moving between lists: {e}")
        return JsonResponse({'success': False, 'error': 'Server error occurred'})


@login_required
@require_GET
def list_metric(request, list_id):
    """Get financial metric data for all councils in a list."""
    field_slug = request.GET.get('field', 'total_debt')
    year_id = request.GET.get('year')
    
    try:
        logger.info(f"list_metric: user={request.user.username}, list_id={list_id}, field={field_slug}, year_id={year_id}")
        council_list = get_object_or_404(CouncilList, id=list_id, user=request.user)
        councils = council_list.councils.all()
        logger.info(f"list_metric: found list '{council_list.name}' with {councils.count()} councils")
        
        if not councils:
            return JsonResponse({'values': {}, 'total': 0})
        
        # Get the requested field and year
        field = get_object_or_404(DataField, slug=field_slug)
        year = get_object_or_404(FinancialYear, id=year_id) if year_id else FinancialYear.objects.filter(is_current=True).first()
        
        if not year:
            return JsonResponse({'error': 'No financial year available'}, status=404)
        
        # Get financial figures for all councils in the list
        # Try to use new data model if available, otherwise use original
        try:
            if NEW_DATA_MODEL_AVAILABLE:
                from council_finance.models.new_data_model import FinancialFigure as NewFinancialFigure
                FigureModel = NewFinancialFigure 
            else:
                FigureModel = FinancialFigure
        except (ImportError, NameError):
            FigureModel = FinancialFigure
        
        figures = FigureModel.objects.filter(
            council__in=councils,
            field=field,
            year=year
        ).select_related('council')
        
        # Build response data
        values = {}
        total = 0
        
        for figure in figures:
            try:
                value = float(figure.value) if figure.value else 0
                values[figure.council.id] = value
                total += value
            except (ValueError, TypeError):
                values[figure.council.id] = 0
        
        return JsonResponse({
            'values': values,
            'total': total,
            'field_name': field.name,
            'year_label': year.label
        })
        
    except (DataField.DoesNotExist, FinancialYear.DoesNotExist) as e:
        logger.error(f"Field or year not found in list_metric: {e}")
        return JsonResponse({'error': f'Field or year not found: {str(e)}'}, status=404)
    except Exception as e:
        import traceback
        logger.error(f"Error getting list metric: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
@csrf_exempt
@require_POST
def create_list_api(request):
    """API endpoint to create a new custom list."""
    try:
        import json
        data = json.loads(request.body)
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'List name is required'}, status=400)
        
        # Check if user already has a list with this name
        if CouncilList.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'success': False, 'error': 'You already have a list with this name'}, status=400)
        
        # Create the new list
        new_list = CouncilList.objects.create(
            user=request.user,
            name=name,
            description=data.get('description', '').strip(),
            color=data.get('color', 'blue'),
            is_default=False
        )
        
        log_activity(
            request,
            activity="Created custom list",
            extra=f"List: {new_list.name}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'List "{new_list.name}" created successfully!',
            'list': {
                'id': new_list.id,
                'name': new_list.name,
                'description': new_list.description,
                'color': new_list.color,
                'council_count': 0
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating list: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to create list'}, status=500)


# ============================================================================
# FOLLOWING & COMPARISON FUNCTIONALITY - Placeholder implementations
# ============================================================================

@login_required



@login_required
@require_POST
def follow_item_api(request):
    """API endpoint to follow items - placeholder."""
    return JsonResponse({'success': True, 'message': 'Follow functionality coming soon'})


@login_required  
@require_POST
def unfollow_item_api(request):
    """API endpoint to unfollow items - placeholder."""
    return JsonResponse({'success': True, 'message': 'Unfollow functionality coming soon'})





# ============================================================================
# COMPARISON FUNCTIONALITY - Basic implementations
# ============================================================================

@login_required
@require_POST
def add_to_compare(request, slug):
    """Add a council to comparison basket."""
    try:
        council = get_object_or_404(Council, slug=slug)  
        # Get or create comparison list in session
        compare_list = request.session.get('compare_councils', [])
        
        if slug not in compare_list:
            compare_list.append(slug)
            request.session['compare_councils'] = compare_list
            
        return JsonResponse({
            'status': 'success',
            'message': f'{council.name} added to comparison',
            'count': len(compare_list)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
def remove_from_compare(request, slug):
    """Remove a council from comparison basket."""
    try:
        council = get_object_or_404(Council, slug=slug)
        compare_list = request.session.get('compare_councils', [])
        
        if slug in compare_list:
            compare_list.remove(slug)
            request.session['compare_councils'] = compare_list
            
        return JsonResponse({
            'status': 'success', 
            'message': f'{council.name} removed from comparison',
            'count': len(compare_list)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def compare_basket(request):
    """Show comparison basket page."""
    compare_slugs = request.session.get('compare_councils', [])
    councils = Council.objects.filter(slug__in=compare_slugs)
    
    context = {
        'councils': councils,
        'page_title': 'Compare Councils'
    }
    return render(request, 'council_finance/compare_basket.html', context)


@login_required
@require_POST
def clear_compare_basket(request):
    """Clear all councils from comparison basket."""
    request.session['compare_councils'] = []
    return JsonResponse({'status': 'success', 'message': 'Comparison basket cleared'})


@login_required
def compare_row(request):
    """Compare row functionality - placeholder."""
    return JsonResponse({'status': 'success', 'data': []})


@login_required
def detailed_comparison(request):
    """Detailed comparison page - placeholder."""
    context = {'page_title': 'Detailed Comparison'}
    return render(request, 'council_finance/detailed_comparison.html', context)


# ============================================================================
# FEED & UPDATE FUNCTIONALITY - Placeholder implementations  
# ============================================================================

@login_required
@require_POST
def like_update(request, update_id):
    """Like an update - placeholder."""
    return JsonResponse({'status': 'success', 'message': 'Like functionality coming soon'})


@comments_access_required
@require_POST
def comment_update(request, update_id):
    """Comment on an update - placeholder."""  
    return JsonResponse({'status': 'success', 'message': 'Comment functionality coming soon'})


@login_required
@require_POST
def interact_with_update_api(request, update_id):
    """API to interact with updates - placeholder."""
    return JsonResponse({'success': True, 'message': 'Interaction API coming soon'})


@login_required
@require_POST
def comment_on_update_api(request, update_id):
    """API to comment on updates - placeholder."""
    return JsonResponse({'success': True, 'message': 'Comment API coming soon'})


@login_required
@require_POST
def update_feed_preferences_api(request):
    """API to update feed preferences - placeholder."""
    return JsonResponse({'success': True, 'message': 'Feed preferences API coming soon'})


@login_required
@require_GET
def get_feed_updates_api(request):
    """API to get feed updates - placeholder."""
    return JsonResponse({'updates': [], 'message': 'Feed updates API coming soon'})


# ActivityLog Comment API Endpoints

@comments_access_required
@require_POST
def comment_on_activity_log(request, activity_log_id):
    """
    API endpoint to add a comment to an ActivityLog entry in the Following feed.
    
    Supports both top-level comments and replies to existing comments.
    """
    try:
        # Get the activity log entry
        activity_log = get_object_or_404(ActivityLog, id=activity_log_id)
        
        # Allow any authenticated user to comment (removed follow restriction)
        # This enables commenting on the public feed and sample feeds
        
        # Get comment data
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Comment content is required'
            }, status=400)
        
        # Validate parent comment if provided
        parent = None
        if parent_id:
            try:
                parent = ActivityLogComment.objects.get(
                    id=parent_id,
                    activity_log=activity_log,
                    is_approved=True
                )
            except ActivityLogComment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid parent comment'
                }, status=400)
        
        # Create the comment
        comment = ActivityLogComment.objects.create(
            activity_log=activity_log,
            user=request.user,
            content=content,
            parent=parent,
            is_approved=True  # Auto-approve for now, can add moderation later
        )
        
        # Log the activity
        from council_finance.activity_logging import log_activity
        log_activity(
            request,
            activity='comment_on_activity_log',
            action=f'Commented on activity log entry',
            extra={
                'activity_log_id': activity_log.id,
                'comment_id': comment.id,
                'is_reply': parent is not None,
                'council_slug': activity_log.related_council.slug if activity_log.related_council else None
            }
        )
        
        # Return success response with comment data
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': {
                    'username': comment.user.username,
                    'display_name': getattr(comment.user, 'get_full_name', lambda: comment.user.username)()
                },
                'created_at': comment.created_at.isoformat(),
                'is_reply': comment.is_reply(),
                'parent_id': comment.parent.id if comment.parent else None,
                'like_count': comment.like_count,
                'reply_count': comment.get_reply_count()
            }
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in comment_on_activity_log: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while posting your comment'
        }, status=500)


@comments_access_required
@require_GET
def get_activity_log_comments(request, activity_log_id):
    """
    API endpoint to get comments for an ActivityLog entry.
    
    Returns paginated comments with threading support.
    """
    try:
        # Get the activity log entry
        activity_log = get_object_or_404(ActivityLog, id=activity_log_id)
        
        # Get approved top-level comments with replies
        comments = ActivityLogComment.objects.filter(
            activity_log=activity_log,
            is_approved=True,
            parent=None  # Only top-level comments
        ).select_related('user').prefetch_related(
            'replies__user'
        ).order_by('created_at')
        
        # Paginate if needed
        page = request.GET.get('page', 1)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        
        paginator = Paginator(comments, 20)  # 20 comments per page
        page_obj = paginator.get_page(page)
        
        # Format comments for JSON response
        comments_data = []
        for comment in page_obj:
            comment_data = {
                'id': comment.id,
                'content': comment.content,
                'user': {
                    'username': comment.user.username,
                    'display_name': getattr(comment.user, 'get_full_name', lambda: comment.user.username)()
                },
                'created_at': comment.created_at.isoformat(),
                'like_count': comment.like_count,
                'reply_count': comment.get_reply_count(),
                'replies': []
            }
            
            # Add replies
            for reply in comment.replies.filter(is_approved=True).order_by('created_at'):
                reply_data = {
                    'id': reply.id,
                    'content': reply.content,
                    'user': {
                        'username': reply.user.username,
                        'display_name': getattr(reply.user, 'get_full_name', lambda: reply.user.username)()
                    },
                    'created_at': reply.created_at.isoformat(),
                    'like_count': reply.like_count,
                    'parent_id': reply.parent.id
                }
                comment_data['replies'].append(reply_data)
            
            comments_data.append(comment_data)
        
        return JsonResponse({
            'success': True,
            'comments': comments_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_comments': page_obj.paginator.count
            }
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in get_activity_log_comments: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while fetching comments'
        }, status=500)


@comments_access_required 
@require_POST
def like_activity_log_comment(request, comment_id):
    """
    API endpoint to like/unlike an ActivityLog comment.
    
    Toggles the like status and updates the like count.
    """
    try:
        comment = get_object_or_404(ActivityLogComment, id=comment_id, is_approved=True)
        
        # For simplicity, we'll just increment/decrement the like count
        # In a full implementation, you'd want a separate Like model to track individual likes
        action = request.POST.get('action', 'like')
        
        if action == 'like':
            comment.like_count += 1
            liked = True
        else:
            comment.like_count = max(0, comment.like_count - 1)
            liked = False
        
        comment.save(update_fields=['like_count'])
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': comment.like_count
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in like_activity_log_comment: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while updating the like'
        }, status=500)


def about(request):
    """
    About page showcasing the Council Finance Counters platform.
    
    Explains what the system does, how it works, and encourages community
    involvement through GitHub contributions and issue reporting.
    """
    # Get GitHub statistics
    github_service = GitHubStatsService()
    
    context = {
        'page_title': 'About Council Finance Counters',
        'github_stats': github_service.get_repository_stats(),
        'recent_issues': github_service.get_recent_issues(limit=3),
        'contributors': github_service.get_contributors(limit=8),
        'github_repo_url': 'https://github.com/mikerouse/cfc',
        'github_issues_url': 'https://github.com/mikerouse/cfc/issues',
        
        # Platform statistics
        'total_councils': Council.objects.count(),
        'total_data_fields': DataField.objects.count(),
        'total_contributions': ActivityLog.objects.filter(activity_type='update').count(),
        'latest_year': FinancialYear.objects.order_by('-start_date').first(),
        
        
        # Technology stack
        'tech_stack': [
            {'name': 'Django', 'description': 'Python web framework for rapid development'},
            {'name': 'PostgreSQL', 'description': 'Robust database for financial data integrity'},
            {'name': 'Tailwind CSS', 'description': 'Modern utility-first CSS framework'},
            {'name': 'OpenAI API', 'description': 'AI-powered insights and factoid generation'},
            {'name': 'JavaScript', 'description': 'Interactive frontend and real-time updates'},
            {'name': 'Redis', 'description': 'Caching and session management'}
        ]
    }
    
    return render(request, 'council_finance/about.html', context)


def github_stats_api(request):
    """
    API endpoint for GitHub repository statistics.
    Returns JSON data for AJAX calls from the About page.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX requests only'}, status=400)
    
    try:
        github_service = GitHubStatsService()
        stats = github_service.get_repository_stats()
        
        # Add contributors count to stats
        contributors = github_service.get_contributors(limit=100)
        stats['contributors_count'] = len(contributors)
        
        return JsonResponse(stats)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in github_stats_api: {str(e)}')
        
        return JsonResponse({
            'stars': 0,
            'forks': 0,
            'open_issues': 0,
            'contributors_count': 0
        }, status=500)


def github_contributors_api(request):
    """
    API endpoint for GitHub repository contributors.
    Returns JSON data for AJAX calls from the About page.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX requests only'}, status=400)
    
    try:
        github_service = GitHubStatsService()
        contributors = github_service.get_contributors(limit=12)
        
        return JsonResponse({
            'contributors': contributors
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in github_contributors_api: {str(e)}')
        
        return JsonResponse({
            'contributors': []
        }, status=500)

