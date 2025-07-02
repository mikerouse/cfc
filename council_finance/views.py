from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Cast
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth import login
from django.utils.crypto import get_random_string
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
    INTERNAL_FIELDS,
)
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
)


def search_councils(request):
    """Return councils matching a query for live search."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    results = (
        Council.objects.filter(Q(name__icontains=query) | Q(slug__icontains=query))
        .values("name", "slug")[:10]
    )
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
        total_debt = (
            FigureSubmission.objects.filter(
                field_name="total_debt", year=latest_year
            ).aggregate(
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
    query = request.GET.get('q', '')

    # Base queryset of all councils
    councils = Council.objects.all()

    # Apply a simple case-insensitive name or slug filter when a query is present
    if query:
        councils = councils.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        )
    context = {
        "councils": councils,
        "query": query,
    }
    return render(request, "council_finance/council_list.html", context)


def council_detail(request, slug):
    """Show details for a single council."""
    # Fetch the council or return a 404 if the slug is unknown
    council = get_object_or_404(Council, slug=slug)

    # Pull all financial figures for this council so the template can
    # present them in an engaging way.
    figures = (
        FigureSubmission.objects.filter(council=council)
        .select_related("year")
        .order_by("year__label", "field_name")
    )

    latest_year = FinancialYear.objects.order_by("-label").first()
    counters = []
    if latest_year:
        from council_finance.agents.counter_agent import CounterAgent

        agent = CounterAgent()
        # Compute all counter values for this council/year using the agent
        values = agent.run(council_slug=slug, year_label=latest_year.label)
        # Fetch enabled counters and attach the calculated value to each entry
        for cc in (
            CouncilCounter.objects.filter(council=council, enabled=True)
            .select_related("counter")
        ):
            result = values.get(cc.counter.slug, {})
            counters.append(
                {
                    "counter": cc.counter,
                    "value": result.get("value"),
                    "formatted": result.get("formatted"),
                    "error": result.get("error"),
                }
            )

    context = {
        "council": council,
        "figures": figures,
        "counters": counters,
    }

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
    favourites = profile.favourites.all()
    lists = request.user.council_lists.all()
    form = CouncilListForm()

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

    context = {"favourites": favourites, "lists": lists, "form": form}
    return render(request, "council_finance/my_lists.html", context)


def following(request):
    """Show councils the user follows."""
    return render(request, "council_finance/following.html")


def submit(request):
    """Placeholder submission page."""
    return render(request, "council_finance/submit.html")


def my_profile(request):
    """Simple profile or redirect to login."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('login')
    return render(request, "council_finance/my_profile.html")


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
    councils = Council.objects.all().order_by('name')
    years = FinancialYear.objects.order_by('-label')
    preview_council_slug = request.GET.get('preview_council') or (councils[0].slug if councils else None)
    # Only use a valid year label for preview_year_label
    valid_year_labels = [y.label for y in years]
    requested_year = request.GET.get('preview_year')
    preview_year_label = requested_year if requested_year in valid_year_labels else (years[0].label if years else None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Counter saved.")
        return redirect("counter_definitions")

    context = {
        "form": form,
        "available_fields": INTERNAL_FIELDS,
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
    council_slug = request.GET.get('council')
    formula = request.GET.get('formula')
    year_label = request.GET.get('year')
    year = None
    if year_label:
        year = FinancialYear.objects.filter(label=year_label).first()
    if not year:
        year = FinancialYear.objects.order_by('-label').first()
    if not (council_slug and formula and year):
        return JsonResponse({'error': 'Missing data'}, status=400)
    agent = CounterAgent()
    from .models import CounterDefinition
    try:
        council = Council.objects.get(slug=council_slug)
        # Build a map of values while tracking any missing figures so we can
        # surface a clear error message instead of casting blank strings.
        figure_map = {}
        missing = set()
        for f in FigureSubmission.objects.filter(council=council, year=year):
            if f.needs_populating or f.value in (None, ""):
                missing.add(f.field_name)
                continue
            try:
                figure_map[f.field_name] = float(f.value)
            except (TypeError, ValueError):
                missing.add(f.field_name)
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
                        % (node.id.replace('_', ' '), council.name, year.label)
                    )
                return figure_map.get(node.id, 0)
            raise ValueError("Unsupported expression element")
        tree = ast.parse(formula, mode="eval")
        value = float(_eval(tree))
        precision = int(request.GET.get('precision', 0))
        show_currency = request.GET.get('show_currency', 'true') == 'true'
        friendly_format = request.GET.get('friendly_format', 'false') == 'true'
        class Dummy:
            pass
        dummy = Dummy()
        dummy.precision = precision
        dummy.show_currency = show_currency
        dummy.friendly_format = friendly_format
        from .models.counter import CounterDefinition as CD
        formatted = CD.format_value(dummy, value)
        return JsonResponse({'value': value, 'formatted': formatted})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'calculation failed'}, status=400)

@login_required
def profile_view(request):
    """Display information about the currently logged-in user."""

    user = request.user
    # Ensure we always have a profile so postcode input always appears.
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"confirmation_token": get_random_string(32)},
    )

    # Handle form submissions
    if request.method == "POST":
        # Update visibility directly
        if "visibility" in request.POST:
            profile.visibility = request.POST.get("visibility", profile.visibility)
            profile.save()
            messages.success(request, "Visibility updated.")
        # Request a change to names, email or password which must be confirmed
        elif "change_details" in request.POST:
            token = get_random_string(32)
            PendingProfileChange.objects.create(
                user=user,
                token=token,
                new_first_name=request.POST.get("first_name", ""),
                new_last_name=request.POST.get("last_name", ""),
                new_email=request.POST.get("email", ""),
                new_password=make_password(request.POST.get("password1", ""))
                if request.POST.get("password1")
                else "",
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
    context = {
        "user": user,
        "profile": profile,
        "gravatar_url": gravatar_url,
        "followers": followers,
        "visibility_choices": UserProfile.VISIBILITY_CHOICES,
        "tab": "profile",
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
    return JsonResponse({"postcode": profile.postcode, "refused": profile.postcode_refused})


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
        if hasattr(e, 'body') and isinstance(e.body, str):
            import json
            try:
                body = json.loads(e.body)
                if 'message' in body:
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

