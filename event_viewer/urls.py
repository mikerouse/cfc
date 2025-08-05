"""
Event Viewer URL Configuration

All URLs require superuser access and follow GOV.UK URL patterns.
"""

from django.urls import path
from . import views

app_name = 'event_viewer'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Event management
    path('events/', views.event_list, name='event_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/resolve/', views.resolve_event, name='resolve_event'),
    path('events/bulk-resolve/', views.bulk_resolve, name='bulk_resolve'),
    
    # Analytics and reporting
    path('analytics/', views.analytics, name='analytics'),
    path('export/', views.export_events, name='export_events'),
]