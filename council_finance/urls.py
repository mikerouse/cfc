from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from .views import (
    general as general_views,
    contributions as contrib_views,
    admin as admin_views,
    api as api_views,
    auth as auth_views,
    onboarding_views,  # New onboarding views
    moderation as mod_views,
    councils as council_views,
    pages as page_views,
    council_management as council_mgmt_views,
    email_status as email_status_views,
    factoid_builder as factoid_builder_api,
    council_edit_api,
    feedback as feedback_views,
)
# Import following functions directly from general to avoid circular import issues
from .views.general import (
    my_lists,
    following,
    follow_item_api,
    unfollow_item_api,
    add_favourite,
    remove_favourite,
    add_to_list,
    remove_from_list,
    move_between_lists,
    list_metric,
    add_to_compare,
    remove_from_compare,
    compare_row,
    compare_basket,
    detailed_comparison,
    clear_compare_basket,
    follow_council,
    unfollow_council,
    like_update,
    comment_update,
    interact_with_update_api,
    comment_on_update_api,
    update_feed_preferences_api,
    get_feed_updates_api,
    comment_on_activity_log,
    get_activity_log_comments,
    like_activity_log_comment,
    github_stats_api,
    github_contributors_api,
)

# Import factoid instance API function
from .api.factoid_views import factoid_instance_api, get_factoids_for_counter_frontend

# Import AI factoid API functions
from .api.ai_factoid_api import (
    ai_council_factoids,
    ai_batch_factoids,
    clear_ai_factoid_cache,
    ai_factoid_status
)

# Import site-wide factoid API functions
from .api.sitewide_factoid_api import (
    get_sitewide_factoids,
    get_sitewide_factoids_health,
    sitewide_factoids_view
)

# Import AI factoid management views
from .views.ai_factoid_management import (
    ai_factoid_management_dashboard,
    council_ai_data_inspector,
    test_ai_generation,
    clear_factoid_cache,
    warmup_council_cache,
    council_financial_data_viewer,
    ai_configuration,
    sitewide_factoid_inspector,
    test_sitewide_generation,
    clear_sitewide_cache
)

# AI tools views - import here to avoid circular import issues
from .views import ai_tools_hub
from .views.ai_analytics_dashboard import (
    ai_analytics_dashboard, usage_analytics_api, cost_tracking_api, create_performance_alert
)
from .views.ai_monitoring_dashboard import (
    ai_monitoring_dashboard, get_live_metrics, get_hourly_trends, 
    resolve_anomaly, update_load_balancer, update_budget_alert
)

# Import comparison API views
from .api import comparison_api

# Import leaderboard API views
from .api.leaderboard_api import (
    get_leaderboard,
    get_council_rankings,
    get_categories,
    leaderboard_view
)

urlpatterns = [
    # Favicon redirect to avoid 404 errors
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico', permanent=True)),
    
    path("", general_views.home, name="home"),
    path("search/", general_views.search_results, name="search_results"),
    path("api/councils/search/", api_views.search_councils, name="search_councils"),
    path("api/emergency-cache-warming/", api_views.emergency_cache_warming, name="emergency_cache_warming"),
    
    # GitHub API endpoints for About page
    path("api/github/stats/", github_stats_api, name="github_stats_api"),
    path("api/github/contributors/", github_contributors_api, name="github_contributors_api"),
    path("admin/", admin.site.urls),
    path("system-events/", include("event_viewer.urls")),  # Event Viewer for superadmins
    path("plugins/", include("core.urls")),
    
    # Auth0 authentication endpoints (via social-django)
    path("auth/", include("social_django.urls", namespace="social")),
    
    # User onboarding endpoints
    path("welcome/", onboarding_views.welcome, name="welcome"),
    path("welcome/details/", onboarding_views.basic_details, name="onboarding_details"),
    path("welcome/age/", onboarding_views.age_verification, name="onboarding_age"),
    path("welcome/location/", onboarding_views.location_info, name="onboarding_location"),
    path("welcome/guidelines/", onboarding_views.community_guidelines, name="onboarding_guidelines"),
    path("welcome/complete/", onboarding_views.onboarding_complete, name="onboarding_complete"),
    
    # Legacy authentication endpoints (keep for backward compatibility)
    path(
        "accounts/login/",
        LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        LogoutView.as_view(template_name="registration/logged_out.html"),
        name="logout",
    ),
    path("accounts/signup/", auth_views.signup_view, name="signup"),
    path("accounts/confirm/<str:token>/", auth_views.confirm_email, name="confirm_email"),
    path("accounts/confirm-change/<str:token>/", auth_views.confirm_profile_change, name="confirm_profile_change"),
    path("accounts/cancel-email-change/", auth_views.cancel_email_change, name="cancel_email_change"),
    path("accounts/confirmation-status/", auth_views.confirmation_status, name="confirmation_status"),
    path(
        "accounts/resend-confirmation/",
        auth_views.resend_confirmation,
        name="resend_confirmation",
    ),
    path("accounts/profile/postcode/", auth_views.update_postcode, name="update_postcode"),
    path(
        "accounts/profile/change/<str:token>/",
        auth_views.confirm_profile_change,
        name="confirm_profile_change",
    ),
    path("accounts/notifications/", auth_views.notifications_page, name="notifications"),
    path("notifications/mark-all-read/", auth_views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("notifications/<int:notification_id>/mark-read/", auth_views.mark_notification_read, name="mark_notification_read"),
    path(
        "accounts/notifications/dismiss/<int:notification_id>/",
        auth_views.dismiss_notification,
        name="dismiss_notification",
    ),
    # Show information about the logged in user.
    path("accounts/profile/", auth_views.profile_view, name="profile"),
    # Email change modal endpoint
    path("accounts/profile/change-email/", auth_views.change_email_modal, name="change_email_modal"),
    # Email change status endpoint
    path("api/email-change-status/", email_status_views.email_change_status, name="email_change_status"),
    # User preferences management
    path("accounts/preferences/", auth_views.user_preferences_view, name="user_preferences"),
    path("api/preferences/", api_views.user_preferences_ajax, name="user_preferences_ajax"),
    # Enhanced auth functionality
    path("accounts/logout/", auth_views.logout_view, name="logout_enhanced"),
    path("accounts/password-reset/", auth_views.password_reset_view, name="password_reset_enhanced"),
    path("accounts/delete-account/", auth_views.account_deletion_view, name="account_deletion"),
    path("accounts/social-accounts/", auth_views.social_account_linking_view, name="social_accounts"),
    path("councils/", council_views.council_list, name="council_list"),
    path(
        "councils/<slug:slug>/counters/",
        council_views.council_counters,
        name="council_counters",
    ),
    path(
        "councils/<slug:slug>/share/",
        council_views.generate_share_link,
        name="generate_share_link",
    ),
    # Legacy edit-table removed - using React edit interface only
    # API endpoints for spreadsheet interface
    path(
        "councils/<slug:slug>/financial-data/",
        council_views.financial_data_api,
        name="financial_data_api",
    ),
    path(
        "api/fields/<slug:field_slug>/options/",
        council_views.field_options_api,
        name="field_options_api",
    ),
    path(
        "api/council/contribute/",
        council_views.contribute_api,
        name="contribute_api",
    ),
    path(
        "councils/<slug:slug>/log/",
        council_views.council_change_log,
        name="council_change_log",
    ),
    path("councils/<slug:slug>/", general_views.council_detail, name="council_detail"),
    # Common menu pages
    path("leaderboards/", general_views.leaderboards, name="leaderboards"),
    path("lists/", my_lists, name="my_lists"),
    path("lists/create/", general_views.create_list_api, name="create_list_api"),
    path("lists/favourites/add/", add_favourite, name="add_favourite"),
    path("lists/favourites/remove/", remove_favourite, name="remove_favourite"),
    path("lists/<int:list_id>/add/", add_to_list, name="add_to_list_api"),
    path("lists/<int:list_id>/remove/", remove_from_list, name="remove_from_list_api"),
    path("lists/move/", move_between_lists, name="move_between_lists"),
    path("lists/<int:list_id>/metric/", list_metric, name="list_metric"),
    path("compare/add/<slug:slug>/", add_to_compare, name="add_to_compare"),
    path("compare/remove/<slug:slug>/", remove_from_compare, name="remove_from_compare"),
    path("compare/row/", compare_row, name="compare_row"),
    path("compare/clear/", clear_compare_basket, name="clear_compare_basket"),
    path("compare/detailed/", detailed_comparison, name="detailed_comparison"),
    
    # ============================================================================
    # NEW REACT COMPARISON BASKET API ENDPOINTS
    # ============================================================================
    
    # Main React-based comparison basket page (replaces legacy system)
    path("compare/", comparison_api.ComparisonBasketView.as_view(), name="compare_basket"),
    
    # API endpoints for React comparison basket
    path("api/comparison/basket/", comparison_api.get_basket_data, name="comparison_basket_api"),
    path("api/comparison/fields/", comparison_api.get_available_fields, name="comparison_fields_api"),
    path("api/comparison/years/", comparison_api.get_available_years, name="comparison_years_api"),
    path("api/comparison/data/", comparison_api.get_comparison_data, name="comparison_data_api"),
    path("api/comparison/export/", comparison_api.export_comparison_data, name="comparison_export_api"),
    path("following/", following, name="following"),
    # Enhanced Following System API Endpoints
    path("following/api/follow/", follow_item_api, name="follow_item_api"),
    path("following/api/unfollow/", unfollow_item_api, name="unfollow_item_api"),
    path("following/api/updates/<int:update_id>/interact/", interact_with_update_api, name="interact_with_update_api"),
    path("following/api/updates/<int:update_id>/comment/", comment_on_update_api, name="comment_on_update_api"),
    path("following/api/preferences/", update_feed_preferences_api, name="update_feed_preferences_api"),
    path("following/api/updates/", get_feed_updates_api, name="get_feed_updates_api"),
    # ActivityLog Comment API Endpoints
    path("following/api/activity-log/<int:activity_log_id>/comment/", comment_on_activity_log, name="comment_on_activity_log"),
    path("following/api/activity-log/<int:activity_log_id>/comments/", get_activity_log_comments, name="get_activity_log_comments"),
    path("following/api/comment/<int:comment_id>/like/", like_activity_log_comment, name="like_activity_log_comment"),
    # Legacy Following URLs (for backward compatibility)
    path("follow/<slug:slug>/", follow_council, name="follow_council"),
    path("unfollow/<slug:slug>/", unfollow_council, name="unfollow_council"),
    path("updates/<int:update_id>/like/", like_update, name="like_update"),
    path("updates/<int:update_id>/comment/", comment_update, name="comment_update"),
    
    # CONTRIBUTE SYSTEM DISABLED - Replaced with enhanced flagging system
    # Users should now use council edit pages and flag data issues instead
    # Redirect to info page about the new system
    path("contribute/", page_views.contribute_redirect, name="contribute_redirect"),
    # Enhanced editing API endpoints
    path("api/field/<slug:field_slug>/info/", api_views.field_info_api, name="field_info_api"),
    path("api/validate-url/", api_views.validate_url_api, name="validate_url_api"),
    path("api/field/<slug:field_slug>/options/", api_views.list_field_options, name="field_options_api"),
    path("api/council/<slug:council_slug>/recent-activity/", api_views.council_recent_activity_api, name="council_recent_activity_api"),
    path("api/council/<slug:council_slug>/recent-activity/<slug:field_slug>/", api_views.field_recent_activity_api, name="field_recent_activity_api"),
    
    # ============================================================================
    # COUNCIL EDIT REACT API ENDPOINTS
    # ============================================================================
    
    # Council characteristics (non-temporal data)
    path("api/council/<slug:council_slug>/characteristics/", council_edit_api.council_characteristics_api, name="council_characteristics_api"),
    path("api/council/<slug:council_slug>/characteristics/save/", council_edit_api.save_council_characteristic_api, name="save_council_characteristic_api"),
    
    # Temporal data (general + financial by year)
    path("api/council/<slug:council_slug>/temporal/<int:year_id>/", council_edit_api.council_temporal_data_api, name="council_temporal_data_api"),
    path("api/council/<slug:council_slug>/temporal/<int:year_id>/save/", council_edit_api.save_temporal_data_api, name="save_temporal_data_api"),
    
    # Available years and context
    path("api/council/<slug:council_slug>/years/", council_edit_api.council_available_years_api, name="council_available_years_api"), 
    path("api/council/<slug:council_slug>/edit-context/", council_edit_api.council_edit_context_api, name="council_edit_context_api"),
    
    # React council edit interface (no fallback)
    path("councils/<slug:slug>/edit/", council_views.council_edit_react, name="council_edit"),
    
    # ============================================================================
    # REACT FACTOID BUILDER API ENDPOINTS
    # ============================================================================
    
    # Field discovery for React factoid builder
    path("api/factoid-builder/fields/", factoid_builder_api.available_fields_api, name="factoid_builder_fields"),
    path("api/factoid-builder/fields/<slug:council_slug>/", factoid_builder_api.available_fields_api, name="factoid_builder_fields_council"),
    
    # Live preview for React factoid builder
    path("api/factoid-builder/preview/", factoid_builder_api.preview_factoid_api, name="factoid_builder_preview"),
    
    # ============================================================================
    # AI FACTOIDS API ENDPOINTS (NEW SYSTEM)
    # ============================================================================
    
    # AI-generated council factoids (replaces counter-based system)
    path("api/factoids/ai/<slug:council_slug>/", ai_council_factoids, name="ai_council_factoids"),
    path("api/factoids/ai/batch/", ai_batch_factoids, name="ai_batch_factoids"),
    path("api/factoids/ai/<slug:council_slug>/cache/", clear_ai_factoid_cache, name="clear_ai_factoid_cache"),
    path("api/factoids/ai/status/", ai_factoid_status, name="ai_factoid_status"),
    
    # Site-wide cross-council factoids for homepage
    path("api/factoids/sitewide/", get_sitewide_factoids, name="sitewide_factoids"),
    path("api/factoids/sitewide/health/", get_sitewide_factoids_health, name="sitewide_factoids_health"),
    path("api/factoids/sitewide/legacy/", sitewide_factoids_view, name="sitewide_factoids_legacy"),
    
    # Leaderboard API endpoints
    path("api/leaderboards/", get_leaderboard, name="api_leaderboards"),
    path("api/leaderboards/categories/", get_categories, name="api_leaderboard_categories"),
    path("api/leaderboards/legacy/", leaderboard_view, name="leaderboard_legacy_api"),
    path("api/leaderboards/<str:category>/", get_leaderboard, name="api_leaderboard_category"),
    path("api/councils/<slug:council_slug>/rankings/", get_council_rankings, name="api_council_rankings"),
    
    # ============================================================================
    # LEGACY FACTOID API ENDPOINTS (DEPRECATED)
    # ============================================================================
    
    # Enhanced Factoid API (new real-time system)
    path("api/factoid/", include("council_finance.api.factoid_urls")),
    # Factoids for counter API (frontend expects this pattern) - MUST come before template pattern
    path("api/factoids/counter/<slug:counter_slug>/<slug:council_slug>/<str:year_slug>/", 
         get_factoids_for_counter_frontend, 
         name="factoids_for_counter_frontend"),
    # Factoid instance API (different namespace for individual factoid instances)
    path("api/factoids/<slug:template_slug>/<slug:council_slug>/<str:year_slug>/", 
         factoid_instance_api, 
         name="factoid_instance_api"),
    
    # ============================================================================
    # AI FACTOID MANAGEMENT INTERFACE (REPLACES OLD FACTOID BUILDER)
    # ============================================================================
    
    # AI Factoid Management Dashboard (replaces /factoid-builder/)
    path("factoid-builder/", ai_factoid_management_dashboard, name="ai_factoid_management_dashboard"),
    path("ai-factoids/", ai_factoid_management_dashboard, name="ai_factoid_management_dashboard"),
    path("ai-factoids/inspect/<slug:council_slug>/", council_ai_data_inspector, name="council_ai_data_inspector"),
    path("ai-factoids/test-generation/", test_ai_generation, name="test_ai_generation"),
    path("ai-factoids/clear-cache/", clear_factoid_cache, name="clear_factoid_cache"),
    path("ai-factoids/warmup-cache/", warmup_council_cache, name="warmup_council_cache"),
    path("ai-factoids/financial-data/<slug:council_slug>/", council_financial_data_viewer, name="council_financial_data_viewer"),
    path("ai-factoids/configuration/", ai_configuration, name="ai_factoid_configuration"),
    
    # Site-wide factoid inspector
    path("ai-factoids/sitewide/", sitewide_factoid_inspector, name="sitewide_factoid_inspector"),
    path("ai-factoids/sitewide/test-generation/", test_sitewide_generation, name="test_sitewide_generation"),
    path("ai-factoids/sitewide/clear-cache/", clear_sitewide_cache, name="clear_sitewide_cache"),
    
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
    
    # Legacy AI Analysis endpoints removed - now using AI factoids instead
    path("api/ai-providers/<int:provider_id>/models/", api_views.provider_models_api, name="provider_models_api"),
    
    # CONTRIBUTE SYSTEM URLS DISABLED - Replaced with enhanced flagging system
    # path("contribute/data-issues-table/", contrib_views.data_issues_table, name="data_issues_table"),
    # path("contribute/stats/", contrib_views.contribute_stats, name="contribute_stats"),
    # path("contribute/submit/", contrib_views.contribute_submit, name="submit_contribution"),
    # path("contribute/field-options/<slug:slug>/", api_views.list_field_options, name="contribute_field_options"),
    # path("contribute/<int:pk>/<str:action>/", contrib_views.review_contribution, name="review_contribution"),
    # path("contribute/mod-panel/", contrib_views.moderator_panel, name="moderator_panel"),
    
    path("fields/<slug:slug>/options/", api_views.list_field_options, name="list_field_options"),
    # Flagging system
    path("ajax/flag-content/", mod_views.flag_content, name="flag_content"),
    path("moderation/flagged-content/", mod_views.flagged_content_list, name="flagged_content_list"),
    path("ajax/resolve-flag/<int:flag_id>/", mod_views.resolve_flag, name="resolve_flag"),
    path("ajax/content-action/<int:flagged_content_id>/", mod_views.take_content_action, name="take_content_action"),
    path("ajax/user-action/<int:user_id>/", mod_views.take_user_action, name="take_user_action"),
    path("my-flags/", mod_views.my_flags, name="my_flags"),
    # CONTRIBUTE SYSTEM DISABLED - Use council edit pages and flagging instead
    # path("submit/", contrib_views.contribute),
    path("profile/", auth_views.my_profile, name="my_profile"),
    path("about/", page_views.about, name="about"),
    path("terms/", page_views.terms_of_use, name="terms_of_use"),
    path("privacy/", page_views.privacy_cookies, name="privacy_cookies"),
    
    # Site feedback system for pre-alpha testing
    path("feedback/", feedback_views.feedback_form, name="feedback_form"),
    path("feedback/thank-you/", feedback_views.feedback_thank_you, name="feedback_thank_you"),
    # Management views for counters
    path("manage/counters/", admin_views.counter_definition_list, name="counter_definitions"),
    path("manage/counters/site/", admin_views.site_counter_list, name="site_counter_list"),
    path("manage/counters/site/add/", admin_views.site_counter_form, name="site_counter_add"),
    path("manage/counters/site/<slug:slug>/", admin_views.site_counter_form, name="site_counter_edit"),
    path("manage/counters/site/<slug:slug>/delete/", admin_views.site_counter_delete, name="site_counter_delete"),
    path("manage/counters/groups/", admin_views.group_counter_list, name="group_counter_list"),
    path("manage/counters/groups/add/", admin_views.group_counter_form, name="group_counter_add"),
    path("manage/counters/groups/<slug:slug>/", admin_views.group_counter_form, name="group_counter_edit"),
    path("manage/counters/groups/<slug:slug>/delete/", admin_views.group_counter_delete, name="group_counter_delete"),
    path("manage/counters/add/", admin_views.counter_definition_form, name="counter_add"),
    # The preview endpoint must appear before the dynamic slug path so Django
    # doesn't interpret "preview" as a slug. Without this ordering a request to
    # "/manage/counters/preview/" would be routed to the counter edit view and
    # return a 404 if no counter actually has the slug "preview".
    path(
        "manage/counters/preview/",
        admin_views.preview_counter_value,
        name="preview_counter_value",
    ),
    path(
        "manage/counters/preview-aggregate/",
        admin_views.preview_aggregate_counter,
        name="preview_aggregate_counter",
    ),
    path(
        "manage/counters/<slug:slug>/delete/",
        admin_views.counter_delete,
        name="counter_delete",
    ),
    path(
        "manage/counters/<slug:slug>/",
        admin_views.counter_definition_form,
        name="counter_edit",
    ),
    path(
        "manage/counters/<slug:slug>/factoids/",
        admin_views.counter_factoid_assignment,
        name="counter_factoid_assignment",
    ),
    # TEST URL to confirm our Django instance is responding
    path("manage/TEST-NUCLEAR-URL/", lambda request: HttpResponse('<h1 style="color:red;background:yellow;font-size:48px;">NUCLEAR URL TEST SUCCESS</h1>'), name="nuclear_test"),
    
    path("god-mode/", admin_views.god_mode, name="god_mode"),
    path("god-mode/activity-log/", admin_views.activity_log_entries, name="activity_log_entries"),
    path("god-mode/activity-log/<int:log_id>/json/", admin_views.activity_log_json, name="activity_log_json"),
    
    # Council Management under God Mode
    path("god-mode/councils/", council_mgmt_views.council_management_dashboard, name="council_management_dashboard"),
    path("god-mode/councils/create/", council_mgmt_views.create_council, name="create_council"),
    path("god-mode/councils/<int:council_id>/edit/", council_mgmt_views.edit_council, name="edit_council"),
    path("god-mode/councils/<int:council_id>/delete/", council_mgmt_views.delete_council, name="delete_council"),
    path("god-mode/councils/import/", council_mgmt_views.import_page, name="import_councils"),
    path("god-mode/councils/bulk-import/", council_mgmt_views.bulk_import, name="bulk_import_councils"),
    path("god-mode/councils/cancel-import/", council_mgmt_views.cancel_import, name="cancel_import"),
    
    # AI Management under God Mode
    path("god-mode/ai/", admin_views.ai_management_dashboard, name="ai_management_dashboard"),
    path("god-mode/ai/models/add/", admin_views.ai_model_form, name="ai_model_add"),
    path("god-mode/ai/models/<int:model_id>/", admin_views.ai_model_form, name="ai_model_edit"),
    path("god-mode/ai/templates/add/", admin_views.ai_template_form, name="ai_template_add"),
    path("god-mode/ai/templates/<int:template_id>/", admin_views.ai_template_form, name="ai_template_edit"),
    path("god-mode/ai/configurations/add/", admin_views.ai_configuration_form, name="ai_configuration_add"),
    path("god-mode/ai/configurations/<int:config_id>/", admin_views.ai_configuration_form, name="ai_configuration_edit"),
    path("god-mode/ai/analysis/<int:analysis_id>/", admin_views.ai_analysis_detail, name="ai_analysis_detail"),
    
    # Field Management
    path("manage/fields/", admin_views.field_list, name="field_list"),
    path("manage/fields/add/", admin_views.field_form_view, name="field_add"),
    path("manage/fields/<int:field_id>/edit/", admin_views.field_form_view, name="field_edit"),
    path("manage/fields/<int:field_id>/delete/", admin_views.field_delete_view, name="field_delete"),
    
    # Formula Validation and Testing APIs
    path("api/fields/validate-formula/", admin_views.validate_formula_api, name="validate_formula_api"),
    path("api/fields/test-formula/", admin_views.test_formula_api, name="test_formula_api"),
    # CONTRIBUTE SYSTEM DISABLED - Use enhanced flagging system instead
    # path("contribute/issue/<int:issue_id>/mark-invalid/", contrib_views.mark_issue_invalid, name="mark_issue_invalid"),
    
    # Include new data architecture URLs (commented out - file doesn't exist)
    # path("", include("council_finance.urls_v2")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
