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

import csv
import hashlib
import inspect
import json

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
        return JsonResponse({"error": "not_found"}, status=404)

    if field.content_type != "list" or not field.dataset_type:
        return JsonResponse({"error": "invalid"}, status=400)

    model = field.dataset_type.model_class()
    options = list(model.objects.values("id", "name"))
    return JsonResponse({"options": options})


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
    # God Mode: Mark DataIssue as invalid
    if request.method == "POST" and request.user.is_superuser and "mark_invalid" in request.POST:
        issue_id = request.POST.get("issue_id")
        DataIssue.objects.filter(id=issue_id).delete()
        return JsonResponse({"status": "ok", "message": "Issue marked invalid and removed."})
    """Show a modern, real-time contribute interface with AJAX editing."""

    from .models import DataIssue, UserProfile
    from .data_quality import assess_data_issues

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
        },
    )


@require_GET
def contribute_stats(request):
    """Return statistics for the contribute page sidebar."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    
    from .models import DataIssue, Contribution
    
    # Get detailed breakdown of missing data by category - only for active councils
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
    
    stats = {
        'missing': missing_total,
        'missing_characteristics': missing_characteristics,
        'missing_financial': missing_financial,
        'pending': Contribution.objects.filter(status='pending').count(),
        'suspicious': DataIssue.objects.filter(issue_type='suspicious').count(),
    }
    
    return JsonResponse(stats)


@require_POST  
def contribute_submit(request):
    """Handle AJAX contribution submissions from the quick edit modal."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    
    # Reuse the existing submit_contribution logic
    return submit_contribution(request)


def data_issues_table(request):
    """Return a page of data issues as HTML for the contribute tables."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")

    from .models import DataIssue, Contribution
    from .data_quality import assess_data_issues

    issue_type = request.GET.get("type")
    if issue_type not in {"missing", "suspicious", "pending"}:
        return HttpResponseBadRequest("invalid type")

    search = request.GET.get("q", "").strip()
    category = request.GET.get("category")
    order = request.GET.get("order", "council")
    direction = request.GET.get("dir", "asc")
    allowed = {"council": "council__name", "field": "field__name", "year": "year__label", "value": "value"}
    order_by = allowed.get(order, "council__name")
    if direction == "desc":
        order_by = f"-{order_by}"

    if request.GET.get("refresh"):
        assess_data_issues()
    if issue_type == "pending":
        qs = Contribution.objects.filter(status="pending").select_related("council", "field", "user", "year")
        if search:
            qs = qs.filter(Q(council__name__icontains=search) | Q(field__name__icontains=search))
        qs = qs.order_by(order_by)
    else:
        qs = DataIssue.objects.filter(issue_type=issue_type, council__status="active").select_related("council", "field", "year")
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

    if issue_type == "pending":
        html = render_to_string(
            "council_finance/pending_table.html",
            {"page_obj": page, "paginator": paginator},
            request=request,
        )
    else:
        show_year = not (issue_type == "missing" and category == "characteristic")
        html = render_to_string(
            "council_finance/data_issues_table_enhanced.html",
            {
                "page_obj": page,
                "paginator": paginator,
                "issue_type": issue_type,
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

    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()

    counters = CounterDefinition.objects.all()
    return render(
        request,
        "council_finance/counter_definition_list.html",
        {"counters": counters},
    )


@login_required
def site_counter_list(request):
    """List all site-wide counters."""

    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()

    from .models import SiteCounter

    counters = SiteCounter.objects.all()
    return render(
        request,
        "council_finance/site_counter_list.html",
        {"counters": counters},
    )


@login_required
def group_counter_list(request):
    """List all custom group counters."""

    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()

    from .models import GroupCounter

    counters = GroupCounter.objects.all()
    return render(
        request,
        "council_finance/group_counter_list.html",
        {"counters": counters},
    )


@login_required
def site_counter_form(request, slug=None):
    """Create or edit a site-wide counter."""

    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()

    from .models import SiteCounter

    counter = get_object_or_404(SiteCounter, slug=slug) if slug else None
    form = SiteCounterForm(request.POST or None, instance=counter)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Counter saved.")
        log_activity(
            request,
            activity="counter_site",
            log_type="user",
            action=slug or "new",
            response="saved",
        )
        return redirect("site_counter_list")
    return render(
        request,
        "council_finance/site_counter_form.html",
        {"form": form},
    )


@login_required
def group_counter_form(request, slug=None):
    """Create or edit a custom group counter."""

    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()

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
def counter_definition_form(request, slug=None):
    """Create or edit a single counter definition, with live preview for selected council."""

    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()

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
    """Display and edit the logged-in user's profile."""

    user = request.user
    # Ensure we always have a profile so postcode input always appears.
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"confirmation_token": get_random_string(32)},
    )

    tab = request.GET.get("tab", "profile")

    # Handle form submissions. Multiple forms POST to this view so we
    # inspect the submitted fields rather than rely on separate URLs.
    if request.method == "POST":
        if "preferred_font" in request.POST:
            # Persist the selected font for the current user.
            profile.preferred_font = request.POST.get("preferred_font") or "Cairo"
            profile.save()
            tab = "custom"
            messages.success(request, "Preferences saved.")
            log_activity(
                request,
                activity="profile_preference",
                log_type="user",
                action=profile.preferred_font,
                response="saved",
            )
        elif user.is_superuser and "tier" in request.POST:
            # Allow superusers to switch tier for testing purposes.
            tier = TrustTier.objects.filter(id=request.POST.get("tier")).first()
            if tier:
                profile.tier = tier
                profile.save()
                messages.success(request, f"Tier changed to {tier.name}.")
                log_activity(
                    request,
                    activity="profile_tier",
                    log_type="user",
                    action=str(tier.id),
                    response="saved",
                )
            tab = "custom"
        elif "visibility" in request.POST:
            profile.visibility = request.POST.get("visibility", profile.visibility)
            profile.save()
            messages.success(request, "Visibility updated.")
            log_activity(
                request,
                activity="profile_visibility",
                log_type="user",
                action=profile.visibility,
                response="saved",
            )
        elif "change_details" in request.POST:
            token = get_random_string(32)
            PendingProfileChange.objects.create(
                user=user,
                token=token,
                new_first_name=request.POST.get("first_name", ""),
                new_last_name=request.POST.get("last_name", ""),
                new_email=request.POST.get("email", ""),
                new_password=(
                    make_password(request.POST.get("password1", ""))
                    if request.POST.get("password1")
                    else ""
                ),
            )
            confirm_link = request.build_absolute_uri(
                reverse("confirm_profile_change", args=[token])
            )
            send_email(
                "Confirm profile change",
                f"Visit the following link to confirm your changes: {confirm_link}",
                user.email,
            )
            messages.info(request, "Check your email to confirm profile changes.")
            log_activity(
                request,
                activity="profile_change",
                log_type="user",
                action="details",
                response="email_sent",
            )
        elif "update_extra" in request.POST:
            form = ProfileExtraForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile details saved.")
                log_activity(
                    request,
                    activity="profile_extra",
                    log_type="user",
                    action="extra",
                    response="saved",
                )

    # List of accounts following the current user
    followers = UserFollow.objects.filter(target=user).select_related("follower")
    # Compute a gravatar URL based on the user's email.
    email = (user.email or "").strip().lower()
    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest() if email else ""
    gravatar_url = (
        f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"
        if email_hash
        else None
    )
    tiers = TrustTier.objects.all()
    fonts = ["Cairo", "Roboto", "Lato", "Open Sans"]
    context = {
        "user": user,
        "profile": profile,
        "gravatar_url": gravatar_url,
        "followers": followers,
        "visibility_choices": UserProfile.VISIBILITY_CHOICES,
        "councils": Council.objects.all(),
        "tab": tab,
        "tiers": tiers,
        "fonts": fonts,
    }
    return render(request, "registration/profile.html", context)


@login_required
def notifications_page(request):
    """Display all notifications for the current user."""
    notifications = request.user.notifications.order_by("-created")
    return render(
        request,
        "registration/notifications.html",
        {"notifications": notifications, "tab": "notifications"},
    )


@login_required
def dismiss_notification(request, notification_id):
    """Mark a notification as read then redirect back."""
    note = get_object_or_404(request.user.notifications, id=notification_id)
    note.read = True
    note.save()
    return redirect(request.META.get("HTTP_REFERER", "notifications"))


def signup_view(request):
    """Allow visitors to create an account with a required postcode."""

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Create the user and log them in immediately
            user = form.save()
            login(request, user)
            # Send the initial confirmation email
            send_confirmation_email(user.profile, request)
            messages.info(request, "Check your inbox to confirm your email.")
            return redirect("profile")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def update_postcode(request):
    """Handle AJAX requests to update the user's postcode."""

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    postcode = request.POST.get("postcode", "").strip()
    # If the user ticks the refusal box we'll store that instead of a postcode
    refused = request.POST.get("refused") == "1"
    if not postcode and not refused:
        return JsonResponse({"error": "Postcode required"}, status=400)

    # Ensure the user has a profile; create one if missing.
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"confirmation_token": get_random_string(32)},
    )
    if refused:
        profile.postcode = ""
        profile.postcode_refused = True
    else:
        profile.postcode = postcode
        profile.postcode_refused = False
    profile.save()
    return JsonResponse(
        {"postcode": profile.postcode, "refused": profile.postcode_refused}
    )


@login_required
def resend_confirmation(request):
    """Send another confirmation email to the logged-in user."""

    # Gracefully handle users who were created before profiles existed.
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"confirmation_token": get_random_string(32)},
    )
    try:
        send_confirmation_email(profile, request)
        messages.info(request, "Confirmation email sent.")
    except ApiException as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Brevo API error: {e}")
        error_msg = "There was a problem sending the confirmation email. Please try again later."
        if hasattr(e, "body") and isinstance(e.body, str):
            import json

            try:
                body = json.loads(e.body)
                if "message" in body:
                    error_msg = f"Email not sent: {body['message']}"
            except Exception:
                pass
        messages.error(request, error_msg)
    return redirect("profile")


def confirm_email(request, token):
    """Mark a user's email address as confirmed using the provided token."""

    try:
        profile = UserProfile.objects.get(confirmation_token=token)
    except UserProfile.DoesNotExist:
        raise Http404("Invalid confirmation link")

    profile.email_confirmed = True
    profile.confirmation_token = ""
    profile.save()
    # Log the confirmation event so the user has a record of it.
    create_notification(profile.user, "Your email address has been confirmed.")
    messages.success(request, "Email confirmed. Thank you!")
    return redirect("profile")


def confirm_profile_change(request, token):
    """Apply pending profile updates once the token is visited."""

    change = get_object_or_404(PendingProfileChange, token=token)
    user = change.user
    if change.new_first_name:
        user.first_name = change.new_first_name
    if change.new_last_name:
        user.last_name = change.new_last_name
    if change.new_email:
        user.email = change.new_email
    if change.new_password:
        user.password = change.new_password
    user.save()
    create_notification(user, "Your profile changes have been applied.")
    change.delete()
    messages.success(request, "Profile updated.")
    return redirect("profile")


@login_required
def add_favourite(request):
    """AJAX endpoint to add a council to favourites."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    slug = request.POST.get("council")
    try:
        council = Council.objects.get(slug=slug)
        request.user.profile.favourites.add(council)
        log_activity(
            request,
            council=council,
            activity="favourite",
            log_type="user",
            action=f"slug={slug}",
            response="ok",
        )
        return JsonResponse({"status": "ok"})
    except Council.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=400)


@login_required
def follow_council(request, slug):
    """AJAX endpoint to follow a council for updates."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    try:
        council = Council.objects.get(slug=slug)
        from .models import CouncilFollow

        CouncilFollow.objects.get_or_create(user=request.user, council=council)
        return JsonResponse({"status": "ok"})
    except Council.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=400)


@login_required
def unfollow_council(request, slug):
    """AJAX endpoint to unfollow a council."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    try:
        council = Council.objects.get(slug=slug)
        from .models import CouncilFollow

        CouncilFollow.objects.filter(user=request.user, council=council).delete()
        return JsonResponse({"status": "ok"})
    except Council.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=400)


@login_required
def remove_favourite(request):
    """AJAX endpoint to remove a council from favourites."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    slug = request.POST.get("council")
    try:
        council = Council.objects.get(slug=slug)
        request.user.profile.favourites.remove(council)
        log_activity(
            request,
            council=council,
            activity="favourite",
            log_type="user",
            action=f"slug={slug}",
            response="ok",
        )
        return JsonResponse({"status": "ok"})
    except Council.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=400)


@login_required
def add_to_list(request, list_id):
    """AJAX endpoint to add a council to a user list."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    slug = request.POST.get("council")
    try:
        council = Council.objects.get(slug=slug)
        target = request.user.council_lists.get(id=list_id)
        target.councils.add(council)
        log_activity(
            request,
            council=council,
            activity="list_add",
            log_type="user",
            action=f"list={list_id}",
            response="ok",
        )
        return JsonResponse({"status": "ok"})
    except (Council.DoesNotExist, CouncilList.DoesNotExist):
        return JsonResponse({"error": "invalid"}, status=400)


@login_required
def remove_from_list(request, list_id):
    """AJAX endpoint to remove a council from a user list."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    slug = request.POST.get("council")
    try:
        council = Council.objects.get(slug=slug)
        target = request.user.council_lists.get(id=list_id)
        target.councils.remove(council)
        log_activity(
            request,
            council=council,
            activity="list_remove",
            log_type="user",
            action=f"list={list_id}",
            response="ok",
        )
        return JsonResponse({"status": "ok"})
    except (Council.DoesNotExist, CouncilList.DoesNotExist):
        return JsonResponse({"error": "invalid"}, status=400)


@login_required
def move_between_lists(request):
    """Handle drag-and-drop moves of councils between lists."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    slug = request.POST.get("council")
    from_id = request.POST.get("from")
    to_id = request.POST.get("to")
    try:
        council = Council.objects.get(slug=slug)
        if from_id:
            request.user.council_lists.get(id=from_id).councils.remove(council)
        if to_id:
            request.user.council_lists.get(id=to_id).councils.add(council)
        log_activity(
            request,
            council=council,
            activity="list_move",
            log_type="user",
            action=f"from={from_id}&to={to_id}",
            response="ok",
        )
        return JsonResponse({"status": "ok"})
    except (Council.DoesNotExist, CouncilList.DoesNotExist):
        return JsonResponse({"error": "invalid"}, status=400)


@login_required
def like_update(request, update_id):
    """Toggle a like on a council update."""
    from .models import CouncilUpdate, CouncilUpdateLike

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    update = CouncilUpdate.objects.filter(id=update_id).first()
    if not update:
        return JsonResponse({"error": "not found"}, status=400)
    like, created = CouncilUpdateLike.objects.get_or_create(
        update=update, user=request.user
    )
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({"status": "ok", "liked": liked, "count": update.likes.count()})


@login_required
def comment_update(request, update_id):
    """Add a comment to a council update."""
    from .models import CouncilUpdate, CouncilUpdateComment

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    update = CouncilUpdate.objects.filter(id=update_id).first()
    if not update:
        return JsonResponse({"error": "not found"}, status=400)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "empty"}, status=400)
    CouncilUpdateComment.objects.create(update=update, user=request.user, text=text)
    return JsonResponse({"status": "ok"})


@require_GET
def generate_share_link(request, slug):
    """Return a signed URL capturing counter and display settings."""
    council = get_object_or_404(Council, slug=slug)
    data = {
        "year": request.GET.get("year"),
        "counters": request.GET.get("counters", "").split(",") if request.GET.get("counters") else [],
        "precision": request.GET.get("precision"),
        "thousands": request.GET.get("thousands") == "true",
        "friendly": request.GET.get("friendly") == "true",
    }
    token = signing.dumps(data)
    base = request.build_absolute_uri(reverse("council_detail", args=[council.slug]))
    return JsonResponse({"url": f"{base}?share={token}"})


@login_required
def submit_contribution(request):
    """Accept a contribution for a specific field.

    The endpoint is triggered via AJAX from the council detail page.
    Tier 3 users and above can bypass moderation; everyone else will
    see their submission placed into a queue for review.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    council = get_object_or_404(Council, slug=request.POST.get("council"))

    # Capture form values before any validation so we can log them in case the
    # field slug is invalid. This helps troubleshooting mysterious submissions.
    field_slug = request.POST.get("field")
    year_id = request.POST.get("year")
    year = FinancialYear.objects.filter(id=year_id).first() if year_id else None
    value = request.POST.get("value", "").strip()

    # Determine client IP for logging and blocking.
    # When Django is configured to respect proxy headers we trust the first
    # address in ``HTTP_X_FORWARDED_FOR``.  This header should only be
    # accepted from a properly configured chain of trusted proxies.  In
    # environments without a proxy (or when ``USE_X_FORWARDED_HOST`` is
    # False) we fall back to ``REMOTE_ADDR`` to avoid spoofing.
    if settings.USE_X_FORWARDED_HOST:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else None
    else:
        forwarded_for = None
        ip = None

    if not ip:
        ip = request.META.get("REMOTE_ADDR")
    if BlockedIP.objects.filter(ip_address=ip).exists():
        return JsonResponse({"error": "blocked"}, status=403)

    # Gracefully handle an invalid field slug. Instead of returning a 404 we
    # log the details and send a JSON error so the UI can show a friendly
    # message.
    try:
        field = DataField.objects.get(slug=field_slug)
        # Characteristic values are not tied to a particular financial year so
        # ignore any ``year`` parameter provided in the request.
        if field.category == "characteristic":
            year = None
    except DataField.DoesNotExist:
        from .models import RejectionLog

        RejectionLog.objects.create(
            council=council,
            field=None,
            year=year,
            value=f"{field_slug}: {value}",
            ip_address=ip,
            reason="invalid_field",
        )
        return JsonResponse(
            {
                "error": "invalid_field",
                "message": "The submitted field was not recognised.",
            },
            status=400,
        )

    profile = request.user.profile
    # Council characteristics are always auto-approved so they appear
    # immediately on the site.  Financial figures still respect the
    # normal auto-approval thresholds based on trust tier and history.
    if field.category == "characteristic":
        status = "approved"
    else:
        status = "approved"
        if profile.tier.level < 3:
            min_ips = int(
                SiteSetting.get(
                    "auto_approve_min_verified_ips",
                    settings.AUTO_APPROVE_MIN_VERIFIED_IPS,
                )
            )
            min_approved = int(
                SiteSetting.get(
                    "auto_approve_min_approved",
                    settings.AUTO_APPROVE_MIN_APPROVED,
                )
            )
            if not (
                profile.email_confirmed
                and profile.verified_ip_count >= min_ips
                and profile.approved_submission_count >= min_approved
            ):
                status = "pending"

    contrib = Contribution.objects.create(
        user=request.user,
        council=council,
        field=field,
        year=year,
        value=value,
        status=status,
        ip_address=ip,
    )
    log_activity(
        request,
        council=council,
        activity="submit_contribution",
        log_type="user",
        action=f"field={field.slug}&year={year.id if year else ''}",
        response=status,
        extra={"value": value},
    )
    if status == "approved":
        # Immediately apply the change so followers see the update straight away.
        try:
            _apply_contribution(contrib, request.user, request)
        except Exception as exc:  # Defensive: avoid 500s during auto-apply
            logger.exception("Failed to apply contribution %s", contrib.id)
            status = "pending"
            contrib.status = "pending"
            contrib.save(update_fields=["status"])
        else:
            from .models import CouncilUpdate
            try:
                CouncilUpdate.objects.create(
                    council=council,
                    message=f"{request.user.username} updated {field.name}",
                )
            except Exception:
                logger.exception("Failed to create CouncilUpdate")
        msg = "Contribution accepted" if status == "approved" else "Contribution queued for approval"
    else:
        msg = "Contribution queued for approval"

    # Award a single point for the submission unless the user recently
    # updated the same field and year. This discourages gaming the system
    # by repeatedly submitting tiny edits.
    from datetime import timedelta
    from django.utils import timezone

    window = timezone.now() - timedelta(weeks=3)
    recent = Contribution.objects.filter(
        user=request.user,
        council=council,
        field=field,
        year=year,
        created__gte=window,
    ).exclude(pk=contrib.pk)
    if not recent.exists():
        # Award extra points for characteristic data because it improves the
        # overall quality of the site for all future years.
        award = 10 if field.category == "characteristic" else 1
        profile.points += award
        profile.save()
        link = reverse("council_detail", args=[council.slug])
        create_notification(
            request.user,
            f"Thanks for submitting a figure for <a href='{link}'>{council.name}</a>. You earned {award} point{'s' if award != 1 else ''}.",
        )

    # Create an in-app notification so the user can see a record of their
    # submission. This helps provide immediate feedback even after redirect.
    create_notification(request.user, f"{msg} for {council.name}")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": status, "message": msg, "value": field.display_value(value)})

    messages.info(request, msg)
    return redirect("council_detail", council.slug)


@login_required
def review_contribution(request, pk, action):
    """Approve, reject or edit a pending contribution.

    Superusers are allowed to moderate contributions even if their profile
    tier is below the normal moderator threshold (level 3).
    """
    contrib = get_object_or_404(Contribution, pk=pk)

    # Enforce the tier requirement unless the user is a superuser. This mirrors
    # the logic used on the contribution page when rendering moderation buttons.
    if not request.user.is_superuser and request.user.profile.tier.level < 3:
        return HttpResponseBadRequest("permission denied")

    if action == "approve" and request.method == "POST":
        try:
            _apply_contribution_v2(contrib, request.user, request)
            contrib.status = "approved"
            contrib.save()
            
            log_activity(
                request,
                council=contrib.council,
                activity="review_contribution",
                log_type="user",
                action=f"id={pk}",
                response="approved",
                extra={"value": contrib.value},
            )
            
            # Reward characteristic data a bit more to encourage its collection.
            points = 3 if contrib.field.category == "characteristic" else 2
            profile = contrib.user.profile
            profile.points += points
            profile.save()
            
            # Build a notification that references the council and field, links to
            # the council detail page and explains the point reward.
            link = reverse("council_detail", args=[contrib.council.slug])
            message = (
                f"Your contribution to <a href='{link}'>{contrib.council.name}</a> "
                f"(Field: {contrib.field.name}) was accepted. You also earned {points} "
                f"points for this. Thank you!"
            )
            create_notification(contrib.user, message)
            
            messages.success(request, f"Contribution approved successfully!")
            
        except Exception as e:
            logger.error(f"Error approving contribution {pk}: {str(e)}", exc_info=True)
            messages.error(request, f"Error approving contribution: {str(e)}")
            return redirect('contribute')
    elif action == "reject" and request.method == "POST":
        reason = request.POST.get("reason")
        if not reason:
            return HttpResponseBadRequest("reason required")
        contrib.status = "rejected"
        contrib.save()
        log_activity(
            request,
            council=contrib.council,
            activity="review_contribution",
            log_type="user",
            action=f"id={pk}",
            response="rejected",
            extra={"reason": reason, "value": contrib.value},
        )
        from .models import RejectionLog

        RejectionLog.objects.create(
            contribution=contrib,
            council=contrib.council,
            field=contrib.field,
            year=contrib.year,
            value=contrib.value,
            ip_address=contrib.ip_address,
            reason=reason,
            reviewed_by=request.user,
        )
        profile = contrib.user.profile
        profile.rejection_count += 1
        profile.save()
        create_notification(
            contrib.user,
            "Your contribution was rejected",
        )
    elif action == "edit" and request.method == "POST":
        contrib.value = request.POST.get("value", contrib.value)
        contrib.edited = True
        contrib.save()
        create_notification(
            contrib.user,
            "Your contribution was edited by a moderator",
        )
        log_activity(
            request,
            council=contrib.council,
            activity="review_contribution",
            log_type="user",
            action=f"id={pk}",
            response="edited",
            extra={"value": contrib.value},
        )
        return redirect("contribute")
    elif action == "delete" and request.method == "POST":
        # Only God Mode (tier 5) or superusers should remove contributions.
        if not request.user.is_superuser and request.user.profile.tier.level < 5:
            return HttpResponseBadRequest("permission denied")
        contrib.delete()
        log_activity(
            request,
            council=contrib.council,
            activity="review_contribution",
            log_type="user",
            action=f"id={pk}",
            response="deleted",
        )
        create_notification(
            contrib.user,
            "A moderator removed your contribution from the queue",
        )
        return redirect("contribute")
    return redirect("contribute")


def _apply_contribution(contribution, user, request=None):
    """Persist an approved contribution and log the change."""
    field = contribution.field
    council = contribution.council

    # Debug logging so the activity log shows each step of the process. This
    # helps diagnose issues when a contribution does not appear to apply
    # correctly from the UI.
    if request:
        log_activity(
            request,
            council=council,
            activity="apply_contribution",
            log_type="debug",
            action=f"start field={field.slug}",
            extra={"value": contribution.value},
        )

    old_value = contribution.old_value

    if field.slug == "council_website":
        council.website = contribution.value
        council.save()
        if request:
            log_activity(
                request,
                council=council,
                activity="apply_contribution",
                log_type="debug",
                action="set website",
                extra={"new": contribution.value},
            )
    elif field.slug == "council_type":
        council.council_type_id = contribution.value or None
        council.save()
        if request:
            log_activity(
                request,
                council=council,
                activity="apply_contribution",
                log_type="debug",
                action="set type",
                extra={"new": contribution.value},
            )
    elif field.slug == "council_nation":
        council.council_nation_id = contribution.value or None
        council.save()
        if request:
            log_activity(
                request,
                council=council,
                activity="apply_contribution",
                log_type="debug",
                action="set nation",
                extra={"new": contribution.value},
            )
    else:
        FigureSubmission.objects.update_or_create(
            council=council,
            field=field,
            year=contribution.year,
            defaults={"value": contribution.value, "needs_populating": False},
        )

    DataChangeLog.objects.create(
        contribution=contribution,
        council=council,
        field=field,
        year=contribution.year,
        old_value=old_value,
        new_value=contribution.value,
        approved_by=user,
    )
    # Clear any outstanding data issues now that the figure is populated.
    from .models import DataIssue
    DataIssue.objects.filter(
        council=council,
        field=field,
        year=contribution.year,
    ).delete()
    if request:
        log_activity(
            request,
            council=council,
            activity="apply_contribution",
            log_type="debug",
            action="clear issues",
        )
    if request:
        log_activity(
            request,
            council=council,
            activity="apply_contribution",
            log_type="debug",
            action="record change",
            extra={"old": old_value, "new": contribution.value},
        )

    # Update contributor stats once a change is successfully recorded. The
    # ``approved_submission_count`` tracks how many edits moderators have
    # accepted. ``verified_ip_count`` increments when a new IP address is
    # associated with an approved contribution.
    profile = contribution.user.profile
    from .models import VerifiedIP

    if contribution.ip_address:
        _, created = VerifiedIP.objects.get_or_create(
            user=contribution.user, ip_address=contribution.ip_address
        )
        if created:
            profile.verified_ip_count += 1
    profile.approved_submission_count += 1
    profile.save()
    if request:
        log_activity(
            request,
            council=council,
            activity="apply_contribution",
            log_type="debug",
            action="update profile",
            extra={
                "verified": profile.verified_ip_count,
                "approved": profile.approved_submission_count,
            },
        )

    log_activity(
        request,
        council=council,
        activity="apply_contribution",
        log_type="user" if user == contribution.user else "moderator",
        action=f"field={field.slug}&year={contribution.year_id}",
        response="applied",
        extra={"old": old_value, "new": contribution.value},
    )


def _apply_contribution_v2(contribution, user, request=None):
    """
    Apply a contribution using the new data architecture.
    This replaces the problematic _apply_contribution function.
    """
    from django.db import transaction
    from django.utils import timezone
    
    # Check if new models are available
    if not NEW_DATA_MODEL_AVAILABLE:
        # Fall back to old system with better error handling
        try:
            return _apply_contribution(contribution, user, request)
        except Exception as e:
            logger.error(f"Error in legacy _apply_contribution: {str(e)}")
            # For characteristic fields that fail with year_id constraint,
            # skip the FigureSubmission creation
            if "year_id" in str(e) and contribution.field.category == 'characteristic':
                logger.info(f"Skipping FigureSubmission creation for characteristic field: {contribution.field.slug}")
                return
            raise
    
    # Use new data architecture
    try:
        with transaction.atomic():
            # Determine if this is a characteristic or financial figure
            is_characteristic = contribution.field.category == 'characteristic'
            
            if is_characteristic:
                # Update or create council characteristic
                characteristic, created = CouncilCharacteristic.objects.get_or_create(
                    council=contribution.council,
                    field=contribution.field,
                    defaults={
                        'value': contribution.value,
                        'updated_by': user
                    }
                )
                
                if not created:
                    # Store history before updating
                    CouncilCharacteristicHistory.objects.create(
                        council=contribution.council,
                        field=contribution.field,
                        old_value=characteristic.value,
                        new_value=contribution.value,
                        changed_by=user,
                        changed_at=timezone.now(),
                        source='contribution'
                    )
                    
                    # Update the characteristic
                    characteristic.value = contribution.value
                    characteristic.updated_by = user
                    characteristic.save()
                
                logger.info(f"Applied characteristic contribution: {contribution.council.name} - {contribution.field.name} = {contribution.value}")
                
            else:
                # For financial figures, we need a year
                year = getattr(contribution, 'year', None)
                if not year:
                    # Try to get the current financial year or create one
                    year = FinancialYear.objects.filter(is_current=True).first()
                    if not year:
                        year = FinancialYear.objects.first()
                
                if year:
                    # Update or create financial figure
                    figure, created = FinancialFigure.objects.get_or_create(
                        council=contribution.council,
                        field=contribution.field,
                        year=year,
                        defaults={
                            'value': contribution.value,
                            'updated_by': user
                        }
                    )
                    
                    if not created:
                        # Store history before updating
                        FinancialFigureHistory.objects.create(
                            council=contribution.council,
                            field=contribution.field,
                            year=year,
                            old_value=figure.value,
                            new_value=contribution.value,
                            changed_by=user,
                            changed_at=timezone.now(),
                            source='contribution'
                        )
                        
                        # Update the figure
                        figure.value = contribution.value
                        figure.updated_by = user
                        figure.save()
                    
                    logger.info(f"Applied financial contribution: {contribution.council.name} - {contribution.field.name} ({year.label}) = {contribution.value}")
                else:
                    logger.warning(f"No financial year available for contribution: {contribution.id}")
                    
    except Exception as e:
        logger.error(f"Error in _apply_contribution_v2: {str(e)}", exc_info=True)
        raise


# Temporary stub functions for missing views - to be implemented later
def user_preferences_view(request):
    """Temporary stub for user preferences view."""
    from django.http import HttpResponse
    return HttpResponse("User preferences feature coming soon")

def user_preferences_ajax(request):
    """Temporary stub for user preferences AJAX view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def council_counters(request, slug):
    """Temporary stub for council counters view."""
    from django.http import HttpResponse
    return HttpResponse("Council counters feature coming soon")

def edit_figures_table(request, slug):
    """Temporary stub for edit figures table view."""
    from django.http import HttpResponse
    return HttpResponse("Edit figures table feature coming soon")

def council_change_log(request, slug):
    """Temporary stub for council change log view.""" 
    from django.http import HttpResponse
    return HttpResponse("Council change log feature coming soon")

def leaderboards(request):
    """Display contribution leaderboards"""
    from .models import UserProfile
    
    # Get top contributors by points
    top_contributors = UserProfile.objects.filter(
        points__gt=0
    ).order_by('-points')[:20]
    
    context = {
        'top_contributors': top_contributors,
        'title': 'Leaderboards'
    }
    
    return render(request, 'council_finance/leaderboards.html', context)

def my_lists(request):
    """User's custom lists of councils"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # For now, show a basic page indicating the feature is being restored
    context = {
        'user': request.user,
        'title': 'My Lists'
    }
    
    return render(request, 'council_finance/my_lists.html', context)

def add_favourite(request):
    """Temporary stub for add favourite view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def remove_favourite(request):
    """Temporary stub for remove favourite view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def add_to_list(request, list_id):
    """Temporary stub for add to list view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def remove_from_list(request, list_id):
    """Temporary stub for remove from list view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def move_between_lists(request):
    """Temporary stub for move between lists view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def list_metric(request, list_id):
    """Temporary stub for list metric view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def add_to_compare(request, slug):
    """Temporary stub for add to compare view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def remove_from_compare(request, slug):
    """Temporary stub for remove from compare view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def compare_row(request):
    """Temporary stub for compare row view."""
    from django.http import HttpResponse
    return HttpResponse("Compare row feature coming soon")

def compare_basket(request):
    """Temporary stub for compare basket view."""
    from django.http import HttpResponse
    return HttpResponse("Compare basket feature coming soon")

def following(request):
    """Temporary stub for following view."""
    from django.http import HttpResponse
    return HttpResponse("Following feature coming soon")

def follow_council(request, slug):
    """Temporary stub for follow council view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def unfollow_council(request, slug):
    """Temporary stub for unfollow council view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def like_update(request, update_id):
    """Temporary stub for like update view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def comment_update(request, update_id):
    """Temporary stub for comment update view."""
    from django.http import JsonResponse
    return JsonResponse({"status": "not implemented"})

def my_profile(request):
    """User profile page - redirect to profile_view"""
    return profile_view(request)

def about(request):
    """Temporary stub for about view."""
    from django.http import HttpResponse
    return HttpResponse("About page coming soon")

def terms_of_use(request):
    """Temporary stub for terms of use view."""
    from django.http import HttpResponse
    return HttpResponse("Terms of use page coming soon")

def privacy_cookies(request):
    """Temporary stub for privacy cookies view."""
    from django.http import HttpResponse
    return HttpResponse("Privacy & cookies page coming soon")

def corrections(request):
    """Temporary stub for corrections view."""
    from django.http import HttpResponse
    return HttpResponse("Corrections page coming soon")

def site_counter_list(request):
    """Temporary stub for site counter list view."""
    from django.http import HttpResponse
    return HttpResponse("Site counter list feature coming soon")

def field_list(request):
    """Enhanced Fields & Characteristics management interface"""
    from django.contrib.auth.decorators import login_required
    from django.db.models import Q, Count
    from django.core.paginator import Paginator
    from .models import DataField, CouncilType, FigureSubmission, DataIssue
    from .models.field import CHARACTERISTIC_SLUGS
    
    # Require authentication and appropriate permissions
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Allow tier 3+ users or superusers to manage fields
    if not request.user.is_superuser and request.user.profile.tier.level < 3:
        messages.error(request, "You need tier 3+ access to manage fields and characteristics.")
        return redirect('home')
    
    # Handle search and filtering
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    content_type_filter = request.GET.get('content_type', '')
    status_filter = request.GET.get('status', 'all')  # all, protected, user_created
    
    # Base queryset with related data for efficiency
    queryset = DataField.objects.select_related().prefetch_related(
        'council_types'
    ).annotate(
        usage_count=Count('figuresubmission'),
        issue_count=Count('dataissue')
    )
    
    # Apply filters
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | 
            Q(explanation__icontains=search) |
            Q(slug__icontains=search)
        )
    
    if category_filter:
        queryset = queryset.filter(category=category_filter)
    
    if content_type_filter:
        queryset = queryset.filter(content_type=content_type_filter)
    
    if status_filter == 'protected':
        queryset = queryset.filter(slug__in=CHARACTERISTIC_SLUGS)
    elif status_filter == 'user_created':
        queryset = queryset.exclude(slug__in=CHARACTERISTIC_SLUGS)
    
    # Order by category, then by name for logical grouping
    queryset = queryset.order_by('category', 'name')
    
    # Paginate results
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options for the form
    categories = DataField.FIELD_CATEGORIES
    content_types = DataField.CONTENT_TYPES
    
    # Group fields by category for tabbed display
    fields_by_category = {}
    for field in queryset:
        if field.category not in fields_by_category:
            fields_by_category[field.category] = []
        fields_by_category[field.category].append(field)
    
    # Statistics for dashboard
    stats = {
        'total_fields': DataField.objects.count(),
        'characteristic_fields': DataField.objects.filter(category='characteristic').count(),
        'financial_fields': DataField.objects.exclude(category='characteristic').count(),
        'protected_fields': DataField.objects.filter(slug__in=CHARACTERISTIC_SLUGS).count(),
        'user_created_fields': DataField.objects.exclude(slug__in=CHARACTERISTIC_SLUGS).count(),
        'fields_with_issues': DataField.objects.filter(dataissue__isnull=False).distinct().count(),
    }
    
    context = {
        'fields': page_obj,
        'fields_by_category': fields_by_category,
        'search': search,
        'category_filter': category_filter,
        'content_type_filter': content_type_filter,
        'status_filter': status_filter,
        'categories': categories,
        'content_types': content_types,
        'stats': stats,
        'characteristic_slugs': CHARACTERISTIC_SLUGS,
        'title': 'Fields & Characteristics Manager'
    }
    
    return render(request, 'council_finance/field_list.html', context)

def field_form(request, slug=None):
    """Enhanced field creation and editing form with moderation support"""
    from django.contrib.auth.decorators import login_required
    from django.db import transaction
    from .models import DataField, ActivityLog
    from .forms import DataFieldForm
    from .models.field import CHARACTERISTIC_SLUGS
    
    # Require authentication and appropriate permissions
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Allow tier 3+ users or superusers to manage fields
    if not request.user.is_superuser and request.user.profile.tier.level < 3:
        messages.error(request, "You need tier 3+ access to manage fields and characteristics.")
        return redirect('field_list')
    
    # Determine if we're editing or creating
    field = None
    is_edit = slug is not None
    
    if is_edit:
        try:
            field = DataField.objects.get(slug=slug)
        except DataField.DoesNotExist:
            messages.error(request, "Field not found.")
            return redirect('field_list')
    
    if request.method == 'POST':
        form = DataFieldForm(request.POST, instance=field)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the field
                    field = form.save()
                    
                    # Log the activity
                    activity_type = 'update' if is_edit else 'create'
                    description = f"{'Updated' if is_edit else 'Created'} field: {field.name}"
                    
                    ActivityLog.log_activity(
                        activity_type=activity_type,
                        description=description,
                        user=request.user,
                        content_object=field,
                        details={
                            'field_slug': field.slug,
                            'field_name': field.name,
                            'category': field.category,
                            'content_type': field.content_type,
                            'is_protected': field.is_protected,
                        },
                        request=request
                    )
                    
                    # Show success message
                    action = 'updated' if is_edit else 'created'
                    messages.success(request, f"Field '{field.name}' has been {action} successfully.")
                    
                    # Redirect based on user action
                    if 'save_and_continue' in request.POST:
                        return redirect('field_edit', slug=field.slug)
                    elif 'save_and_add_another' in request.POST:
                        return redirect('field_add')
                    else:
                        return redirect('field_list')
                        
            except Exception as e:
                messages.error(request, f"Error saving field: {str(e)}")
    else:
        form = DataFieldForm(instance=field)
    
    # Additional context for the template
    context = {
        'form': form,
        'field': field,
        'is_edit': is_edit,
        'is_protected': field.is_protected if field else False,
        'characteristic_slugs': CHARACTERISTIC_SLUGS,
        'title': f"{'Edit' if is_edit else 'Add'} Field"
    }
    
    return render(request, 'council_finance/field_form.html', context)

def field_delete(request, slug):
    """Enhanced field deletion with safety checks and audit logging"""
    from django.contrib.auth.decorators import login_required
    from django.db import transaction
    from .models import DataField, ActivityLog, FigureSubmission
    from .models.field import CHARACTERISTIC_SLUGS
    
    # Require authentication and appropriate permissions
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Allow tier 4+ users or superusers to delete fields (higher threshold)
    if not request.user.is_superuser and request.user.profile.tier.level < 4:
        messages.error(request, "You need tier 4+ access to delete fields.")
        return redirect('field_list')
    
    try:
        field = DataField.objects.get(slug=slug)
    except DataField.DoesNotExist:
        messages.error(request, "Field not found.")
        return redirect('field_list')
    
    # Check if field is protected
    if field.is_protected:
        messages.error(request, f"Cannot delete '{field.name}' - this is a protected system field.")
        return redirect('field_list')
    
    # Check if field has data
    usage_count = FigureSubmission.objects.filter(field=field).count()
    
    if request.method == 'POST':
        if 'confirm_delete' in request.POST:
            try:
                with transaction.atomic():
                    field_name = field.name
                    field_slug = field.slug
                    
                    # Log the deletion before actually deleting
                    ActivityLog.log_activity(
                        activity_type='delete',
                        description=f"Deleted field: {field_name}",
                        user=request.user,
                        details={
                            'field_slug': field_slug,
                            'field_name': field_name,
                            'category': field.category,
                            'content_type': field.content_type,
                            'usage_count': usage_count,
                            'deletion_reason': request.POST.get('deletion_reason', ''),
                        },
                        request=request
                    )
                    
                    # Delete the field
                    field.delete()
                    
                    messages.success(request, f"Field '{field_name}' has been deleted successfully.")
                    return redirect('field_list')
                    
            except Exception as e:
                messages.error(request, f"Error deleting field: {str(e)}")
        else:
            messages.info(request, "Deletion cancelled.")
            return redirect('field_list')
    
    context = {
        'field': field,
        'usage_count': usage_count,
        'title': f"Delete Field: {field.name}"
    }
    
    return render(request, 'council_finance/field_delete.html', context)

def factoid_list(request):
    """List all factoids"""
    from django.http import HttpResponse
    return HttpResponse("Factoid List - Not implemented yet")

def factoid_form(request, slug=None):
    """Add or edit factoid form"""
    from django.http import HttpResponse
    return HttpResponse("Factoid Form - Not implemented yet")

def preview_factoid(request):
    """Preview a factoid"""
    from django.http import HttpResponse
    return HttpResponse("Preview Factoid - Not implemented yet")

def factoid_delete(request, slug):
    """Delete a factoid"""
    from django.http import HttpResponse
    return HttpResponse("Factoid Delete - Not implemented yet")

def god_mode(request):
    """Enhanced God Mode dashboard for system administration and data management"""
    # Restrict access to superusers only
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied. Superuser permissions required.")
    
    from django.contrib import messages
    from django.core.management import call_command
    from django.db import transaction
    from django.utils import timezone
    from .models import (
        Council, DataIssue, ActivityLog, UserProfile, 
        Contribution, FigureSubmission, DataField
    )
    from .population import reconcile_populations
    from .data_quality import assess_data_issues
    import time
    
    # Handle POST requests for various God Mode operations
    if request.method == "POST":
        action = None
        start_time = time.time()
        
        if "reconcile_population" in request.POST:
            try:
                with transaction.atomic():
                    count = reconcile_populations()
                    action = "reconcile_population"
                    messages.success(request, f"Population reconciliation completed. Updated {count} councils.")
                    
                    # Log the God Mode activity
                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type="bulk_operation",
                        description=f"Population cache reconciliation completed",
                        details={
                            "operation": "reconcile_population",
                            "councils_updated": count,
                            "execution_time": round(time.time() - start_time, 2)
                        }
                    )
            except Exception as e:
                messages.error(request, f"Population reconciliation failed: {str(e)}")
                
        elif "assess_issues" in request.POST:
            try:
                with transaction.atomic():
                    count = assess_data_issues()
                    action = "assess_issues"
                    messages.success(request, f"Data quality assessment completed. Processed {count} issues.")
                    
                    # Log the God Mode activity
                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type="bulk_operation",
                        description=f"Data quality assessment completed",
                        details={
                            "operation": "assess_issues",
                            "issues_processed": count,
                            "execution_time": round(time.time() - start_time, 2)
                        }
                    )
            except Exception as e:
                messages.error(request, f"Data quality assessment failed: {str(e)}")
                
        elif "clear_stale_data" in request.POST:
            try:
                with transaction.atomic():
                    # Clear old rejected contributions (older than 6 months)
                    from datetime import timedelta
                    cutoff_date = timezone.now() - timedelta(days=180)
                    deleted_count = Contribution.objects.filter(
                        status='rejected',
                        created__lt=cutoff_date
                    ).count()
                    Contribution.objects.filter(
                        status='rejected',
                        created__lt=cutoff_date
                    ).delete()
                    
                    action = "clear_stale_data"
                    messages.success(request, f"Cleared {deleted_count} stale rejected contributions.")
                    
                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type="bulk_operation",
                        description=f"Stale data cleanup completed",
                        details={
                            "operation": "clear_stale_data",
                            "items_deleted": deleted_count,
                            "execution_time": round(time.time() - start_time, 2)
                        }
                    )
            except Exception as e:
                messages.error(request, f"Stale data cleanup failed: {str(e)}")
                
        elif "regenerate_stats" in request.POST:
            try:
                with transaction.atomic():
                    # Recalculate user points and statistics
                    users_updated = 0
                    for profile in UserProfile.objects.all():
                        old_points = profile.points
                        approved_contributions = Contribution.objects.filter(
                            user=profile.user,
                            status='approved'
                        ).count()
                        # Basic point calculation: 1 point per approved contribution
                        profile.points = approved_contributions
                        profile.approved_submission_count = approved_contributions
                        profile.save()
                        users_updated += 1
                    
                    action = "regenerate_stats"
                    messages.success(request, f"Regenerated statistics for {users_updated} users.")
                    
                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type="bulk_operation",
                        description=f"User statistics regeneration completed",
                        details={
                            "operation": "regenerate_stats",
                            "users_updated": users_updated,
                            "execution_time": round(time.time() - start_time, 2)
                        }
                    )
            except Exception as e:
                messages.error(request, f"Statistics regeneration failed: {str(e)}")
                
        elif "add_financial_year" in request.POST:
            try:
                from .year_utils import validate_year_label_format, create_year_with_smart_defaults
                
                new_year_label = request.POST.get('new_year_label', '').strip()
                if not new_year_label:
                    messages.error(request, "Please enter a financial year label.")
                else:
                    # Validate the year format
                    is_valid, error_message = validate_year_label_format(new_year_label)
                    if not is_valid:
                        messages.error(request, f"Invalid year format: {error_message}")
                    else:
                        # Create the year with smart defaults
                        year, created = create_year_with_smart_defaults(
                            label=new_year_label,
                            is_current=False,  # Let users manually set current year if needed
                            user=request.user
                        )
                        
                        if created:
                            messages.success(request, f"✅ Financial year '{new_year_label}' created successfully!")
                            
                            # Log the God Mode activity
                            ActivityLog.objects.create(
                                user=request.user,
                                activity_type="financial_year_creation",
                                description=f"Financial year '{new_year_label}' created via God Mode",
                                details={
                                    "operation": "add_financial_year",
                                    "year_label": new_year_label,
                                    "is_forecast": getattr(year, 'is_forecast', False),
                                    "is_provisional": getattr(year, 'is_provisional', False)
                                }
                            )
                        else:
                            messages.warning(request, f"⚠️ Financial year '{new_year_label}' already exists.")
                            
            except Exception as e:
                messages.error(request, f"Failed to create financial year: {str(e)}")
        
        # Redirect to avoid form resubmission
        return redirect('god_mode')
    
    # Gather dashboard statistics
    stats = {
        'total_councils': Council.objects.count(),
        'active_councils': Council.objects.filter(status='active').count(),
        'total_data_issues': DataIssue.objects.count(),
        'missing_data_issues': DataIssue.objects.filter(issue_type='missing').count(),
        'suspicious_data_issues': DataIssue.objects.filter(issue_type='suspicious').count(),
        'total_users': UserProfile.objects.count(),
        'total_contributions': Contribution.objects.count(),
        'pending_contributions': Contribution.objects.filter(status='pending').count(),
        'approved_contributions': Contribution.objects.filter(status='approved').count(),
        'rejected_contributions': Contribution.objects.filter(status='rejected').count(),
        'total_fields': DataField.objects.count(),
        'characteristic_fields': DataField.objects.filter(category='characteristic').count(),
        'financial_fields': DataField.objects.filter(category='financial').count(),
    }
    
    # Recent God Mode activities
    recent_activities = ActivityLog.objects.filter(
        activity_type='bulk_operation'
    ).order_by('-created')[:10]
    
    # === ENHANCED GOD MODE SURVEILLANCE SYSTEM ===
    # Like Zeus atop Olympus, monitoring all activity across the realm
    
    from datetime import timedelta
    from django.db.models import Count, Q, Avg
    from django.contrib.auth.models import User
    
    # Time windows for surveillance
    now = timezone.now()
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)
    last_week = now - timedelta(days=7)
    last_month = now - timedelta(days=30)
    
    # ==> USER ACTIVITY SURVEILLANCE <=
    user_activity_surveillance = {
        'active_users_24h': User.objects.filter(last_login__gte=last_24h).count(),
        'new_users_24h': User.objects.filter(date_joined__gte=last_24h).count(),
        'contributions_24h': Contribution.objects.filter(created__gte=last_24h).count(),
        'contributions_today': Contribution.objects.filter(created__gte=last_24h).count(),  # Alias for template
        'rejected_contributions_24h': Contribution.objects.filter(
            created__gte=last_24h, status='rejected'
        ).count(),
        'suspicious_activity_count': UserProfile.objects.filter(
            Q(rejection_count__gt=10) | Q(points__lt=0)
        ).count(),
        'top_contributors_today': Contribution.objects.filter(
            created__gte=last_24h, status='approved'
        ).values('user__username').annotate(count=Count('id')).order_by('-count')[:5],
    }
    
    # ==> DATA QUALITY SURVEILLANCE <=
    try:
        total_figures = FigureSubmission.objects.count()
        complete_figures = FigureSubmission.objects.exclude(value__isnull=True).exclude(value__exact='').count()
        completeness_percentage = (complete_figures / max(total_figures, 1)) * 100
    except:
        completeness_percentage = 0
        
    data_quality_surveillance = {
        'missing_data_issues': DataIssue.objects.filter(issue_type='missing').count(),
        'suspicious_data_issues': DataIssue.objects.filter(issue_type='suspicious').count(),
        'councils_incomplete_data': Council.objects.annotate(
            figure_count=Count('figuresubmission')
        ).filter(figure_count__lt=10).count(),
        'completeness_percentage': completeness_percentage,
        'consistency_score': min(100, max(0, completeness_percentage)),  # Simplified consistency score
        'recent_data_changes': ActivityLog.objects.filter(
            activity_type='data_correction',
            created__gte=last_24h
        ).count(),
    }
    
    # ==> SECURITY MONITORING <=
    security_monitoring = {
        'failed_login_attempts_24h': 0,  # Would need login failure tracking
        'blocked_ips': 0,  # Would need IP blocking system  
        'unusual_patterns': ActivityLog.objects.filter(
            created__gte=last_hour
        ).values('user').annotate(count=Count('id')).filter(count__gt=50).count(),
        'bulk_operations_24h': ActivityLog.objects.filter(
            activity_type='bulk_operation',
            created__gte=last_24h
        ).count(),
        'admin_activities_24h': ActivityLog.objects.filter(
            user__is_superuser=True,
            created__gte=last_24h
        ).count(),
    }
    
    # ==> REAL-TIME ALERTS GENERATION <=
    active_alerts = []
    
    # Check for unusual activity patterns
    if user_activity_surveillance['rejected_contributions_24h'] > user_activity_surveillance['contributions_24h'] * 0.3 and user_activity_surveillance['contributions_24h'] > 0:
        active_alerts.append({
            'level': 'warning',
            'message': "High rejection rate detected - may indicate data quality issues",
            'action': 'review_rejection_patterns',
            'timestamp': timezone.now()
        })
    
    # Check for data completeness issues
    if data_quality_surveillance['completeness_percentage'] < 80:
        active_alerts.append({
            'level': 'error',
            'message': f"Data completeness at {data_quality_surveillance['completeness_percentage']:.1f}% - below 80% threshold",
            'action': 'assess_issues',
            'timestamp': timezone.now()
        })
    
    # Check for unusual bulk operations
    if security_monitoring['bulk_operations_24h'] > 10:
        active_alerts.append({
            'level': 'info',
            'message': f"{security_monitoring['bulk_operations_24h']} bulk operations in last 24h - monitoring for anomalies",
            'action': 'review_bulk_operations',
            'timestamp': timezone.now()
        })
    
    # Check for suspicious user behavior
    if user_activity_surveillance['suspicious_activity_count'] > 5:
        active_alerts.append({
            'level': 'warning',
            'message': f"{user_activity_surveillance['suspicious_activity_count']} users flagged for suspicious activity",
            'action': 'review_user_behavior',
            'timestamp': timezone.now()
        })
    
    # ==> SYSTEM HEALTH INDICATORS <=
    health_indicators = []
    
    # Check for councils without population data
    councils_without_population = Council.objects.filter(
        status='active',
        latest_population__isnull=True
    ).count()
    if councils_without_population > 0:
        health_indicators.append({
            'type': 'warning',
            'message': f'{councils_without_population} active councils missing population data',
            'action': 'reconcile_population'
        })
    
    # Check for high number of pending contributions
    pending_count = Contribution.objects.filter(status='pending').count()
    if pending_count > 50:
        health_indicators.append({
            'type': 'warning',
            'message': f'{pending_count} contributions pending review',
            'action': 'review_contributions'
        })
    
    # Check for data quality issues
    critical_issues = DataIssue.objects.filter(issue_type='missing').count()
    if critical_issues > 100:
        health_indicators.append({
            'type': 'error',
            'message': f'{critical_issues} critical data quality issues',
            'action': 'assess_issues'
        })
    
    # Get financial years and other missing context data
    financial_years = FinancialYear.objects.order_by('-label')
    all_councils = Council.objects.all()
    
    # Generate recommended year (next financial year)
    try:
        recommended_year = current_financial_year_label()
        # Check if current year exists, if so suggest next year
        if FinancialYear.objects.filter(label=recommended_year).exists():
            # Extract start year and suggest next year
            start_year = int(recommended_year.split('/')[0])
            next_start = start_year + 1
            next_end = str(next_start + 1)[-2:]
            recommended_year = f"{next_start}/{next_end}"
    except:
        recommended_year = None
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'health_indicators': health_indicators,
        'title': 'God Mode - Zeus Surveillance System',
        # Enhanced God Mode Surveillance
        'user_activity_surveillance': user_activity_surveillance,
        'data_quality_surveillance': data_quality_surveillance,
        'security_monitoring': security_monitoring,
        'active_alerts': active_alerts,
        # Financial Years Management
        'financial_years': financial_years,
        'recommended_year': recommended_year,
        'all_councils': all_councils,
        # Additional data for enhanced surveillance
        'recent_rejections': RejectionLog.objects.select_related('council', 'field', 'reviewed_by').order_by('-created')[:20],
        'recent_users': User.objects.filter(date_joined__gte=last_week).order_by('-date_joined')[:10],
        'high_activity_users': ActivityLog.objects.filter(
            created__gte=last_24h
        ).values('user__username').annotate(
            activity_count=Count('id')
        ).order_by('-activity_count')[:10],
        'council_activity_hotspots': ActivityLog.objects.filter(
            created__gte=last_24h,
            related_council__isnull=False
        ).values('related_council__name').annotate(
            activity_count=Count('id')
        ).order_by('-activity_count')[:10],
    }
    
    return render(request, 'council_finance/god_mode.html', context)

def activity_log_entries(request):
    """Activity log entries"""
    from django.http import HttpResponse
    return HttpResponse("Activity Log Entries - Not implemented yet")

def activity_log_json(request, log_id):
    """Activity log JSON data"""
    from django.http import JsonResponse
    return JsonResponse({"message": "Activity Log JSON - Not implemented yet"})

def mark_issue_invalid(request, issue_id):
    """Mark an issue as invalid"""
    from django.http import HttpResponse
    return HttpResponse("Mark Issue Invalid - Not implemented yet")

def site_counter_form(request, slug=None):
    """Add or edit site counter form"""
    from django.http import HttpResponse
    return HttpResponse("Site Counter Form - Not implemented yet")

def group_counter_list(request):
    """List group counters"""
    from django.http import HttpResponse
    return HttpResponse("Group Counter List - Not implemented yet")

def group_counter_form(request, slug=None):
    """Add or edit group counter form"""
    from django.http import HttpResponse
    return HttpResponse("Group Counter Form - Not implemented yet")

def counter_definition_form(request, slug=None):
    """Add or edit counter definition form"""
    from django.http import HttpResponse
    return HttpResponse("Counter Definition Form - Not implemented yet")

def preview_counter_value(request):
    """Preview counter value"""
    from django.http import HttpResponse
    return HttpResponse("Preview Counter Value - Not implemented yet")

def preview_aggregate_counter(request):
    """Preview aggregate counter"""
    from django.http import HttpResponse
    return HttpResponse("Preview Aggregate Counter - Not implemented yet")

def data_issues_table(request):
    """Return paginated data issues for the contribute page AJAX calls"""
    from django.http import JsonResponse
    from django.core.paginator import Paginator
    from .models import DataIssue
    
    # Check if this is an AJAX request
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    
    # Get parameters
    data_type = request.GET.get('type', 'missing_characteristics')
    page_num = int(request.GET.get('page', 1))
    search = request.GET.get('search', '')
    
    # Build the queryset based on data type
    if data_type == 'missing_characteristics':
        qs = DataIssue.objects.filter(
            issue_type="missing", 
            field__category="characteristic",
            council__status="active"
        )
    elif data_type == 'missing_financial':
        qs = DataIssue.objects.filter(
            issue_type="missing",
            council__status="active"
        ).exclude(field__category="characteristic")
    elif data_type == 'suspicious':
        qs = DataIssue.objects.filter(issue_type="suspicious")
    elif data_type == 'pending':
        # This would be for pending contributions - stub for now
        from .models import Contribution
        contributions = Contribution.objects.filter(status='pending')[:25]
        return JsonResponse({
            'html': '<tr><td colspan="4" class="text-center py-4">Pending contributions feature coming soon</td></tr>',
            'pagination_html': '',
            'total_count': 0
        })
    else:
        qs = DataIssue.objects.none()
    
    # Apply search filter
    if search:
        qs = qs.filter(council__name__icontains=search)
    
    # Select related for efficiency
    qs = qs.select_related("council", "field", "year").order_by("council__name")
    
    # Paginate
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_num)
    
    # Build HTML for the table rows
    rows_html = []
    for issue in page_obj:
        year_display = issue.year.year if issue.year else "N/A"
        rows_html.append(f"""
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {issue.council.name}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {issue.field.name}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {year_display}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="contributeManager.openEditModal({{
                        council: '{issue.council.slug}',
                        field: '{issue.field.slug}',
                        councilName: '{issue.council.name}',
                        fieldName: '{issue.field.name}',
                        year: '{issue.year.slug if issue.year else ""}',
                        yearName: '{year_display}'
                    }})" class="text-blue-600 hover:text-blue-900">
                        Add Data
                    </button>
                </td>
            </tr>
        """)
    
    # Build pagination HTML
    pagination_html = ""
    if paginator.num_pages > 1:
        pagination_html = f"""
            <div class="flex items-center justify-between px-6 py-3 bg-gray-50">
                <div class="text-sm text-gray-700">
                    Showing {page_obj.start_index()} to {page_obj.end_index()} of {paginator.count} results
                </div>
                <div class="flex space-x-1">
        """
        
        if page_obj.has_previous():
            pagination_html += f"""
                <button onclick="contributeManager.loadPage({page_obj.previous_page_number()})" 
                        class="px-3 py-1 rounded-md bg-white border border-gray-300 text-sm text-gray-700 hover:bg-gray-50">
                    Previous
                </button>
            """
        
        if page_obj.has_next():
            pagination_html += f"""
                <button onclick="contributeManager.loadPage({page_obj.next_page_number()})" 
                        class="px-3 py-1 rounded-md bg-white border border-gray-300 text-sm text-gray-700 hover:bg-gray-50">
                    Next
                </button>
            """
        
        pagination_html += """
                </div>
            </div>
        """
    
    return JsonResponse({
        'html': ''.join(rows_html),
        'pagination_html': pagination_html,
        'total_count': paginator.count
    })

def submit_contribution(request):
    """Handle contribution submissions - delegate to contribute_submit for AJAX calls"""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return contribute_submit(request)
    else:
        # Handle regular form submission
        from django.http import HttpResponse
        return HttpResponse("Submit Contribution - Regular form submission not implemented yet")

def search_councils(request):
    """Search councils API for autocomplete"""
    from .models import Council
    
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({"results": []})
    
    councils = Council.objects.filter(
        name__icontains=query,
        status='active'
    ).order_by('name')[:20]
    
    results = [
        {
            'id': council.slug,
            'name': council.name,
            'type': council.council_type.name if council.council_type else 'Unknown'
        }
        for council in councils
    ]
    
    return JsonResponse({"results": results})

def signup_view(request):
    """User signup view"""
    from django.http import HttpResponse
    return HttpResponse("Signup - Not implemented yet")

def confirm_email(request, token):
    """Confirm email address"""
    from django.http import HttpResponse
    return HttpResponse("Confirm Email - Not implemented yet")

def resend_confirmation(request):
    """Resend confirmation email"""
    from django.http import HttpResponse
    return HttpResponse("Resend Confirmation - Not implemented yet")

def update_postcode(request):
    """Update user postcode"""
    from django.http import HttpResponse
    return HttpResponse("Update Postcode - Not implemented yet")

def confirm_profile_change(request):
    """Confirm profile change"""
    from django.http import HttpResponse
    return HttpResponse("Confirm Profile Change - Not implemented yet")

def notifications_page(request):
    """Notifications page"""
    from django.http import HttpResponse
    return HttpResponse("Notifications - Not implemented yet")

def dismiss_notification(request):
    """Dismiss a notification"""
    from django.http import JsonResponse
    return JsonResponse({"message": "Dismiss Notification - Not implemented yet"})

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

def council_detail(request, slug):
    """Council detail page showing counters and data"""
    from .models import Council
    
    council = get_object_or_404(Council, slug=slug)
    
    context = {
        'council': council,
        'title': f"{council.name} - Council Finance Data"
    }
    
    return render(request, 'council_finance/council_detail.html', context)
