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

# Import the constant containing valid field names for counter formulas.
from council_finance.forms import (
    SignUpForm,
    CouncilListForm,
    CounterDefinitionForm,
    SiteCounterForm,
    GroupCounterForm,
    DataFieldForm,
    ProfileExtraForm,
    FactoidForm,
    UpdateCommentForm,
)
from django.conf import settings

# Minimum trust tier level required to access management views.
MANAGEMENT_TIER = 4

# Logger used throughout this module for operational messages.
logger = logging.getLogger(__name__)

from council_finance.models import DataField
from council_finance.factoids import get_factoids, get_factoids_for_template_system, previous_year_label
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
    Factoid,
    TrustTier,
    Contribution,
    DataChangeLog,
    BlockedIP,
    # RejectionLog is used in the God Mode admin view for moderating
    # contribution rejections and IP blocks.
    RejectionLog,
    ActivityLog,
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
    
    if latest_year:
        field = DataField.objects.filter(slug="total_debt").first()
        total_debt = (
            FinancialFigure.objects.filter(field=field, year=latest_year).aggregate(
                total=Sum("value")
            )["total"]
            or 0
        )
    else:
        # Fallback when no figures are loaded
        total_debt = 0

    # Get total council count for hero section
    total_councils = Council.objects.count()
    
    # Calculate enhanced hero stats
    total_debt_billions = total_debt / 1_000_000_000 if total_debt else 0
    
    # Calculate completion percentage
    all_years = FinancialYear.objects.all()
    expected_data_points = total_councils * DataField.objects.count() * all_years.count()
    actual_data_points = CouncilCharacteristic.objects.count() + FinancialFigure.objects.count()
    completion_percentage = (actual_data_points / expected_data_points * 100) if expected_data_points > 0 else 0
    
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
            council_index = int(today_seed[:8], 16) % council_count
            council_of_the_day = Council.objects.all()[council_index]
            
            # Get a few more featured councils (exclude council of the day)
            featured_councils_raw = list(Council.objects.exclude(id=council_of_the_day.id).order_by('?')[:5])
            featured_councils_raw.insert(0, council_of_the_day)  # Put council of the day first
            
            # Enhance featured councils with financial data carousel
            featured_councils = []
            from council_finance.agents.counter_agent import CounterAgent
            agent = CounterAgent()
            
            for council in featured_councils_raw:
                council_data = {'council': council, 'financial_years': []}
                
                # Get current liabilities data for available years
                for year in all_years[:3]:  # Show up to 3 most recent years
                    result = agent.run(council_slug=council.slug, year_label=year.label)
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
    except:
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

    # When any counter total is missing, compute them all so visitors always see
    # up to date figures even if the background task failed to run.
    if missing_cache:
        # Run the agent synchronously so the cache is filled before rendering
        # the page. This means the first visitor after a deployment may trigger
        # a slight delay, but subsequent requests will hit the cache.
        SiteTotalsAgent().run()

    def get_site_counter_factoids(site_counter):
        """Generate custom factoids for site counters with council-specific data."""
        factoids = []
        
        # Get council data for this counter
        from council_finance.agents.counter_agent import CounterAgent
        agent = CounterAgent()
        councils_with_data = []
        
        year_label = site_counter.year.label if site_counter.year else "2024/25"
        
        for council in Council.objects.all():
            result = agent.run(council_slug=council.slug, year_label=year_label)
            counter_data = result.get(site_counter.counter.slug)
            if counter_data and counter_data.get('value') and counter_data.get('value') > 0:
                councils_with_data.append({
                    'council': council,
                    'value': counter_data['value'],
                    'formatted': counter_data['formatted']
                })
        
        # Sort by value
        councils_with_data.sort(key=lambda x: x['value'])
        
        # Factoid 1: Number of councils with caution if incomplete
        total_councils = Council.objects.count()
        if total_councils < 200:
            factoids.append(f"⚠️ Incomplete data: Based on {len(councils_with_data)} of {total_councils} councils. <a href='/contribute/' class='text-blue-600 hover:text-blue-800'>Help us get more accurate figures</a>")
        else:
            factoids.append(f"Based on data from {len(councils_with_data)} councils")
        
        # Factoid 2: Highest council (if we have data)
        if councils_with_data:
            highest = councils_with_data[-1]
            friendly_format = site_counter.counter.format_value(highest['value'])
            factoids.append(f"Highest: {highest['council'].name} ({friendly_format})")
        
        # Factoid 3: Lowest council (if we have multiple councils)
        if len(councils_with_data) > 1:
            lowest = councils_with_data[0]
            friendly_format = site_counter.counter.format_value(lowest['value'])
            factoids.append(f"Lowest: {lowest['council'].name} ({friendly_format})")
        elif len(councils_with_data) == 1:
            # If only one council, show it as the only contributor
            only = councils_with_data[0]
            friendly_format = site_counter.counter.format_value(only['value'])
            factoids.append(f"Only data available: {only['council'].name} ({friendly_format})")
        
        return factoids

    # Now build the list of promoted counters using the cached totals. This may
    # happen after the agent has populated the cache above.
    for sc in SiteCounter.objects.filter(promote_homepage=True):
        year_label = sc.year.label if sc.year else "all"
        value = cache.get(f"counter_total:{sc.slug}:{year_label}", 0)
        prev_value = 0
        if sc.year:
            prev_value = cache.get(f"counter_total:{sc.slug}:{year_label}:prev", 0)
        formatted = CounterDefinition.format_value(sc, value)
        promoted.append({
            "slug": sc.slug,
            "counter_slug": sc.counter.slug,  # Add counter definition slug for factoids
            "year": sc.year.label if sc.year else None,  # Add year for factoids
            "name": sc.name,
            "formatted": formatted,
            "raw": value,
            "duration": sc.duration,
            "precision": sc.precision,
            "show_currency": sc.show_currency,
            "friendly_format": sc.friendly_format,
            "explanation": sc.explanation,
            "columns": sc.columns,
            "factoids": get_site_counter_factoids(sc),
        })

    # Group counters follow the same pattern but target a subset of councils.
    for gc in GroupCounter.objects.filter(promote_homepage=True):
        year_label = gc.year.label if gc.year else "all"
        value = cache.get(f"counter_total:{gc.slug}:{year_label}", 0)
        prev_value = 0
        if gc.year:
            prev_value = cache.get(f"counter_total:{gc.slug}:{year_label}:prev", 0)
        formatted = CounterDefinition.format_value(gc, value)
        promoted.append({
            "slug": gc.slug,
            "name": gc.name,
            "formatted": formatted,
            "raw": value,
            "duration": gc.duration,
            "precision": gc.precision,
            "show_currency": sc.show_currency,
            "friendly_format": gc.friendly_format,
            "explanation": "",  # groups currently lack custom explanations
            "columns": 3,  # groups default to full width for now
            "factoids": get_factoids(
                gc.counter.slug,
                {"value": formatted, "raw": value, "previous_raw": prev_value},
            ),
        })

    context = {
        "total_debt": total_debt,
        "total_debt_billions": total_debt_billions,
        "total_councils": total_councils,
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

        agent = CounterAgent()
        # Compute all counter values for this council/year using the agent
        values = agent.run(council_slug=slug, year_label=selected_year.label)
        prev_values = {}
        prev_label = previous_year_label(selected_year.label)
        if prev_label:
            prev_year = FinancialYear.objects.filter(label=prev_label).first()
            if prev_year:
                prev_values = agent.run(council_slug=slug, year_label=prev_year.label)

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
                "factoids": get_factoids_for_template_system(
                    counter.slug,
                    council=council,
                    year=selected_year,
                    base_context={
                        "value": result.get("formatted"),
                        "raw": result.get("value"),
                        "previous_raw": prev.get("value"),
                    },
                ),
            }
            if counter.headline:
                head_list.append(item)
            else:
                other_list.append(item)
            if counter.show_by_default:
                default_slugs.append(counter.slug)
        counters = head_list + other_list

    # Pull a few non-financial stats to display in a meta zone. These use
    # existing DataField values so we don't need a separate model.
    meta_fields = ["population", "elected_members", "waste_report_count"]
    meta_values = []
    for slug in meta_fields:
        field = DataField.objects.filter(slug=slug).first()
        if not field:
            continue
        if slug == "population":
            # Check for population in CouncilCharacteristic first
            characteristic = CouncilCharacteristic.objects.filter(council=council, field=field).first()
            if characteristic:
                display = field.display_value(characteristic.value)
            elif council.latest_population is not None:
                display = field.display_value(str(council.latest_population))
            else:
                display = "No data"
            meta_values.append({"field": field, "value": display})
            continue        # First check if it's a council characteristic
        characteristic = CouncilCharacteristic.objects.filter(council=council, field=field).first()
        if characteristic:
            display = field.display_value(characteristic.value)
        else:
            # Then check financial figures (get the most recent)
            financial_figure = (
                FinancialFigure.objects.filter(council=council, field=field)
                .order_by("-year__label")
                .first()
            )
            if financial_figure:
                display = field.display_value(str(financial_figure.value))
            else:
                display = "No data"
        meta_values.append({"field": field, "value": display})

    is_following = False
    if request.user.is_authenticated:
        from council_finance.models import CouncilFollow

        is_following = CouncilFollow.objects.filter(
            user=request.user, council=council
        ).exists()
    
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

    context = {
        "council": council,
        "figures": figures,
        "counters": counters,
        "years": years,
        "selected_year": selected_year,
        "default_counter_slugs": default_slugs,
        "tab": tab,
        "focus": focus,
        "meta_values": meta_values,
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
        "share_data": share_data,
        # Administrative messaging
        "administrative_messages": administrative_messages,
        "recent_merge_activity": recent_merge_activity,
        "recent_flag_activity": recent_flag_activity,
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
    """Display the top contributors ordered by points."""

    # Fetch the highest scoring profiles and include the related user object
    # so the template can reference usernames without additional queries.
    top_profiles = (
        UserProfile.objects.select_related("user")
        .order_by("-points")[:20]
    )

    context = {"top_profiles": top_profiles}
    return render(request, "council_finance/leaderboards.html", context)


def my_lists(request):
    """Allow users to manage their favourite councils and custom lists."""
    if not request.user.is_authenticated:
        return redirect("login")

    profile = request.user.profile
    # Prefetch councils so template access doesn't hit the DB repeatedly
    lists = request.user.council_lists.prefetch_related("councils")
    favourites = profile.favourites.all()
    form = CouncilListForm()

    # Cached population figures avoid expensive per-request lookups.
    councils = Council.objects.all()
    # Map of council_id -> numeric value for sorting and totals
    pop_values = {c.id: float(c.latest_population or 0) for c in councils}
    # Map of council_id -> display string used in templates
    pop_display = {
        c.id: int(c.latest_population)
        if c.latest_population is not None
        else "Needs populating"
        for c in councils
    }

    # Pre-calculate population totals for each list so the template can
    # display a summary row without additional queries.
    pop_totals = {}
    for lst in lists:
        total = 0
        for c in lst.councils.all():
            try:
                total += float(pop_values.get(c.id, 0))
            except (TypeError, ValueError):
                continue
        pop_totals[lst.id] = total

    # Choices for the dynamic metric column. We exclude population because it
    # already has a dedicated column.
    metric_choices = [
        (f.slug, f.slug.replace("_", " ").title())
        for f in DataField.objects.exclude(slug="population")
    ]
    default_metric = "total_debt"

    # Allow the metric column to show figures from different years.
    # Present the years newest first so the latest data is selected by default.
    years = FinancialYear.objects.order_by("-label")
    default_year = years.first() if years else None

    if request.method == "POST":
        if "new_list" in request.POST:
            form = CouncilListForm(request.POST)
            if form.is_valid():
                new_list = form.save(commit=False)
                new_list.user = request.user
                new_list.save()
                messages.success(request, "List created")
                return redirect("my_lists")
        elif "remove_fav" in request.POST:
            slug = request.POST.get("council")
            try:
                council = Council.objects.get(slug=slug)
                profile.favourites.remove(council)
                messages.info(request, "Favourite removed")
            except Council.DoesNotExist:
                messages.error(request, "Council not found")
            return redirect("my_lists")
        elif "add_to_list" in request.POST:
            slug = request.POST.get("council")
            list_id = request.POST.get("list")
            try:
                council = Council.objects.get(slug=slug)
                target = request.user.council_lists.get(id=list_id)
                target.councils.add(council)
                messages.success(request, "Added to list")
            except (Council.DoesNotExist, CouncilList.DoesNotExist):
                messages.error(request, "Invalid request")
            return redirect("my_lists")

    # Provide population figures and list metadata to the template
    list_meta = list(lists.values("id", "name"))
    context = {
        "favourites": favourites,
        "lists": lists,
        "form": form,
        # Display values shown in the table
        "populations": pop_display,
        # Numeric values for sorting and totals
        "pop_values": pop_values,
        "list_meta": list_meta,
        "pop_totals": pop_totals,
        "metric_choices": metric_choices,
        "default_metric": default_metric,
        "years": years,
        "default_year": default_year,
    }
    return render(request, "council_finance/my_lists.html", context)


def following(request):
    """
    Enhanced Following page with comprehensive social features.
    
    Shows personalized feed based on user's follows including councils, lists, 
    contributors, and financial figures. Supports filtering, prioritization,
    and real-time interactions.
    """
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect("login")
    
    from council_finance.models import (
        FollowableItem, FeedUpdate, UserFeedPreferences, TrendingContent,
        Council, CouncilList, 
    )
    from council_finance.services.following_services import FeedService, FollowService, TrendingService
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Count, Q
    import json
    
    # Get or create user feed preferences
    preferences, created = UserFeedPreferences.objects.get_or_create(
        user=request.user,
        defaults={
            'algorithm': 'mixed',
            'show_financial_updates': True,
            'show_contributions': True,
            'show_council_news': True,
            'show_list_changes': True,
            'show_system_updates': False,
            'show_achievements': True,
        }
    )
    
    # Get algorithm preference from request or user preferences
    algorithm = request.GET.get('algorithm', preferences.algorithm)
    feed_filter = request.GET.get('filter', 'all')
    
    # Build content type filters based on preferences
    content_filters = Q()
    if not preferences.show_financial_updates:
        content_filters &= ~Q(update_type='financial')
    if not preferences.show_contributions:
        content_filters &= ~Q(update_type='contribution')
    if not preferences.show_council_news:
        content_filters &= ~Q(update_type='council_news')
    if not preferences.show_list_changes:
        content_filters &= ~Q(update_type='list_change')
    if not preferences.show_system_updates:
        content_filters &= ~Q(update_type='system')
    if not preferences.show_achievements:
        content_filters &= ~Q(update_type='achievement')

    # Get personalized feed with filters applied
    feed_updates = FeedService.get_personalized_feed(
        user=request.user,
        limit=50,
        algorithm=algorithm,
        content_filters=content_filters,
        feed_filter=feed_filter
    )
    
    # Get user's follows categorized
    user_follows = FollowService.get_user_follows(request.user)
    follows_by_type = {}
    for follow in user_follows:
        content_type = follow.content_type.model
        if content_type not in follows_by_type:
            follows_by_type[content_type] = []
        follows_by_type[content_type].append({
            'id': follow.id,
            'object': follow.content_object,
            'priority': follow.priority,
            'created_at': follow.created_at,
            'interaction_count': follow.interaction_count
        })
    
    # Get trending content for recommendations (with fallbacks)
    try:
        trending_councils = TrendingService.get_trending_content('council', limit=5)
    except Exception as e:
        trending_councils = []
        logger.warning(f"Could not get trending councils: {e}")
    
    try:
        trending_lists = TrendingService.get_trending_content('councillist', limit=3)
    except Exception as e:
        trending_lists = []
        logger.warning(f"Could not get trending lists: {e}")
    
    # Get follower statistics
    total_follows = user_follows.count()
    follows_by_priority = user_follows.values('priority').annotate(count=Count('id'))
    priority_stats = {stat['priority']: stat['count'] for stat in follows_by_priority}
    
    # Get recent activity stats
    from datetime import timedelta
    from django.utils import timezone
    import logging
    
    logger = logging.getLogger(__name__)
    
    recent_cutoff = timezone.now() - timedelta(days=7)
    try:
        recent_updates_count = FeedService.get_recent_updates_count(
            user=request.user,
            days=7,
            content_filters=content_filters,
            feed_filter=feed_filter
        )
    except Exception as e:
        recent_updates_count = 0
        logger.warning(f"Could not get recent updates count: {e}")
    
    # Get suggested follows (councils with high activity that user doesn't follow)
    try:
        followed_council_ids = FollowableItem.objects.filter(
            user=request.user,
            content_type=ContentType.objects.get_for_model(Council)
        ).values_list('object_id', flat=True)
        
        # Get councils with recent updates by querying FeedUpdate directly
        council_content_type = ContentType.objects.get_for_model(Council)
        councils_with_recent_updates = FeedUpdate.objects.filter(
            content_type=council_content_type,
            created_at__gte=recent_cutoff,
            is_public=True
        ).values_list('object_id', flat=True).distinct()
        
        # Get follower counts for councils using the new FollowableItem system
        councils_with_followers = FollowableItem.objects.filter(
            content_type=council_content_type
        ).values('object_id').annotate(
            follower_count=Count('id')
        ).filter(follower_count__gt=2)  # Lower threshold for testing
        
        high_follower_council_ids = [item['object_id'] for item in councils_with_followers]
        
        # Combine councils with high followers or recent updates
        suggested_council_ids = set(councils_with_recent_updates) | set(high_follower_council_ids)
        
        # Exclude already followed councils
        suggested_council_ids -= set(followed_council_ids)
        
        # Get the actual council objects with follower count from the old system for display
        # (since we might not have enough data in the new system yet)
        if suggested_council_ids:
            suggested_councils = Council.objects.filter(
                id__in=list(suggested_council_ids)
            ).annotate(
                # Use the existing followed_by relationship from the old CouncilFollow system
                follower_count=Count('followed_by')
            ).order_by('-follower_count')[:5]
        else:
            # Fallback: suggest some active councils if no specific suggestions
            suggested_councils = Council.objects.filter(
                status='active'
            ).annotate(
                follower_count=Count('followed_by')
            ).order_by('-follower_count')[:5]
            
    except Exception as e:
        logger.warning(f"Could not get suggested councils: {e}")
        suggested_councils = []
    
    # Prepare context
    context = {
        'feed_updates': feed_updates,
        'preferences': preferences,
        'follows_by_type': follows_by_type,
        'trending_councils': trending_councils,
        'trending_lists': trending_lists,
        'suggested_councils': suggested_councils,
        'total_follows': total_follows,
        'priority_stats': priority_stats,
        'recent_updates_count': recent_updates_count,
        'current_algorithm': algorithm,
        'current_filter': feed_filter,
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
        # For JavaScript
        'preferences_json': json.dumps({
            'algorithm': preferences.algorithm,
            'show_financial_updates': preferences.show_financial_updates,
            'show_contributions': preferences.show_contributions,
            'show_council_news': preferences.show_council_news,
            'show_list_changes': preferences.show_list_changes,
            'show_system_updates': preferences.show_system_updates,
            'show_achievements': preferences.show_achievements,
        }),
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
        councils = councils.extra(
            select={
                'name_exact': f"CASE WHEN LOWER(name) = LOWER('{query}') THEN 1 ELSE 0 END",
                'name_starts': f"CASE WHEN LOWER(name) LIKE LOWER('{query}%') THEN 1 ELSE 0 END"
            }
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
def add_favourite(request):
    """Add a council to user's favourites."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council_slug = request.POST.get('council')
        if not council_slug:
            return JsonResponse({"error": "Council slug required"}, status=400)
        
        council = Council.objects.get(slug=council_slug)
        profile = request.user.profile
        profile.favourites.add(council)
        
        return JsonResponse({"status": "success", "message": "Added to favourites"})
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except Exception as e:
        logger.error(f"Error adding favourite: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def remove_favourite(request):
    """Remove a council from user's favourites."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council_slug = request.POST.get('council')
        if not council_slug:
            return JsonResponse({"error": "Council slug required"}, status=400)
        
        council = Council.objects.get(slug=council_slug)
        profile = request.user.profile
        profile.favourites.remove(council)
        
        return JsonResponse({"status": "success", "message": "Removed from favourites"})
    
    except Council.DoesNotExist:
        return JsonResponse({"error": "Council not found"}, status=404)
    except Exception as e:
        logger.error(f"Error removing favourite: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


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


def list_metric(request, list_id):
    """Get metric data for a specific list."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        council_list = request.user.council_lists.get(id=list_id)
        metric = request.GET.get('metric', 'total_debt')
        year_id = request.GET.get('year')
          # Get councils in the list with their metric values
        councils = council_list.councils.all()
        results = {}
        total = 0
        
        for council in councils:
            try:
                if year_id:
                    year = FinancialYear.objects.get(id=year_id)
                    financial_figure = FinancialFigure.objects.filter(
                        council=council, 
                        year=year,
                        field__slug=metric
                    ).first()
                    value = financial_figure.value if financial_figure else 0
                else:
                    # Use latest available data
                    financial_figure = FinancialFigure.objects.filter(
                        council=council,
                        field__slug=metric
                    ).order_by('-year__label').first()
                    value = financial_figure.value if financial_figure else 0
                
                results[council.id] = {
                    'value': float(value) if value else 0,
                    'formatted': f"£{value:,.0f}" if value else "N/A"
                }
                total += float(value) if value else 0
            except (TypeError, ValueError):
                results[council.id] = {'value': 0, 'formatted': "N/A"}
        
        return JsonResponse({
            "status": "success",
            "results": results,
            "total": total,
            "total_formatted": f"£{total:,.0f}"
        })
    
    except CouncilList.DoesNotExist:
        return JsonResponse({"error": "List not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting list metric: {e}")
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


