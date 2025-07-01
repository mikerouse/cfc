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

# Additional views for common site pages

def leaderboards(request):
    """Placeholder leaderboards page."""
    return render(request, "council_finance/leaderboards.html")


def my_lists(request):
    """Display lists for authenticated users."""
    if not request.user.is_authenticated:
        # Redirect anonymous users to the login page
        from django.shortcuts import redirect
        return redirect('login')
    return render(request, "council_finance/my_lists.html")


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
