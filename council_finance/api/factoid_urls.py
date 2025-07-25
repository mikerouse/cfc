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
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'templates', FactoidAPIViewSet, basename='factoid-template')

app_name = 'factoid_api'

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Custom API endpoints
    path('fields/search/', realtime_field_search, name='field-search'),
    path('templates/validate/', quick_template_validation, name='quick-validation'),
]
