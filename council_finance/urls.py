from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.contrib import admin

from .views import (
    general as general_views,
    contributions as contrib_views,
    admin as admin_views,
    api as api_views,
    auth as auth_views,
    moderation as mod_views,
    councils as council_views,
    pages as page_views,
    council_management as council_mgmt_views,
    email_status as email_status_views,
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
)

urlpatterns = [
    # Favicon redirect to avoid 404 errors
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico', permanent=True)),
    
    path("", general_views.home, name="home"),
    path("search/", general_views.search_results, name="search_results"),
    path("api/councils/search/", api_views.search_councils, name="search_councils"),
    path("admin/", admin.site.urls),
    path("plugins/", include("core.urls")),
    # Authentication endpoints
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
    path(
        "councils/<slug:slug>/edit-table/",
        council_views.edit_figures_table,
        name="edit_figures_table",
    ),
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
    path("compare/", compare_basket, name="compare_basket"),
    path("following/", following, name="following"),
    # Enhanced Following System API Endpoints
    path("following/api/follow/", follow_item_api, name="follow_item_api"),
    path("following/api/unfollow/", unfollow_item_api, name="unfollow_item_api"),
    path("following/api/updates/<int:update_id>/interact/", interact_with_update_api, name="interact_with_update_api"),
    path("following/api/updates/<int:update_id>/comment/", comment_on_update_api, name="comment_on_update_api"),
    path("following/api/preferences/", update_feed_preferences_api, name="update_feed_preferences_api"),
    path("following/api/updates/", get_feed_updates_api, name="get_feed_updates_api"),
    # Legacy Following URLs (for backward compatibility)
    path("follow/<slug:slug>/", follow_council, name="follow_council"),
    path("unfollow/<slug:slug>/", unfollow_council, name="unfollow_council"),
    path("updates/<int:update_id>/like/", like_update, name="like_update"),
    path("updates/<int:update_id>/comment/", comment_update, name="comment_update"),
    path("contribute/", contrib_views.contribute, name="contribute"),
    # Enhanced editing API endpoints
    path("api/field/<slug:field_slug>/info/", api_views.field_info_api, name="field_info_api"),
    path("api/field/<slug:field_slug>/options/", api_views.list_field_options, name="field_options_api"),
    path("api/council/<slug:council_slug>/recent-activity/", api_views.council_recent_activity_api, name="council_recent_activity_api"),
    path("api/council/<slug:council_slug>/recent-activity/<slug:field_slug>/", api_views.field_recent_activity_api, name="field_recent_activity_api"),
    
    # Factoid API endpoints
    path("api/factoids/<slug:counter_slug>/<slug:council_slug>/<str:year_label>/", api_views.factoid_data_api, name="factoid_data_api"),
    path("api/factoid-playlists/<slug:counter_slug>/", api_views.factoid_playlist_api, name="factoid_playlist_api"),
    path("api/factoid-playlists/<int:playlist_id>/regenerate/", api_views.regenerate_factoid_playlist_api, name="regenerate_factoid_playlist_api"),
    path("api/factoid-templates/<slug:template_slug>/preview/", api_views.factoid_template_preview_api, name="factoid_template_preview_api"),
    
    # AI Analysis API endpoints
    path("api/ai-analysis/<slug:council_slug>/<str:year_label>/", api_views.council_ai_analysis_api, name="council_ai_analysis_api"),
    path("api/ai-analysis/status/<int:analysis_id>/", api_views.ai_analysis_status_api, name="ai_analysis_status_api"),
    path("api/ai-providers/<int:provider_id>/models/", api_views.provider_models_api, name="provider_models_api"),
    path("contribute/data-issues-table/", contrib_views.data_issues_table, name="data_issues_table"),
    path("contribute/stats/", contrib_views.contribute_stats, name="contribute_stats"),
    path("contribute/submit/", contrib_views.contribute_submit, name="submit_contribution"),
    path("contribute/field-options/<slug:slug>/", api_views.list_field_options, name="contribute_field_options"),
    path("fields/<slug:slug>/options/", api_views.list_field_options, name="list_field_options"),
    path("contribute/<int:pk>/<str:action>/", contrib_views.review_contribution, name="review_contribution"),
    path("contribute/mod-panel/", contrib_views.moderator_panel, name="moderator_panel"),
    # Flagging system
    path("ajax/flag-content/", mod_views.flag_content, name="flag_content"),
    path("moderation/flagged-content/", mod_views.flagged_content_list, name="flagged_content_list"),
    path("ajax/resolve-flag/<int:flag_id>/", mod_views.resolve_flag, name="resolve_flag"),
    path("ajax/content-action/<int:flagged_content_id>/", mod_views.take_content_action, name="take_content_action"),
    path("ajax/user-action/<int:user_id>/", mod_views.take_user_action, name="take_user_action"),
    path("my-flags/", mod_views.my_flags, name="my_flags"),
    path("submit/", contrib_views.contribute),
    path("profile/", auth_views.my_profile, name="my_profile"),
    path("about/", page_views.about, name="about"),
    path("terms/", page_views.terms_of_use, name="terms_of_use"),
    path("privacy/", page_views.privacy_cookies, name="privacy_cookies"),
    path("corrections/", page_views.corrections, name="corrections"),
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
    # Management views for fields
    path("manage/fields/", admin_views.field_list, name="field_list"),
    path("manage/fields/add/", admin_views.field_form, name="field_add"),
    path("manage/fields/<slug:slug>/", admin_views.field_form, name="field_edit"),
    path("manage/fields/<slug:slug>/delete/", admin_views.field_delete, name="field_delete"),
    # TEST URL to confirm our Django instance is responding
    path("manage/TEST-NUCLEAR-URL/", lambda request: HttpResponse('<h1 style="color:red;background:yellow;font-size:48px;">NUCLEAR URL TEST SUCCESS</h1>'), name="nuclear_test"),
    
    # Enhanced factoid template management
    path("manage/factoid-templates/", admin_views.factoid_template_list, name="factoid_template_list"),
    path("manage/factoid-templates/add/", admin_views.factoid_template_form, name="factoid_template_add"),
    path("manage/factoid-templates/<slug:slug>/", admin_views.factoid_template_form, name="factoid_template_edit"),
    path("manage/factoid-templates/<slug:slug>/delete/", admin_views.factoid_template_delete, name="factoid_template_delete"),
    
    # Factoid playlist management
    path("manage/factoid-playlists/", admin_views.factoid_playlist_list, name="factoid_playlist_list"),
    path("manage/factoid-playlists/<int:playlist_id>/regenerate/", admin_views.factoid_playlist_regenerate, name="factoid_playlist_regenerate"),
    
    # Legacy factoid management (backward compatibility)
    path("manage/factoids/", admin_views.factoid_list, name="factoid_list"),
    path("manage/factoids/add/", admin_views.factoid_form, name="factoid_add"),
    path("manage/factoids/preview/", admin_views.preview_factoid, name="preview_factoid"),
    path("manage/factoids/<slug:slug>/", admin_views.factoid_form, name="factoid_edit"),
    path(
        "manage/factoids/<slug:slug>/delete/",
        admin_views.factoid_delete,
        name="factoid_delete",
    ),
    
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
    path("contribute/issue/<int:issue_id>/mark-invalid/", contrib_views.mark_issue_invalid, name="mark_issue_invalid"),
    
    # Include new data architecture URLs (commented out - file doesn't exist)
    # path("", include("council_finance.urls_v2")),
]
