from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth import login
from .models import Council, UserProfile
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
import hashlib
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Cast

from .models import Council, FinancialYear, FigureSubmission


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

    # Pass the object straight through to the template for display
    return render(
        request,
        "council_finance/council_detail.html",
        {"council": council},
    )


@login_required
def profile_view(request):
    """Display information about the currently logged-in user."""

    user = request.user
    # Attempt to grab the related profile (created automatically via signals).
    profile = getattr(user, "profile", None)
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
    }
    return render(request, "registration/profile.html", context)


def signup_view(request):
    """Allow visitors to create an account with a required postcode."""

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Create the user and log them in immediately
            user = form.save()
            login(request, user)
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
    if not postcode:
        return JsonResponse({"error": "Postcode required"}, status=400)

    profile = request.user.profile
    profile.postcode = postcode
    profile.save()
    return JsonResponse({"postcode": profile.postcode})
