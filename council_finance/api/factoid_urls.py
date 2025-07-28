"""
Factoid API URL Configuration

URL patterns for the factoid system API endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .factoid_views import (
    FactoidAPIViewSet,
    realtime_field_search,
    quick_template_validation,
    quick_template_preview,
    factoid_instance_api,
    get_factoids_for_counter,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'templates', FactoidAPIViewSet, basename='factoid-template')

app_name = 'factoid_api'

urlpatterns = [
    # Custom API endpoints (before ViewSet to ensure they match first)
    path('fields/search/', realtime_field_search, name='field-search'),
    path('quick-validate/', quick_template_validation, name='quick-validation'),
    path('quick-preview/', quick_template_preview, name='quick-preview'),
    
    # Get factoids for a specific counter
    path('counter/<slug:council_slug>/<slug:counter_slug>/', get_factoids_for_counter, name='factoids-for-counter'),
    path('counter/<slug:council_slug>/<slug:counter_slug>/<path:year_slug>/', get_factoids_for_counter, name='factoids-for-counter-year'),
    
    # ViewSet routes
    path('', include(router.urls)),
]
