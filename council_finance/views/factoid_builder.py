"""
API views for the React-based Factoid Builder.
This module provides endpoints for discovering data fields and previewing factoids.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from council_finance.models import DataField, Council

@require_GET
def available_fields_api(request, council_slug=None):
    """
    API endpoint to get available data fields for the factoid builder.
    Can be filtered by council to show only fields with data for that council.
    """
    fields = DataField.objects.all().order_by('category', 'name')
    
    if council_slug:
        # If a council is specified, we could filter to only fields that have data for that council.
        # This is a placeholder for that logic.
        pass

    field_data = [
        {
            "slug": field.slug,
            "name": field.name,
            "category": field.get_category_display(),
            "data_type": field.data_type,
        }
        for field in fields
    ]
    
    return JsonResponse({"fields": field_data})

@require_GET
def preview_factoid_api(request):
    """
    API endpoint to live-preview a factoid based on a formula and context.
    """
    # This is a placeholder for the preview logic.
    # The actual implementation will take a formula and context (council, year)
    # and return the calculated result.
    return JsonResponse({
        "success": True,
        "preview": {
            "text": "This is a preview of the factoid.",
            "value": 12345,
            "formatted_value": "12,345"
        }
    })
