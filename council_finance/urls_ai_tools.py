"""
AI Tools URL Configuration

Separate URL patterns for AI tools to avoid circular imports.
"""

from django.urls import path

# Import AI tools views
from .views import ai_tools_hub
from .views.ai_analytics_dashboard import (
    ai_analytics_dashboard, usage_analytics_api, cost_tracking_api, create_performance_alert
)
from .views.ai_monitoring_dashboard import (
    ai_monitoring_dashboard, get_live_metrics, get_hourly_trends, 
    resolve_anomaly, update_load_balancer, update_budget_alert
)

# AI Tools URL patterns
urlpatterns = [
    # AI Tools Hub - Unified navigation for all AI features
    path("ai-tools/", ai_tools_hub.ai_tools_hub, name="ai_tools_hub"),
    path("ai-tools/analytics/", ai_analytics_dashboard, name="ai_tools_analytics"),
    path("ai-tools/monitoring/", ai_monitoring_dashboard, name="ai_tools_monitoring"),
    path("ai-tools/monitoring/api/live-metrics/", get_live_metrics, name="ai_tools_live_metrics"),
    path("ai-tools/monitoring/api/hourly-trends/", get_hourly_trends, name="ai_tools_hourly_trends"),
    path("ai-tools/monitoring/api/resolve-anomaly/", resolve_anomaly, name="ai_tools_resolve_anomaly"),
    path("ai-tools/monitoring/api/update-load-balancer/", update_load_balancer, name="ai_tools_update_load_balancer"),
    
    # Legacy AI Analytics Dashboard URLs (kept for backwards compatibility)
    path("ai-factoids/analytics/", ai_analytics_dashboard, name="ai_analytics_dashboard"),
    path("ai-factoids/analytics/usage-api/", usage_analytics_api, name="usage_analytics_api"),
    path("ai-factoids/analytics/cost-api/", cost_tracking_api, name="cost_tracking_api"),
    path("ai-factoids/analytics/alerts/create/", create_performance_alert, name="create_performance_alert"),
]