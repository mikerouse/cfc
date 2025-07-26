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
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'templates', FactoidAPIViewSet, basename='factoid-template')

app_name = 'factoid_api'

urlpatterns = [
    # Custom API endpoints (use different path to avoid ViewSet conflicts)
    path('fields/search/', realtime_field_search, name='field-search'),
    path('quick-validate/', quick_template_validation, name='quick-validation'),
    path('quick-preview/', quick_template_preview, name='quick-preview'),
    
    # ViewSet routes
    path('', include(router.urls)),
]
