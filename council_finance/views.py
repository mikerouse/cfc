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
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET
import csv
import hashlib

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
)

from datetime import date


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
            "show_currency": gc.show_currency,
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
    """Show contribution dashboard with various queues."""
    from .models import DataIssue
    from django.core.paginator import Paginator

    # Load the first page of each issue type. The remaining pages can be
    # requested via AJAX so initial load time stays reasonable even when the
    # dataset contains thousands of records.
    missing_financial_qs = (
        DataIssue.objects.filter(issue_type="missing")
        .exclude(field__category="characteristic")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )
    missing_characteristic_qs = (
        DataIssue.objects.filter(issue_type="missing", field__category="characteristic")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )
    suspicious_qs = (
        DataIssue.objects.filter(issue_type="suspicious")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )

    missing_financial_paginator = Paginator(missing_financial_qs, 50)
    missing_characteristic_paginator = Paginator(missing_characteristic_qs, 50)
    suspicious_paginator = Paginator(suspicious_qs, 50)
    missing_financial_page = missing_financial_paginator.get_page(1)
    missing_characteristic_page = missing_characteristic_paginator.get_page(1)
    suspicious_page = suspicious_paginator.get_page(1)
    my_contribs = (
        Contribution.objects.filter(user=request.user).select_related(
            "council", "field"
        )
        if request.user.is_authenticated
        else []
    )
    return render(
        request,
        "council_finance/contribute.html",
        {
            "missing_financial_page": missing_financial_page,
            "missing_financial_paginator": missing_financial_paginator,
            "missing_characteristic_page": missing_characteristic_page,
            "missing_characteristic_paginator": missing_characteristic_paginator,
            "suspicious_page": suspicious_page,
            "suspicious_paginator": suspicious_paginator,
            "my_contribs": my_contribs,
        },
    )


def data_issues_table(request):
    """Return a page of data issues as HTML for the contribute tables."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")

    from .models import DataIssue

    issue_type = request.GET.get("type")
    if issue_type not in {"missing", "suspicious"}:
        return HttpResponseBadRequest("invalid type")

    search = request.GET.get("q", "").strip()
    category = request.GET.get("category")
    order = request.GET.get("order", "council")
    direction = request.GET.get("dir", "asc")
    allowed = {"council": "council__name", "field": "field__name", "year": "year__label", "value": "value"}
    order_by = allowed.get(order, "council__name")
    if direction == "desc":
        order_by = f"-{order_by}"

    qs = DataIssue.objects.filter(issue_type=issue_type).select_related("council", "field", "year")
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

    show_year = not (issue_type == "missing" and category == "characteristic")
    html = render_to_string(
        "council_finance/data_issues_table.html",
        {
            "page_obj": page,
            "paginator": paginator,
            "issue_type": issue_type,
            "show_year": show_year,
        },
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
from django.views.decorators.http import require_GET


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
        elif user.is_superuser and "tier" in request.POST:
            # Allow superusers to switch tier for testing purposes.
            tier = TrustTier.objects.filter(id=request.POST.get("tier")).first()
            if tier:
                profile.tier = tier
                profile.save()
                messages.success(request, f"Tier changed to {tier.name}.")
            tab = "custom"
        elif "visibility" in request.POST:
            profile.visibility = request.POST.get("visibility", profile.visibility)
            profile.save()
            messages.success(request, "Visibility updated.")
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
        elif "update_extra" in request.POST:
            form = ProfileExtraForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile details saved.")

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
    if status == "approved":
        # Immediately apply the change so followers see the update straight away.
        try:
            _apply_contribution(contrib, request.user)
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
        award = 2 if field.category == "characteristic" else 1
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
        return JsonResponse({"status": status, "message": msg})

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
        _apply_contribution(contrib, request.user)
        contrib.status = "approved"
        contrib.save()
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
    elif action == "reject" and request.method == "POST":
        reason = request.POST.get("reason")
        if not reason:
            return HttpResponseBadRequest("reason required")
        contrib.status = "rejected"
        contrib.save()
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
        return redirect("contribute")
    return redirect("contribute")


def _apply_contribution(contribution, user):
    """Persist an approved contribution and log the change."""
    field = contribution.field
    council = contribution.council

    old_value = contribution.old_value

    if field.slug == "council_website":
        council.website = contribution.value
        council.save()
    elif field.slug == "council_type":
        council.council_type_id = contribution.value or None
        council.save()
    elif field.slug == "council_nation":
        council.council_nation_id = contribution.value or None
        council.save()
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


@login_required
def list_metric(request, list_id):
    """Return metric values for a list and a selected year."""
    field = request.GET.get("field")
    if not field:
        return JsonResponse({"error": "field required"}, status=400)
    try:
        lst = request.user.council_lists.prefetch_related("councils").get(id=list_id)
    except CouncilList.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    # Allow callers to specify a financial year. Default to the latest year when
    # the parameter is missing or invalid.
    year_id = request.GET.get("year")
    if year_id:
        year = FinancialYear.objects.filter(id=year_id).first()
    else:
        year = None
    if not year:
        year = FinancialYear.objects.order_by("-label").first()

    values = {}
    total = 0.0
    if year:
        field_obj = DataField.objects.filter(slug=field).first()
        qs = FigureSubmission.objects.filter(
            council__in=lst.councils.all(), year=year, field=field_obj
        )
        for fs in qs:
            values[str(fs.council_id)] = fs.value
            try:
                total += float(fs.value)
            except (TypeError, ValueError):
                continue

    return JsonResponse({"values": values, "total": total})


def add_to_compare(request, slug):
    """Add a council slug to the comparison basket stored in the session."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    basket = request.session.get("compare_basket", [])
    if slug not in basket:
        basket.append(slug)
        basket = basket[:6]
        request.session["compare_basket"] = basket
    return JsonResponse({"count": len(basket)})


def remove_from_compare(request, slug):
    """Remove a council from the session comparison basket."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    basket = request.session.get("compare_basket", [])
    if slug in basket:
        basket.remove(slug)
        request.session["compare_basket"] = basket
    return JsonResponse({"count": len(basket)})


def compare_row(request):
    """Return a single table row of comparison data for AJAX."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")
    slug = request.GET.get("field")
    if not slug:
        return HttpResponseBadRequest("field required")
    field = DataField.objects.filter(slug=slug).first()
    if not field:
        return HttpResponseBadRequest("invalid field")
    councils = Council.objects.filter(slug__in=request.session.get("compare_basket", []))
    values = []
    numeric = []
    for c in councils:
        if slug == "council_type":
            values.append(c.council_type.name if c.council_type else "")
        else:
            fs = (
                FigureSubmission.objects.filter(council=c, field=field)
                .order_by("-year__label")
                .first()
            )
            if fs:
                values.append(field.display_value(fs.value))
                try:
                    numeric.append(float(fs.value))
                except (TypeError, ValueError):
                    numeric.append(None)
            else:
                values.append("")
                numeric.append(None)

    summary = None
    if field.content_type in {"monetary", "integer"} and any(v is not None for v in numeric):
        valid = [v for v in numeric if v is not None]
        total = sum(valid)
        average = total / len(valid)
        max_idx = valid.index(max(valid))
        min_idx = valid.index(min(valid))
        summary = {
            "total": field.display_value(total),
            "average": field.display_value(average),
            "highest": councils[max_idx].name,
            "lowest": councils[min_idx].name,
        }

    return render(
        request,
        "council_finance/compare_row.html",
        {"field": field, "values": values, "summary": summary},
    )


def compare_basket(request):
    """Display the user's current comparison basket."""
    slugs = request.session.get("compare_basket", [])
    councils = list(Council.objects.filter(slug__in=slugs).order_by("name"))
    selected = request.session.get("compare_fields", [])
    if request.method == "POST" and request.user.is_authenticated and "save_list" in request.POST:
        form = CouncilListForm(request.POST)
        if form.is_valid():
            lst = form.save(commit=False)
            lst.user = request.user
            lst.save()
            lst.councils.set(councils)
            messages.success(request, "List saved")
            return redirect("my_lists")
    else:
        form = CouncilListForm()
    fields = DataField.objects.filter(slug__in=["council_type", "population"] + selected)
    rows = []
    for field in fields:
        vals = []
        numeric = []
        for c in councils:
            if field.slug == "council_type":
                vals.append(c.council_type.name if c.council_type else "")
            else:
                fs = (
                    FigureSubmission.objects.filter(council=c, field=field)
                    .order_by("-year__label")
                    .first()
                )
                if fs:
                    vals.append(field.display_value(fs.value))
                    try:
                        numeric.append(float(fs.value))
                    except (TypeError, ValueError):
                        numeric.append(None)
                else:
                    vals.append("")
                    numeric.append(None)

        summary = None
        if field.content_type in {"monetary", "integer"} and any(n is not None for n in numeric):
            valid = [n for n in numeric if n is not None]
            total = sum(valid)
            average = total / len(valid)
            max_idx = valid.index(max(valid))
            min_idx = valid.index(min(valid))
            summary = {
                "total": field.display_value(total),
                "average": field.display_value(average),
                "highest": councils[max_idx].name,
                "lowest": councils[min_idx].name,
            }

        rows.append({"field": field, "values": vals, "summary": summary})
    field_choices = DataField.objects.exclude(slug__in=["council_type", "population"] + selected)
    context = {
        "councils": councils,
        "rows": rows,
        "field_choices": field_choices,
        "form": form,
    }
    return render(request, "council_finance/comparison_basket.html", context)


@login_required
def edit_figures_table(request, slug):
    """Return the edit table HTML for a specific year."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")

    council = get_object_or_404(Council, slug=slug)
    year_label = request.GET.get("year")
    year = None
    if year_label:
        year = FinancialYear.objects.filter(label=year_label).first()
    if not year:
        year = FinancialYear.objects.order_by("-label").first()

    # Fetch all field definitions relevant to this council. Existing figure
    # submissions are loaded into a map so we can include blank rows for
    # missing data, allowing users to provide new figures.
    fields = DataField.objects.exclude(category="characteristic")
    if council.council_type_id:
        fields = fields.filter(
            Q(council_types__isnull=True) | Q(council_types=council.council_type)
        )
    else:
        fields = fields.filter(council_types__isnull=True)
    fields = fields.distinct()

    existing = {
        (fs.field_id): fs
        for fs in FigureSubmission.objects.filter(council=council, year=year)
        .exclude(field__category="characteristic")
        .select_related("field", "year")
    }
    figures = []
    for field in fields.order_by("name"):
        fs = existing.get(field.id)
        if not fs:
            fs = FigureSubmission(council=council, year=year, field=field, value="")
        figures.append(fs)

    context = {
        "figures": figures,
        "council": council,
        "pending_pairs": set(
            f"{slug}-{y or 'none'}"
            for slug, y in Contribution.objects.filter(council=council, status="pending").values_list("field__slug", "year_id")
        ),
    }
    return render(request, "council_finance/edit_figures_table.html", context)


def council_counters(request, slug):
    """Return counter values for a council and year as JSON."""
    # Allow callers to specify a financial year label. Default to latest year
    # when the parameter is missing or invalid so the UI always has data.
    year_label = request.GET.get("year")
    if year_label:
        year = FinancialYear.objects.filter(label=year_label).first()
    else:
        year = None
    if not year:
        year = FinancialYear.objects.order_by("-label").first()

    council = get_object_or_404(Council, slug=slug)

    data = {}
    if year:
        from council_finance.agents.counter_agent import CounterAgent

        agent = CounterAgent()
        values = agent.run(council_slug=slug, year_label=year.label)

        override_map = {
            cc.counter_id: cc.enabled
            for cc in CouncilCounter.objects.filter(council=council)
        }

        ordered = list(CounterDefinition.objects.all())
        if council.council_type_id:
            ordered = [
                c
                for c in ordered
                if not c.council_types.exists()
                or c.council_types.filter(id=council.council_type_id).exists()
            ]
        else:
            ordered = [c for c in ordered if not c.council_types.exists()]
        ordered.sort(key=lambda c: (not c.headline, c.slug))
        for counter in ordered:
            enabled = override_map.get(counter.id, counter.show_by_default)
            if not enabled:
                continue
            result = values.get(counter.slug, {})
            data[counter.slug] = {
                "name": counter.name,
                "duration": counter.duration,
                "value": result.get("value"),
                "formatted": result.get("formatted"),
                "error": result.get("error"),
                # Expose formatting defaults so the client can override them
                # when rendering counters in the UI. These mirror fields on
                # ``CounterDefinition`` and allow the front end to apply custom
                # user preferences without another round trip to the server.
                "show_currency": counter.show_currency,
                "precision": counter.precision,
                "friendly_format": counter.friendly_format,
                "headline": counter.headline,
            }

    return JsonResponse({"counters": data})


@login_required
def field_list(request):
    """List all data fields and council characteristics for management."""
    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()
    # Split fields by category so the template can render a tab for each
    # category. Ordering by name keeps the list predictable within each tab.
    fields_by_category = {
        slug: DataField.objects.filter(category=slug).order_by("name")
        for slug, _ in DataField.FIELD_CATEGORIES
    }
    context = {
        "categories": DataField.FIELD_CATEGORIES,
        "fields_by_category": fields_by_category,
    }
    return render(request, "council_finance/field_list.html", context)


@login_required
def field_form(request, slug=None):
    """Create or edit a data field."""
    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()
    field = get_object_or_404(DataField, slug=slug) if slug else None
    form = DataFieldForm(request.POST or None, instance=field)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Field saved.")
        return redirect("field_list")
    return render(request, "council_finance/field_form.html", {"form": form})


@login_required
def factoid_list(request):
    """List all factoids for management."""
    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()
    factoids = Factoid.objects.all()
    return render(request, "council_finance/factoid_list.html", {"factoids": factoids})


@login_required
def factoid_form(request, slug=None):
    """Create or edit a factoid."""
    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()
    factoid = get_object_or_404(Factoid, slug=slug) if slug else None
    form = FactoidForm(request.POST or None, instance=factoid)
    councils = Council.objects.order_by("name")
    years = list(FinancialYear.objects.order_by("-label"))
    for y in years:
        y.display_label = "Year to Date" if y.label.lower() == "general" else y.label
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Factoid saved.")
        return redirect("factoid_list")
    return render(
        request,
        "council_finance/factoid_form.html",
        {"form": form, "councils": councils, "years": years},
    )


@login_required
def factoid_delete(request, slug):
    """Remove a factoid. Only available to God Mode admins."""

    # God Mode corresponds to trust tier level 5. Superusers automatically
    # bypass the tier requirement which allows emergency cleanup of data.
    if not request.user.is_superuser and request.user.profile.tier.level < 5:
        raise Http404()

    factoid = get_object_or_404(Factoid, slug=slug)
    factoid.delete()
    messages.success(request, "Factoid deleted.")
    return redirect("factoid_list")


@login_required
def field_delete(request, slug):
    """Delete a data field unless it's protected."""
    if not request.user.is_superuser and request.user.profile.tier.level < MANAGEMENT_TIER:
        raise Http404()
    field = get_object_or_404(DataField, slug=slug)
    if field.is_protected:
        messages.error(request, "This field cannot be deleted.")
    else:
        field.delete()
        messages.success(request, "Field deleted.")
    return redirect("field_list")


@login_required
def god_mode(request):
    """Tier 5 tool for reviewing the rejection log and blocking IPs.

    Superusers are allowed to bypass the tier requirement entirely.
    """
    if not request.user.is_superuser and request.user.profile.tier.level < 5:
        raise Http404()

    # Configure a logger specifically for this view. The logger writes to
    # ``logs/god_mode.log`` so admins can see a history of actions performed
    # through this interface. We only set up the handler once to avoid duplicate
    # log entries when the view is called multiple times.
    import logging
    from pathlib import Path
    from django.conf import settings

    logger = logging.getLogger("god_mode")
    if not logger.handlers:
        log_dir = Path(settings.BASE_DIR) / "logs"
        log_dir.mkdir(exist_ok=True)
        handler = logging.FileHandler(log_dir / "god_mode.log")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    logger.info("%s accessed God Mode via %s", request.user.username, request.method)

    if request.GET.get("export") == "csv":
        rows = RejectionLog.objects.all().values_list(
            "id",
            "council__name",
            "field__name",
            "year__label",
            "value",
            "reason",
            "ip_address",
        )
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=rejections.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Council", "Field", "Year", "Value", "Reason", "IP"])
        for row in rows:
            writer.writerow(row)
        logger.info("CSV export triggered by %s", request.user.username)
        return response

    if request.method == "POST":
        if "reconcile_population" in request.POST:
            from .population import reconcile_populations

            updated = reconcile_populations()
            messages.success(request, f"Reconciled {updated} population figures")
            logger.info("Population reconciliation triggered by %s", request.user.username)
            return redirect("god_mode")
        if "assess_issues" in request.POST:
            from .data_quality import assess_data_issues

            total = assess_data_issues()
            messages.success(request, f"Identified {total} data issues")
            logger.info("Data issue assessment run by %s", request.user.username)
            return redirect("god_mode")
        if "delete" in request.POST:
            ids = request.POST.getlist("ids")
            RejectionLog.objects.filter(id__in=ids).delete()
            messages.success(request, "Deleted entries")
            logger.info(
                "Deleted rejection log entries %s by %s", ids, request.user.username
            )
        if "block" in request.POST:
            ip = request.POST.get("block")
            BlockedIP.objects.get_or_create(ip_address=ip)
            messages.success(request, f"Blocked {ip}")
            logger.info("Blocked IP %s by %s", ip, request.user.username)
        return redirect("god_mode")

    logs = RejectionLog.objects.select_related("council", "field", "reviewed_by")[:200]
    return render(request, "council_finance/god_mode.html", {"logs": logs})
