"""
URL Configuration for AI Tools and Analytics

Provides unified routing for all AI-related monitoring, analytics,
and management interfaces.
"""

from django.urls import path
from council_finance.views import (
    ai_analytics_dashboard,
    ai_monitoring_dashboard,
    ai_tools_hub,
)

app_name = 'ai_tools'

urlpatterns = [
    # Main AI tools hub
    path('', ai_tools_hub.ai_tools_hub, name='hub'),
    
    # Analytics dashboard
    path('analytics/', ai_analytics_dashboard.ai_analytics_dashboard, name='analytics'),
    
    # Monitoring dashboard
    path('monitoring/', ai_monitoring_dashboard.ai_monitoring_dashboard, name='monitoring'),
    
    # Monitoring API endpoints
    path('monitoring/api/live-metrics/', ai_monitoring_dashboard.get_live_metrics, name='live_metrics'),
    path('monitoring/api/hourly-trends/', ai_monitoring_dashboard.get_hourly_trends, name='hourly_trends'),
    path('monitoring/api/resolve-anomaly/', ai_monitoring_dashboard.resolve_anomaly, name='resolve_anomaly'),
    path('monitoring/api/update-load-balancer/', ai_monitoring_dashboard.update_load_balancer, name='update_load_balancer'),
    path('monitoring/api/update-budget-alert/', ai_monitoring_dashboard.update_budget_alert, name='update_budget_alert'),
]