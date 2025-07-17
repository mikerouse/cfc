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
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import ValidationError

import ast
import csv
import hashlib
import inspect
import json
import operator

# Brevo's Python SDK exposes ApiException from the `rest` module
from brevo_python.rest import ApiException

from .emails import send_confirmation_email, send_email
from .notifications import create_notification

# Import the constant containing valid field names for counter formulas.
from .forms import (
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

from .models import DataField
from .factoids import get_factoids, previous_year_label
from .models import (
    Council,
    FinancialYear,
    FigureSubmission,
    UserProfile,
    UserFollow,
    PendingProfileChange,
    CouncilList,
    CounterDefinition,
    CouncilCounter,
    SiteCounter,
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
)

# Import new data models
try:
    from .models.new_data_model import (
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
def list_field_options(request, slug):
    """Return selectable options for a list type field."""
    # The contribution modal needs to populate a drop-down when a
    # characteristic is backed by another dataset (e.g. council type).
    # This small API provides the ID/name pairs used to build that menu.
    from .models import DataField

    try:
        field = DataField.objects.get(slug=slug)
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
    """Landing page with search and overall debt counter."""
    # Pull any search query from the request
    query = request.GET.get("q", "")

    # Look up councils matching the query when present
    councils = []
    if query:
        councils = Council.objects.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        )

    # Determine the latest financial year for which we have debt figures
    latest_year = FinancialYear.objects.order_by("-label").first()

    if latest_year:
        field = DataField.objects.filter(slug="total_debt").first()
        total_debt = (
            FigureSubmission.objects.filter(field=field, year=latest_year).aggregate(
                total=Sum(Cast("value", DecimalField(max_digits=20, decimal_places=2)))
            )["total"]
            or 0
        )
    else:
        # Fallback when no figures are loaded
        total_debt = 0

    promoted = []
    # Import here to keep the view lightweight if the home page is cached.
    from .models import SiteCounter, GroupCounter
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
        elif val == 0 and FigureSubmission.objects.exists():
            # A zero total with actual figures likely means the cache was
            # populated before data was loaded. Trigger a refresh so visitors
            # see correct values without manual intervention.
            missing_cache = True
        if sc.year and cache.get(f"{key}:prev") is None:
            missing_cache = True

    for gc in GroupCounter.objects.filter(promote_homepage=True):
        year_label = gc.year.label if gc.year else "all"
        key = f"counter_total:{gc.slug}:{year_label}"
        val = cache.get(key)
        # Group counters may be restricted to subsets of councils. We apply the
        # same logic as above to ensure the totals reflect loaded data.
        if val is None:
            missing_cache = True
        elif val == 0 and FigureSubmission.objects.exists():
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
            "name": sc.name,
            "formatted": formatted,
            "raw": value,
            "duration": sc.duration,
            "precision": sc.precision,
            "show_currency": sc.show_currency,
            "friendly_format": sc.friendly_format,
            "explanation": sc.explanation,
            "columns": sc.columns,
            "factoids": get_factoids(
                sc.counter.slug,
                {"value": formatted, "raw": value, "previous_raw": prev_value},
            ),
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
        "query": query,
        "councils": councils,
        "total_debt": total_debt,
        "promoted_counters": promoted,
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
            share_data = None

    # Pull all financial figures for this council so the template can
    # present them in an engaging way.
    # Only include figures relevant to this council's type. When a DataField
    # has no specific types assigned it applies to all councils.
    figures = FigureSubmission.objects.filter(council=council).select_related(
        "year", "field"
    )
    if council.council_type_id:
        figures = figures.filter(
            Q(field__council_types__isnull=True)
            | Q(field__council_types=council.council_type)
        )
    else:
        figures = figures.filter(field__council_types__isnull=True)
    figures = figures.order_by("year__label", "field__slug").distinct()

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
                "factoids": get_factoids(
                    counter.slug,
                    {
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
            if council.latest_population is not None:
                display = field.display_value(str(council.latest_population))
            else:
                display = "No data"
            meta_values.append({"field": field, "value": display})
            continue
        fs = (
            FigureSubmission.objects.filter(council=council, field=field)
            .order_by("-year__label")
            .first()
        )
        if fs:
            display = field.display_value(fs.value)
        else:
            display = "No data"
        meta_values.append({"field": field, "value": display})

    is_following = False
    if request.user.is_authenticated:
        from .models import CouncilFollow

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
        
    edit_figures = figures.filter(year=edit_selected_year) if edit_selected_year else figures.none()

    missing_characteristic_page = None
    missing_characteristic_paginator = None
    if tab == "edit":
        from .models import DataIssue
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
    # No extra context is required when editing since characteristic drop-downs
    # were replaced by the missing-characteristics table.

    return render(request, "council_finance/council_detail.html", context)


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
    """Show recent updates for councils the user follows."""

    if not request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("login")

    from .models import CouncilFollow, CouncilUpdate

    followed_ids = CouncilFollow.objects.filter(user=request.user).values_list("council_id", flat=True)
    updates = (
        CouncilUpdate.objects.filter(council_id__in=followed_ids)
        .select_related("council")
        .order_by("-created")[:50]
    )

    comment_forms = {u.id: UpdateCommentForm() for u in updates}

    context = {"updates": updates, "comment_forms": comment_forms}
    return render(request, "council_finance/following.html", context)


def contribute(request):
    """Show a modern, real-time contribute interface with AJAX editing."""
    
    from .models import DataIssue, UserProfile, Contribution
    from .data_quality import assess_data_issues

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
    
    from .models import DataIssue, Contribution
    
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
        from .smart_data_quality import get_data_collection_priorities
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
        from .models import DataIssue
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

        from .models import DataIssue, Contribution
        from .data_quality import assess_data_issues

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
    """Return the moderator side panel HTML."""
    if not request.user.is_authenticated or request.user.profile.tier.level < 3:
        return HttpResponseBadRequest("permission denied")

    pending = (
        Contribution.objects.filter(status="pending")
        .select_related("council", "field", "user", "year")[:10]
    )

    html = render_to_string(
        "council_finance/moderator_panel.html",
        {"pending": pending},
        request=request,
    )
    return JsonResponse({"html": html})


def my_profile(request):
    """Simpler social style profile page with editable options."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("login")

    user = request.user
    profile, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"confirmation_token": get_random_string(32)}
    )

    form = ProfileExtraForm(request.POST or None, instance=profile)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile details saved.")
        # Allow superusers to change their active tier for testing.
        if user.is_superuser and "tier" in request.POST:
            tier = TrustTier.objects.filter(id=request.POST.get("tier")).first()
            if tier:
                profile.tier = tier
                profile.save()
        # Save the preferred font choice when provided.
        if "preferred_font" in request.POST:
            profile.preferred_font = request.POST.get("preferred_font") or "Cairo"
            profile.save()

    email = (user.email or "").strip().lower()
    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest() if email else ""
    gravatar_url = (
        f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"
        if email_hash
        else None
    )

    tiers = TrustTier.objects.all()
    # A short list of Google fonts to choose from. These names must match the
    # Google Fonts API as they are inserted directly into the request URL in
    # the base template.
    fonts = ["Cairo", "Roboto", "Lato", "Open Sans"]

    context = {
        "form": form,
        "profile": profile,
        "gravatar_url": gravatar_url,
        "tiers": tiers,
        "fonts": fonts,
    }
    return render(request, "council_finance/my_profile.html", context)


def about(request):
    """About page that can be populated from the admin later."""
    return render(request, "council_finance/about.html")


def terms_of_use(request):
    """Terms of use page."""
    return render(request, "council_finance/terms_of_use.html")


def privacy_cookies(request):
    """Show cookie usage and brief privacy policy."""
    return render(request, "council_finance/privacy_cookies.html")


def corrections(request):
    """Allow visitors to submit correction requests."""
    submitted = False
    if request.method == "POST":
        # Later we might store the message in the database
        submitted = True
    return render(request, "council_finance/corrections.html", {"submitted": submitted})


@login_required
def counter_definition_list(request):
    """Display a list of existing counters for quick management."""
    from django.core.paginator import Paginator
    from .models import SiteCounter, GroupCounter

    # Base queryset - include created_by for permission checks
    counters = CounterDefinition.objects.select_related('created_by').all().order_by('name')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        counters = counters.filter(name__icontains=search_query)
    
    # Apply type filter
    type_filter = request.GET.get('type', '')
    if type_filter:
        if type_filter == 'headline':
            counters = counters.filter(headline=True)
        elif type_filter == 'default':
            counters = counters.filter(show_by_default=True)
        elif type_filter == 'currency':
            counters = counters.filter(show_currency=True)
        elif type_filter == 'friendly':
            counters = counters.filter(friendly_format=True)
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    # We'll handle this in the template for now since it requires counting usage
    
    # Paginate
    page_size = int(request.GET.get('page_size', 15))
    paginator = Paginator(counters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_definitions = CounterDefinition.objects.count()
    total_site_counters = SiteCounter.objects.count()
    total_group_counters = GroupCounter.objects.count()
    
    # Count unused counters (definitions not used in site or group counters)
    used_definition_ids = set()
    used_definition_ids.update(SiteCounter.objects.values_list('counter_id', flat=True))
    used_definition_ids.update(GroupCounter.objects.values_list('counter_id', flat=True))
    unused_counters = total_definitions - len(used_definition_ids)
    
    # Add usage counts to each counter
    for counter in page_obj:
        counter.site_counter_count = SiteCounter.objects.filter(counter=counter).count()
        counter.group_counter_count = GroupCounter.objects.filter(counter=counter).count()
        counter.council_counter_count = 0  # This would require checking actual council page usage
    
    # Add usage counts to each counter
    for counter in page_obj:
        counter.site_counter_count = SiteCounter.objects.filter(counter=counter).count()
        counter.group_counter_count = GroupCounter.objects.filter(counter=counter).count()
        counter.council_counter_count = 0  # This would require checking actual council page usage
    
    stats = {
        'total_definitions': total_definitions,
        'total_site_counters': total_site_counters,
        'total_group_counters': total_group_counters,
        'unused_counters': unused_counters,
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'search_query': search_query,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'page_size': page_size,
    }
    
    return render(
        request,
        "council_finance/counter_definition_list.html",
        context,
    )


@login_required
def counter_delete(request, slug):
    """Delete a counter definition if the user has permission."""
    counter = get_object_or_404(CounterDefinition, slug=slug)
    
    # Check if user has permission to delete this counter
    if not (request.user.is_superuser or counter.created_by == request.user):
        messages.error(request, "You don't have permission to delete this counter.")
        return redirect('counter_definitions')
    
    # Check if counter is being used
    site_counter_count = SiteCounter.objects.filter(counter=counter).count()
    group_counter_count = GroupCounter.objects.filter(counter=counter).count()
    
    if site_counter_count > 0 or group_counter_count > 0:
        messages.warning(
            request, 
            f"This counter is currently in use ({site_counter_count} site counters, {group_counter_count} group counters). "
            "Please remove those references first."
        )
        return redirect('counter_definitions')
    
    # Process the deletion
    counter_name = counter.name
    counter.delete()
    
    messages.success(request, f"Counter '{counter_name}' was successfully deleted.")
    log_activity(
        request,
        activity="counter_delete",
        action=f"deleted counter definition: {slug}",
        extra={"counter_name": counter_name}
    )
    
    return redirect('counter_definitions')


@login_required
def site_counter_list(request):
    """List all site-wide counters."""
    from django.core.paginator import Paginator
    from .models import SiteCounter, CounterDefinition

    # Base queryset
    counters = SiteCounter.objects.all().select_related('counter', 'year').order_by('name')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        counters = counters.filter(name__icontains=search_query)
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        if status_filter == 'homepage':
            counters = counters.filter(promote_homepage=True)
        elif status_filter == 'currency':
            counters = counters.filter(show_currency=True)
        elif status_filter == 'friendly':
            counters = counters.filter(friendly_format=True)
    
    # Paginate
    page_size = int(request.GET.get('page_size', 10))
    paginator = Paginator(counters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_counters = SiteCounter.objects.count()
    homepage_counters = SiteCounter.objects.filter(promote_homepage=True).count()
    available_base_counters = CounterDefinition.objects.count()
    
    context = {
        'page_obj': page_obj,
        'total_counters': total_counters,
        'homepage_counters': homepage_counters,
        'available_base_counters': available_base_counters,
        'search_query': search_query,
        'status_filter': status_filter,
        'page_size': page_size,
    }
    
    return render(
        request,
        "council_finance/site_counter_list.html",
        context,
    )


@login_required
def group_counter_list(request):
    """List all custom group counters."""
    from django.core.paginator import Paginator
    from .models import GroupCounter, CounterDefinition

    # Base queryset
    counters = GroupCounter.objects.all().select_related('counter', 'year', 'council_list').order_by('name')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        counters = counters.filter(name__icontains=search_query)
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        if status_filter == 'homepage':
            counters = counters.filter(promote_homepage=True)
        elif status_filter == 'currency':
            counters = counters.filter(show_currency=True)
        elif status_filter == 'friendly':
            counters = counters.filter(friendly_format=True)
    
    # Paginate
    page_size = int(request.GET.get('page_size', 10))
    paginator = Paginator(counters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_counters = GroupCounter.objects.count()
    homepage_counters = GroupCounter.objects.filter(promote_homepage=True).count()
    available_base_counters = CounterDefinition.objects.count()
    
    context = {
        'page_obj': page_obj,
        'total_counters': total_counters,
        'homepage_counters': homepage_counters,
        'available_base_counters': available_base_counters,
        'search_query': search_query,
        'status_filter': status_filter,
        'page_size': page_size,
    }
    
    return render(
        request,
        "council_finance/group_counter_list.html",
        context,
    )


@login_required
def site_counter_form(request, slug=None):
    """Create or edit a site-wide counter."""
    from .models import SiteCounter, CounterDefinition, FinancialYear

    # For a new counter, we might auto-select a base counter definition
    base_slug = request.GET.get('base')
    base_counter = None
    if base_slug:
        base_counter = CounterDefinition.objects.filter(slug=base_slug).first()

    counter = get_object_or_404(SiteCounter, slug=slug) if slug else None
    
    # If we're creating a new counter with a base, pre-populate the form
    initial = {}
    if not counter and base_counter:
        initial = {
            'name': f"{base_counter.name} (Site)",
            'counter': base_counter,
            'show_currency': base_counter.show_currency,
            'friendly_format': base_counter.friendly_format,
            'precision': base_counter.precision,
            'duration': base_counter.duration,
        }

    form = SiteCounterForm(request.POST or None, instance=counter, initial=initial)
    
    if request.method == "POST" and form.is_valid():
        site_counter = form.save()
        messages.success(request, f"Site counter '{site_counter.name}' saved successfully.")
        log_activity(
            request,
            activity="site_counter_save",
            log_type="user",
            action=slug or "new",
            response="saved",
            extra={'counter_name': site_counter.name}
        )
        return redirect("site_counter_list")
    
    # Provide counter choices for the form
    counter_choices = CounterDefinition.objects.all().order_by('name')
    year_choices = FinancialYear.objects.all().order_by('-label')
    
    context = {
        "form": form,
        "counter": counter,
        "is_edit": slug is not None,
        "base_counter": base_counter,
        "counter_choices": counter_choices,
        "year_choices": year_choices,
        "title": f"Edit {counter.name}" if counter else "Add Site-Wide Counter",
    }
    
    return render(
        request,
        "council_finance/site_counter_form.html",
        context,
    )


@login_required
def site_counter_delete(request, slug):
    """Delete a site counter."""
    from .models import SiteCounter
    
    counter = get_object_or_404(SiteCounter, slug=slug)
    counter_name = counter.name
    
    counter.delete()
    messages.success(request, f"Site counter '{counter_name}' was successfully deleted.")
    log_activity(
        request,
        activity="site_counter_delete",
        action=f"deleted site counter: {slug}",
        extra={"counter_name": counter_name}
    )
    
    return redirect('site_counter_list')


@login_required
def group_counter_form(request, slug=None):
    """Create or edit a custom group counter."""

    from .models import GroupCounter

    counter = get_object_or_404(GroupCounter, slug=slug) if slug else None
    form = GroupCounterForm(request.POST or None, instance=counter)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Counter saved.")
        log_activity(
            request,
            activity="counter_group",
            log_type="user",
            action=slug or "new",
            response="saved",
        )
        return redirect("group_counter_list")
    return render(
        request,
        "council_finance/group_counter_form.html",
        {"form": form},
    )


@login_required
def group_counter_delete(request, slug):
    """Delete a group counter."""
    from .models import GroupCounter
    
    counter = get_object_or_404(GroupCounter, slug=slug)
    counter_name = counter.name
    
    counter.delete()
    messages.success(request, f"Group counter '{counter_name}' was successfully deleted.")
    log_activity(
        request,
        activity="group_counter_delete",
        action=f"deleted group counter: {slug}",
        extra={"counter_name": counter_name}
    )
    
    return redirect('group_counter_list')


@login_required
def counter_definition_form(request, slug=None):
    """Create or edit a single counter definition, with live preview for selected council."""

    from .models import Council

    counter = get_object_or_404(CounterDefinition, slug=slug) if slug else None
    form = CounterDefinitionForm(request.POST or None, instance=counter)

    # For preview dropdown: all councils and all years
    councils = Council.objects.all().order_by("name")
    years = list(FinancialYear.objects.order_by("-label"))
    for y in years:
        y.display_label = "Year to Date" if y.label.lower() == "general" else y.label
    preview_council_slug = request.GET.get("preview_council") or (
        councils[0].slug if councils else None
    )
    # Only use a valid year label for preview_year_label
    valid_year_labels = [y.label for y in years]
    requested_year = request.GET.get("preview_year")
    preview_year_label = (
        requested_year
        if requested_year in valid_year_labels
        else (years[0].label if years else None)
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Counter saved.")
        log_activity(
            request,
            activity="counter_definition",
            log_type="user",
            action=slug or "new",
            response="saved",
        )
        return redirect("counter_definitions")

    context = {
        "form": form,
        "available_fields": [f.slug for f in DataField.objects.all()],
        "councils": councils,
        "years": years,
        "preview_council_slug": preview_council_slug,
        "preview_year_label": preview_year_label,
    }
    return render(
        request,
        "council_finance/counter_definition_form.html",
        context,
    )



# AJAX endpoint for previewing counter value for a council and formula


@login_required
@require_GET
def preview_counter_value(request):
    from .agents.counter_agent import CounterAgent
    from .models import Council, FinancialYear

    council_slug = request.GET.get("council")
    formula = request.GET.get("formula")
    year_label = request.GET.get("year")
    year = None
    if year_label:
        year = FinancialYear.objects.filter(label=year_label).first()
    if not year:
        year = FinancialYear.objects.order_by("-label").first()
    if not (council_slug and formula and year):
        return JsonResponse({"error": "Missing data"}, status=400)
    agent = CounterAgent()
    from .models import CounterDefinition

    try:
        council = Council.objects.get(slug=council_slug)
        # Build a map of values while tracking any missing figures so we can
        # surface a clear error message instead of casting blank strings.
        figure_map = {}
        missing = set()
        for f in FigureSubmission.objects.filter(council=council, year=year):
            slug = f.field.slug
            if f.needs_populating or f.value in (None, ""):
                missing.add(slug)
                continue
            try:
                figure_map[slug] = float(f.value)
            except (TypeError, ValueError):
                missing.add(slug)
        import ast, operator

        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Num):
                return node.n
            if isinstance(node, ast.BinOp):
                return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                return -_eval(node.operand)
            if isinstance(node, ast.Name):
                if node.id in missing:
                    raise ValueError(
                        (
                            "Counter failed - no %s figure is held for %s in %s. "
                            "Please populate the figure from the council's official sources and try again."
                        )
                        % (node.id.replace("_", " "), council.name, year.label)
                    )
                return figure_map.get(node.id, 0)
            raise ValueError("Unsupported expression element")

        tree = ast.parse(formula, mode="eval")
        value = float(_eval(tree))
        precision = int(request.GET.get("precision", 0))
        show_currency = request.GET.get("show_currency", "true") == "true"
        friendly_format = request.GET.get("friendly_format", "false") == "true"

        class Dummy:
            pass

        dummy = Dummy()
        dummy.precision = precision
        dummy.show_currency = show_currency
        dummy.friendly_format = friendly_format
        from .models.counter import CounterDefinition as CD

        formatted = CD.format_value(dummy, value)
        return JsonResponse({"value": value, "formatted": formatted})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        return JsonResponse({"error": "calculation failed"}, status=400)


@login_required
@require_GET
def preview_aggregate_counter(request):
    """Preview a site or group counter by summing across councils."""
    from .agents.counter_agent import CounterAgent
    from .models import Council, FinancialYear, CouncilList, CounterDefinition

    counter_slug = request.GET.get("counter")
    if not counter_slug:
        return JsonResponse({"error": "Missing counter"}, status=400)
    year_param = request.GET.get("year")
    if year_param and year_param != "all":
        # ``year`` may be provided as either a label like "23/24" or the
        # primary key value from the model. Handle both to keep the
        # JavaScript simple.
        year = (
            FinancialYear.objects.filter(pk=year_param).first()
            if str(year_param).isdigit()
            else FinancialYear.objects.filter(label=year_param).first()
        )
        if not year:
            return JsonResponse({"error": "Invalid data"}, status=400)
        years = [year]
    else:
        years = list(FinancialYear.objects.order_by("-label"))
    counter = CounterDefinition.objects.filter(slug=counter_slug).first()
    if not counter or not years:
        return JsonResponse({"error": "Invalid data"}, status=400)

    councils = Council.objects.all()
    cslugs = request.GET.get("councils")
    if cslugs:
        councils = councils.filter(slug__in=[s for s in cslugs.split(",") if s])
    clist = request.GET.get("council_list")
    if clist:
        try:
            cl = CouncilList.objects.get(pk=clist)
            councils = councils.filter(pk__in=cl.councils.values_list("pk", flat=True))
        except CouncilList.DoesNotExist:
            pass
    ctypes = request.GET.get("council_types")
    if ctypes:
        ids = [int(i) for i in ctypes.split(",") if i]
        councils = councils.filter(council_type_id__in=ids)

    agent = CounterAgent()
    total = 0
    for c in councils:
        for yr in years:
            values = agent.run(council_slug=c.slug, year_label=yr.label)
            result = values.get(counter_slug)
            if result and result.get("value") is not None:
                try:
                    total += float(result["value"])
                except (TypeError, ValueError):
                    pass

    dummy = type(
        "D",
        (),
        {
            "precision": int(request.GET.get("precision", 0)),
            "show_currency": request.GET.get("show_currency", "true") == "true",
            "friendly_format": request.GET.get("friendly_format", "false") == "true",
        },
    )()

    # ``format_value`` lives on ``CounterDefinition`` and expects the instance
    # to provide precision, show_currency and friendly_format attributes.
    # Using the dummy object lets us preview arbitrary settings.
    formatted = CounterDefinition.format_value(dummy, total)
    return JsonResponse({"value": total, "formatted": formatted})


@login_required
@require_GET
def preview_factoid(request):
    """Return the rendered factoid text for a counter, council and year."""
    from .agents.counter_agent import CounterAgent
    from .models import Council, FinancialYear, CounterDefinition

    # ``counter`` may be provided as a slug or primary key. Form widgets use
    # primary keys by default while JavaScript previews sometimes pass slugs.
    # Accept either format for convenience.
    counter_value = request.GET.get("counter")
    council_slug = request.GET.get("council")
    year_label = request.GET.get("year")
    text = request.GET.get("text", "")
    ftype = request.GET.get("type", "")

    if not (counter_value and council_slug and year_label and text):
        return JsonResponse({"error": "Missing data"}, status=400)

    year = FinancialYear.objects.filter(label=year_label).first()
    if not year:
        return JsonResponse({"error": "Invalid year"}, status=400)

    counter = CounterDefinition.objects.filter(slug=counter_value).first()
    if not counter:
        # Fall back to lookup by primary key so the preview works when the form
        # submits IDs.
        try:
            counter = CounterDefinition.objects.filter(pk=int(counter_value)).first()
        except (TypeError, ValueError):
            counter = None
    if not counter:
        return JsonResponse({"error": "Invalid counter"}, status=400)

    if not FigureSubmission.objects.filter(council__slug=council_slug, year=year).exists():
        return JsonResponse({"error": "No data for the selected year"}, status=400)

    agent = CounterAgent()
    values = agent.run(council_slug=council_slug, year_label=year.label)
    result = values.get(counter.slug)
    if not result or result.get("value") in (None, ""):
        return JsonResponse({"error": "No data for the selected year"}, status=400)

    value_str = result.get("formatted")
    if ftype == "percent_change":
        prev_label = previous_year_label(year.label)
        prev_value = None
        if prev_label:
            prev_year = FinancialYear.objects.filter(label=prev_label).first()
            if prev_year:
                prev_values = agent.run(council_slug=council_slug, year_label=prev_year.label)
                prev = prev_values.get(counter.slug)
                if prev:
                    prev_value = prev.get("value")
        if prev_value in (None, ""):
            return JsonResponse({"error": "No previous data to compare"}, status=400)
        try:
            change = (float(result.get("value")) - float(prev_value)) / float(prev_value) * 100
            value_str = f"{change:.1f}%"
        except Exception:
            return JsonResponse({"error": "No previous data to compare"}, status=400)

    class SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    rendered = text.format_map(SafeDict(value=value_str))
    return JsonResponse({"text": rendered})


@login_required
def profile_view(request):
    """Enhanced user profile view with comprehensive management features"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    from django.contrib import messages
    from django.utils.crypto import get_random_string
    from django.contrib.auth.hashers import make_password
    from django.urls import reverse
    import hashlib
    
    user = request.user
    # Ensure we always have a profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"confirmation_token": get_random_string(32)},
    )

    tab = request.GET.get("tab", "profile")

    # Handle form submissions
    if request.method == "POST":
        if "preferred_font" in request.POST:
            # Save font preferences
            profile.preferred_font = request.POST.get("preferred_font", "Cairo")
            profile.font_size = request.POST.get("font_size", "medium")
            profile.high_contrast_mode = request.POST.get("high_contrast_mode") == "on"
            profile.color_theme = request.POST.get("color_theme", "auto")
            profile.save()
            messages.success(request, "Display preferences saved.")
            tab = "display"
            
        elif "update_profile" in request.POST:
            # Update basic profile info
            profile.postcode = request.POST.get("postcode", "")
            profile.postcode_refused = request.POST.get("postcode_refused") == "on"
            profile.political_affiliation = request.POST.get("political_affiliation", "")
            profile.works_for_council = request.POST.get("works_for_council") == "on"
            
            employer_council_id = request.POST.get("employer_council")
            if employer_council_id:
                from .models import Council
                profile.employer_council = Council.objects.filter(id=employer_council_id).first()
            else:
                profile.employer_council = None
                
            profile.official_email = request.POST.get("official_email", "")
            profile.save()
            messages.success(request, "Profile details updated.")
            
        elif "visibility" in request.POST:
            profile.visibility = request.POST.get("visibility", profile.visibility)
            profile.save()
            messages.success(request, "Privacy settings updated.")
            tab = "privacy"
            
        elif user.is_superuser and "tier" in request.POST:
            # Allow superusers to change tier
            tier = TrustTier.objects.filter(id=request.POST.get("tier")).first()
            if tier:
                profile.tier = tier
                profile.save()
                messages.success(request, f"Tier changed to {tier.name}.")
            tab = "advanced"

    # Gather data for template
    followers = UserFollow.objects.filter(target=user).select_related("follower")
    following = UserFollow.objects.filter(follower=user).select_related("target")
    
    # Gravatar
    email = (user.email or "").strip().lower()
    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest() if email else ""
    gravatar_url = (
        f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=150"
        if email_hash
        else None
    )
    
    # Statistics
    from .models import Contribution, Council
    contributions = Contribution.objects.filter(user=user)
    approved_contributions = contributions.filter(status='approved')
    pending_contributions = contributions.filter(status='pending')
    
    # Leaderboard position
    users_with_more_points = UserProfile.objects.filter(points__gt=profile.points).count()
    rank = users_with_more_points + 1
    
    context = {
        'user': user,
        'profile': profile,
        'tab': tab,
        'gravatar_url': gravatar_url,
        'followers': followers,
        'following': following,
        'rank': rank,
        'contributions_count': contributions.count(),
        'approved_count': approved_contributions.count(),
        'pending_count': pending_contributions.count(),
        'recent_contributions': contributions.order_by('-created')[:5],
        'visibility_choices': UserProfile.VISIBILITY_CHOICES,
        'font_size_choices': UserProfile.FONT_SIZE_CHOICES,
        'theme_choices': UserProfile.THEME_CHOICES,
        'councils': Council.objects.all().order_by('name'),
        'tiers': TrustTier.objects.all(),
        'fonts': ["Cairo", "Roboto", "Lato", "Open Sans", "Inter", "Poppins"],
    }
    
    return render(request, 'council_finance/profile.html', context)

def user_preferences_view(request):
    """User preferences view"""
    from django.http import HttpResponse
    return HttpResponse("User Preferences - Not implemented yet")

def user_preferences_ajax(request):
    """User preferences AJAX"""
    from django.http import JsonResponse
    return JsonResponse({"message": "User Preferences AJAX - Not implemented yet"})

def council_list(request):
    """Display list of councils with filters and search"""
    from .models import Council
    from django.core.paginator import Paginator
    
    councils = Council.objects.filter(status='active').order_by('name')
    
    # Apply search if provided
    search = request.GET.get('search', '')
    if search:
        councils = councils.filter(name__icontains=search)
    
    # Apply filters
    council_type = request.GET.get('type')
    if council_type:
        councils = councils.filter(council_type__name=council_type)
    
    # Paginate
    paginator = Paginator(councils, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'council_type': council_type
    }
    
    return render(request, 'council_finance/council_list.html', context)

def generate_share_link(request):
    """Generate share link"""
    from django.http import JsonResponse
    return JsonResponse({"message": "Generate Share Link - Not implemented yet"})

def signup_view(request):
    """User signup view"""
    from django.http import HttpResponse
    return HttpResponse("Signup - Not implemented yet")

def confirm_email(request, token):
    """Confirm email address with token"""
    from django.http import HttpResponse
    return HttpResponse("Confirm Email - Not implemented yet")

def resend_confirmation(request):
    """Resend confirmation email"""
    from django.http import HttpResponse
    return HttpResponse("Resend Confirmation - Not implemented yet")

def update_postcode(request):
    """Update user postcode"""
    from django.http import JsonResponse
    return JsonResponse({"status": "success"})

def confirm_profile_change(request, token):
    """Confirm profile change"""
    from django.http import HttpResponse
    return HttpResponse("Confirm Profile Change - Not implemented yet")

def notifications_page(request):
    """Notifications page"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    notifications = request.user.notifications.all().order_by('-created')[:20]
    return render(request, 'notifications.html', {
        'notifications': notifications
    })


@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        notification = request.user.notifications.get(id=notification_id)
        notification.read = True
        notification.save()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False, 'error': 'Notification not found'})


@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        request.user.notifications.filter(read=False).update(read=True)
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False, 'error': 'Failed to update notifications'})

def council_counters(request, slug):
    """Display counters for a specific council as JSON or HTML."""
    council = get_object_or_404(Council, slug=slug)
    
    # Get the selected year from request or use default
    years = list(FinancialYear.objects.order_by("-label").exclude(label__iexact="general"))
    default_label = SiteSetting.get("default_financial_year", settings.DEFAULT_FINANCIAL_YEAR)
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
                "description": counter.description,
            }
            
            if counter.show_on_homepage:
                head_list.append(counter_info)
            else:
                other_list.append(counter_info)
        
        counters = head_list + other_list
    
    # Return JSON if requested via AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "counters": [
                {
                    "slug": c["slug"],
                    "name": c["name"],
                    "description": c["description"],
                    "value": c["value"],
                    "formatted": c["formatted"],
                    "error": c["error"],
                }
                for c in counters
            ],
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

def dismiss_notification(request, notification_id):
    """Dismiss a specific notification."""
    if not request.user.is_authenticated:
        return redirect("login")
    
    from django.http import JsonResponse
    # TODO: Implement notification dismissal logic
    return JsonResponse({"status": "success", "message": "Notification dismissed"})


def review_contribution(request, pk, action):
    """Review a contribution (approve/reject)."""
    from django.http import JsonResponse
    # TODO: Implement contribution review logic
    return JsonResponse({"status": "success", "message": f"Contribution {action}ed"})


def edit_figures_table(request, slug):
    """Edit figures table for a council via AJAX."""
    from django.http import JsonResponse
    # TODO: Implement figures table editing
    return JsonResponse({"status": "success", "message": "Table edit interface"})


def add_favourite(request):
    """Add a council to user's favourites."""
    from django.http import JsonResponse
    # TODO: Implement favourite management
    return JsonResponse({"status": "success", "message": "Added to favourites"})


def remove_favourite(request):
    """Remove a council from user's favourites."""
    from django.http import JsonResponse
    # TODO: Implement favourite management
    return JsonResponse({"status": "success", "message": "Removed from favourites"})


def add_to_list(request, list_id):
    """Add a council to a specific list."""
    from django.http import JsonResponse
    # TODO: Implement list management
    return JsonResponse({"status": "success", "message": "Added to list"})


def remove_from_list(request, list_id):
    """Remove a council from a specific list."""
    from django.http import JsonResponse
    # TODO: Implement list management
    return JsonResponse({"status": "success", "message": "Removed from list"})


def move_between_lists(request):
    """Move a council between lists."""
    from django.http import JsonResponse
    # TODO: Implement list management
    return JsonResponse({"status": "success", "message": "Moved between lists"})


def list_metric(request, list_id):
    """Get metric data for a list."""
    from django.http import JsonResponse
    # TODO: Implement list metrics
    return JsonResponse({"status": "success", "data": {}})


def add_to_compare(request, slug):
    """Add a council to comparison basket."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from council_finance.models import Council
    
    council = get_object_or_404(Council, slug=slug)
    
    # Initialize session basket if it doesn't exist
    if 'compare_basket' not in request.session:
        request.session['compare_basket'] = []
    
    # Check if council is already in basket
    if slug not in request.session['compare_basket']:
        # Limit to maximum 5 councils for comparison
        if len(request.session['compare_basket']) >= 5:
            return JsonResponse({
                "status": "error", 
                "message": "Maximum 5 councils can be compared at once"
            })
        
        request.session['compare_basket'].append(slug)
        request.session.modified = True
        
        return JsonResponse({
            "status": "success", 
            "message": f"{council.name} added to comparison",
            "count": len(request.session['compare_basket'])
        })
    else:
        return JsonResponse({
            "status": "info", 
            "message": f"{council.name} is already in comparison basket",
            "count": len(request.session['compare_basket'])
        })


def remove_from_compare(request, slug):
    """Remove a council from comparison basket."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from council_finance.models import Council
    
    council = get_object_or_404(Council, slug=slug)
    
    # Initialize session basket if it doesn't exist
    if 'compare_basket' not in request.session:
        request.session['compare_basket'] = []
    
    # Remove council from basket if it exists
    if slug in request.session['compare_basket']:
        request.session['compare_basket'].remove(slug)
        request.session.modified = True
        
        return JsonResponse({
            "status": "success", 
            "message": f"{council.name} removed from comparison",
            "count": len(request.session['compare_basket'])
        })
    else:
        return JsonResponse({
            "status": "info", 
            "message": f"{council.name} was not in comparison basket",
            "count": len(request.session['compare_basket'])
        })


def compare_row(request):
    """Get comparison row data for a specific field."""
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    from django.template.loader import render_to_string
    from council_finance.models import Council, DataField, FinancialFigure, CouncilCharacteristic
    from decimal import Decimal
    import statistics
    import json
    
    field_slug = request.GET.get('field')
    if not field_slug:
        return JsonResponse({"status": "error", "message": "Field slug required"})
    
    field = get_object_or_404(DataField, slug=field_slug)
    
    # Get councils from session basket
    basket_slugs = request.session.get('compare_basket', [])
    if not basket_slugs:
        return JsonResponse({"status": "error", "message": "No councils in comparison basket"})
    
    councils = Council.objects.filter(slug__in=basket_slugs).order_by('name')
    
    # Get values for each council
    values = []
    numeric_values = []
    
    for council in councils:
        value = None
        display_value = "No data"
        
        # Try to get value based on field category
        if field.category == 'characteristic':
            try:
                characteristic = CouncilCharacteristic.objects.get(council=council, field=field)
                value = characteristic.value
                display_value = field.display_value(value) if value else "No data"
            except CouncilCharacteristic.DoesNotExist:
                pass
        else:
            # For financial figures, get the latest year's data
            try:
                latest_figure = FinancialFigure.objects.filter(
                    council=council, 
                    field=field
                ).order_by('-year__label').first()
                
                if latest_figure and latest_figure.value is not None:
                    value = float(latest_figure.value)
                    display_value = field.display_value(str(latest_figure.value))
                    numeric_values.append(value)
            except (FinancialFigure.DoesNotExist, ValueError, TypeError):
                pass
        
        values.append(display_value)
    
    # Calculate summary statistics for numeric fields
    summary = None
    if numeric_values and field.content_type in ['monetary', 'integer']:
        try:
            summary = {
                'total': field.display_value(str(sum(numeric_values))),
                'average': field.display_value(str(sum(numeric_values) / len(numeric_values))),
                'highest': field.display_value(str(max(numeric_values))),
                'lowest': field.display_value(str(min(numeric_values))),
            }
        except (ValueError, ZeroDivisionError):
            pass
    
    # Render the row HTML
    row_html = render_to_string('council_finance/compare_row.html', {
        'field': field,
        'values': values,
        'summary': summary
    })
    
    # Clean up the HTML to prevent JSON issues
    row_html = row_html.strip()
    
    # Use HttpResponse with manual JSON to avoid HTML escaping
    response_data = {
        "status": "success", 
        "html": row_html,
        "field_name": field.name
    }
    
    return HttpResponse(
        json.dumps(response_data, ensure_ascii=False),
        content_type='application/json'
    )


def compare_basket(request):
    """Display comparison basket page with e-commerce style comparison tool."""
    from django.shortcuts import redirect
    from django.utils import timezone
    from council_finance.models import Council, DataField, CouncilList, FinancialFigure, CouncilCharacteristic
    from decimal import Decimal
    
    # Handle saving as custom list
    if request.method == 'POST' and request.POST.get('save_list'):
        if request.user.is_authenticated:
            list_name = request.POST.get('name', '').strip()
            if list_name:
                basket_slugs = request.session.get('compare_basket', [])
                councils = Council.objects.filter(slug__in=basket_slugs)
                
                # Create the list
                council_list = CouncilList.objects.create(
                    name=list_name,
                    user=request.user,
                    description=f"Comparison basket saved on {timezone.now().strftime('%Y-%m-%d')}"
                )
                council_list.councils.set(councils)
                
                # Add success message (you might want to use Django messages framework)
                context = {
                    'save_success': True,
                    'list_name': list_name
                }
                return render(request, "council_finance/comparison_basket.html", context)
    
    # Get councils from session basket
    basket_slugs = request.session.get('compare_basket', [])
    councils = Council.objects.filter(slug__in=basket_slugs).order_by('name')
    
    # Get available data fields for comparison
    field_choices = DataField.objects.all().order_by('category', 'name')
    
    # Get default comparison rows (show some key fields by default)
    default_fields = ['council_type', 'population', 'council_nation']
    rows = []
    
    for field_slug in default_fields:
        try:
            field = DataField.objects.get(slug=field_slug)
            values = []
            numeric_values = []
            
            for council in councils:
                value = None
                display_value = "No data"
                
                # Get characteristic data
                if field.category == 'characteristic':
                    try:
                        characteristic = CouncilCharacteristic.objects.get(council=council, field=field)
                        value = characteristic.value
                        display_value = field.display_value(value) if value else "No data"
                    except CouncilCharacteristic.DoesNotExist:
                        # Fallback to council attributes for core fields
                        if field_slug == 'council_type' and hasattr(council, 'council_type'):
                            display_value = str(council.council_type)
                        elif field_slug == 'population' and hasattr(council, 'latest_population'):
                            display_value = f"{council.latest_population:,}" if council.latest_population else "No data"
                        elif field_slug == 'council_nation' and hasattr(council, 'council_nation'):
                            display_value = str(council.council_nation)
                else:
                    # For financial figures, get the latest year's data
                    try:
                        latest_figure = FinancialFigure.objects.filter(
                            council=council, 
                            field=field
                        ).order_by('-year__label').first()
                        
                        if latest_figure and latest_figure.value is not None:
                            value = float(latest_figure.value)
                            display_value = field.display_value(str(latest_figure.value))
                            numeric_values.append(value)
                    except (FinancialFigure.DoesNotExist, ValueError, TypeError):
                        pass
                
                values.append(display_value)
            
            # Calculate summary for numeric fields
            summary = None
            if numeric_values and field.content_type in ['monetary', 'integer']:
                try:
                    summary = {
                        'total': field.display_value(str(sum(numeric_values))),
                        'average': field.display_value(str(sum(numeric_values) / len(numeric_values))),
                        'highest': field.display_value(str(max(numeric_values))),
                        'lowest': field.display_value(str(min(numeric_values))),
                    }
                except (ValueError, ZeroDivisionError):
                    pass
            
            rows.append({
                'field': field,
                'values': values,
                'summary': summary
            })
            
        except DataField.DoesNotExist:
            continue
    
    context = {
        'councils': councils,
        'field_choices': field_choices,
        'rows': rows,
    }
    
    return render(request, "council_finance/comparison_basket.html", context)


def clear_compare_basket(request):
    """Clear all councils from comparison basket."""
    from django.http import JsonResponse
    
    if request.method == 'POST':
        request.session['compare_basket'] = []
        request.session.modified = True
        return JsonResponse({"status": "success", "message": "Comparison basket cleared"})
    
    return JsonResponse({"status": "error", "message": "Invalid request method"})


def follow_council(request, slug):
    """Follow a council for updates."""
    from django.http import JsonResponse
    # TODO: Implement following functionality
    return JsonResponse({"status": "success", "message": "Following council"})


def unfollow_council(request, slug):
    """Unfollow a council."""
    from django.http import JsonResponse
    # TODO: Implement following functionality
    return JsonResponse({"status": "success", "message": "Unfollowed council"})


def like_update(request, update_id):
    """Like an update."""
    from django.http import JsonResponse
    # TODO: Implement update liking
    return JsonResponse({"status": "success", "message": "Update liked"})


def comment_update(request, update_id):
    """Comment on an update."""
    from django.http import JsonResponse
    # TODO: Implement update commenting
    return JsonResponse({"status": "success"})


# Contribution views
def submit_contribution(request):
    """Submit a contribution."""
    from django.http import JsonResponse
    # TODO: Implement contribution submission
    return JsonResponse({"status": "success"})


def review_contribution(request, pk, action):
    """Review a contribution."""
    from django.http import JsonResponse
    # TODO: Implement contribution review
    return JsonResponse({"status": "success"})


# Field management views
def field_list(request):
    """List all data fields for management."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get all fields grouped by category
    fields = DataField.objects.all().prefetch_related('council_types').order_by('category', 'name')
    
    # Get all available categories for grouping
    categories = DataField.FIELD_CATEGORIES
    
    context = {
        'title': 'Fields & Characteristics Manager',
        'fields': fields,
        'categories': categories,
    }
    
    log_activity(
        request,
        activity="field_list_view",
        action="viewed field management page",
        extra={'field_count': fields.count()}
    )
    
    return render(request, "council_finance/field_list.html", context)


def field_form(request, slug=None):
    """Create or edit a data field."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Determine if we're editing or creating
    field = None
    is_edit = False
    if slug:
        field = get_object_or_404(DataField, slug=slug)
        is_edit = True
    
    if request.method == 'POST':
        form = DataFieldForm(request.POST, instance=field)
        if form.is_valid():
            field = form.save()
            
            action = "updated" if is_edit else "created"
            messages.success(request, f'Field "{field.name}" {action} successfully.')
            
            log_activity(
                request,
                activity="field_form",
                action=f"{action} field: {field.slug}",
                extra={'field_name': field.name, 'field_category': field.category}
            )
            
            return redirect('field_list')
    else:
        form = DataFieldForm(instance=field)
    
    context = {
        'title': f'{"Edit" if is_edit else "Add"} Field',
        'form': form,
        'field': field,
        'is_edit': is_edit,
    }
    
    return render(request, "council_finance/field_form.html", context)


def field_delete(request, slug):
    """Delete a data field."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    field = get_object_or_404(DataField, slug=slug)
    
    # Check if field is protected
    if field.is_protected:
        messages.error(request, f'Field "{field.name}" is protected and cannot be deleted.')
        return redirect('field_list')
    
    if request.method == 'POST':
        try:
            field_name = field.name
            field.delete()
            messages.success(request, f'Field "{field_name}" deleted successfully.')
            
            log_activity(
                request,
                activity="field_delete",
                action=f"deleted field: {slug}",
                extra={'field_name': field_name}
            )
            
            return JsonResponse({"status": "success", "message": f"Field '{field_name}' deleted successfully"})
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error deleting field {slug}: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred while deleting the field"}, status=500)
    
    # For GET requests, show confirmation page
    context = {
        'title': f'Delete Field: {field.name}',
        'field': field,
    }
    
    return render(request, "council_finance/field_delete.html", context)


def factoid_list(request):
    """List all factoids for management."""
    # TODO: Implement factoid management
    return render(request, "council_finance/factoid_list.html", {})


def factoid_form(request, slug=None):
    """Create or edit a factoid."""
    # TODO: Implement factoid form
    return render(request, "council_finance/factoid_form.html", {})


def factoid_delete(request, slug):
    """Delete a factoid."""
    from django.http import JsonResponse
    # TODO: Implement factoid deletion
    return JsonResponse({"status": "success", "message": "Factoid deleted"})


def god_mode(request):
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


