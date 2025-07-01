from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Council


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
