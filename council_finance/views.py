from django.shortcuts import render, get_object_or_404, redirect
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
from django.urls import reverse
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
    DataFieldForm,
    ProfileExtraForm,
)
from django.conf import settings

from .models import DataField
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
    SiteSetting,
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

    context = {
        "query": query,
        "councils": councils,
        "total_debt": total_debt,
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
    figures = (
        FigureSubmission.objects.filter(council=council)
        .select_related("year", "field")
        .order_by("year__label", "field__slug")
    )

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
    counters = []
    default_slugs = []
    if selected_year:
        from council_finance.agents.counter_agent import CounterAgent

        agent = CounterAgent()
        # Compute all counter values for this council/year using the agent
        values = agent.run(council_slug=slug, year_label=selected_year.label)

        # Build a lookup of overrides so we know which counters are enabled or
        # disabled specifically for this council.
        override_map = {
            cc.counter_id: cc.enabled
            for cc in CouncilCounter.objects.filter(council=council)
        }

        # Loop over every defined counter and decide whether it should be
        # displayed. If the council has an explicit override we honour that,
        # otherwise we fall back to the counter's show_by_default flag.
        for counter in CounterDefinition.objects.all():
            enabled = override_map.get(counter.id, counter.show_by_default)
            if not enabled:
                continue
            result = values.get(counter.slug, {})
            counters.append(
                {
                    "counter": counter,
                    "value": result.get("value"),
                    "formatted": result.get("formatted"),
                    "error": result.get("error"),
                }
            )
            if counter.show_by_default:
                default_slugs.append(counter.slug)

    context = {
        "council": council,
        "figures": figures,
        "counters": counters,
        "years": years,
        "selected_year": selected_year,
        "default_counter_slugs": default_slugs,
        "tab": tab,
        "focus": focus,
        # Set of field slugs with pending contributions so the template
        # can show a "pending confirmation" notice in place of the form.
        "pending_slugs": set(
            Contribution.objects.filter(
                council=council, status="pending"
            ).values_list("field__slug", flat=True)
        ),
    }
    if tab == "edit":
        from .models import CouncilType

        context["council_types"] = CouncilType.objects.all()

    return render(request, "council_finance/council_detail.html", context)


# Additional views for common site pages


def leaderboards(request):
    """Placeholder leaderboards page."""
    return render(request, "council_finance/leaderboards.html")


def my_lists(request):
    """Allow users to manage their favourite councils and custom lists."""
    if not request.user.is_authenticated:
        return redirect("login")

    profile = request.user.profile
    # Prefetch councils so template access doesn't hit the DB repeatedly
    lists = request.user.council_lists.prefetch_related("councils")
    favourites = profile.favourites.all()
    form = CouncilListForm()

    # Latest year used when pulling population figures for display
    latest_year = FinancialYear.objects.order_by("-label").first()
    # Map of council_id -> numeric population value so we can sum totals
    pop_values = {}
    # Map of council_id -> display string used in templates
    pop_display = {}
    if latest_year:
        pop_field = DataField.objects.filter(slug="population").first()
        for fs in FigureSubmission.objects.filter(field=pop_field, year=latest_year):
            try:
                val = float(fs.value)
            except (TypeError, ValueError):
                val = 0
            pop_values[fs.council_id] = val
            # When we have a meaningful value show it, otherwise instruct that
            # the figure still needs to be populated.
            pop_display[fs.council_id] = int(val) if val else "Needs populating"

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
    """Show councils the user follows."""
    return render(request, "council_finance/following.html")


def contribute(request):
    """Show contribution dashboard with various queues."""
    queue = Contribution.objects.filter(status="pending").select_related("council", "field", "user")
    my_contribs = (
        Contribution.objects.filter(user=request.user).select_related("council", "field")
        if request.user.is_authenticated
        else []
    )
    return render(
        request,
        "council_finance/contribute.html",
        {"queue": queue, "my_contribs": my_contribs},
    )


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
        f"https://www.gravatar.com/avatar/{email_hash}?d=identicon" if email_hash else None
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

    if not request.user.is_staff:
        raise Http404()

    counters = CounterDefinition.objects.all()
    return render(
        request,
        "council_finance/counter_definition_list.html",
        {"counters": counters},
    )


@login_required
def counter_definition_form(request, slug=None):
    """Create or edit a single counter definition, with live preview for selected council."""

    if not request.user.is_staff:
        raise Http404()

    from .models import Council

    counter = get_object_or_404(CounterDefinition, slug=slug) if slug else None
    form = CounterDefinitionForm(request.POST or None, instance=counter)

    # For preview dropdown: all councils and all years
    councils = Council.objects.all().order_by("name")
    years = FinancialYear.objects.order_by("-label")
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
    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )
    if BlockedIP.objects.filter(ip_address=ip).exists():
        return JsonResponse({"error": "blocked"}, status=403)

    # Gracefully handle an invalid field slug. Instead of returning a 404 we
    # log the details and send a JSON error so the UI can show a friendly
    # message.
    try:
        field = DataField.objects.get(slug=field_slug)
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
    # Submissions from tier 3+ skip moderation
    status = "approved" if profile.tier.level >= 3 else "pending"

    Contribution.objects.create(
        user=request.user,
        council=council,
        field=field,
        year=year,
        value=value,
        status=status,
        ip_address=ip,
    )
    if status == "approved":
        msg = "Contribution accepted"
    else:
        msg = "Contribution queued for approval"

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
        # Always award two points when a contribution is approved.
        points = 2
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

        for counter in CounterDefinition.objects.all():
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
            }

    return JsonResponse({"counters": data})


@login_required
def field_list(request):
    """List all data fields for staff management."""
    if not request.user.is_staff:
        raise Http404()
    fields = DataField.objects.all()
    return render(request, "council_finance/field_list.html", {"fields": fields})


@login_required
def field_form(request, slug=None):
    """Create or edit a data field."""
    if not request.user.is_staff:
        raise Http404()
    field = get_object_or_404(DataField, slug=slug) if slug else None
    form = DataFieldForm(request.POST or None, instance=field)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Field saved.")
        return redirect("field_list")
    return render(request, "council_finance/field_form.html", {"form": form})


@login_required
def field_delete(request, slug):
    """Delete a data field unless it's protected."""
    if not request.user.is_staff:
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
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
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
        if "delete" in request.POST:
            ids = request.POST.getlist("ids")
            RejectionLog.objects.filter(id__in=ids).delete()
            messages.success(request, "Deleted entries")
            logger.info("Deleted rejection log entries %s by %s", ids, request.user.username)
        if "block" in request.POST:
            ip = request.POST.get("block")
            BlockedIP.objects.get_or_create(ip_address=ip)
            messages.success(request, f"Blocked {ip}")
            logger.info("Blocked IP %s by %s", ip, request.user.username)
        return redirect("god_mode")

    logs = RejectionLog.objects.select_related("council", "field", "reviewed_by")[:200]
    return render(request, "council_finance/god_mode.html", {"logs": logs})
