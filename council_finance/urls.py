from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/councils/search/", views.search_councils, name="search_councils"),
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
    path("accounts/signup/", views.signup_view, name="signup"),
    path("accounts/confirm/<str:token>/", views.confirm_email, name="confirm_email"),
    path(
        "accounts/resend-confirmation/",
        views.resend_confirmation,
        name="resend_confirmation",
    ),
    path("accounts/profile/postcode/", views.update_postcode, name="update_postcode"),
    path(
        "accounts/profile/change/<str:token>/",
        views.confirm_profile_change,
        name="confirm_profile_change",
    ),
    path("accounts/notifications/", views.notifications_page, name="notifications"),
    path(
        "accounts/notifications/dismiss/<int:notification_id>/",
        views.dismiss_notification,
        name="dismiss_notification",
    ),
    # Show information about the logged in user.
    path("accounts/profile/", views.profile_view, name="profile"),
    # User preferences management
    path("accounts/preferences/", views.user_preferences_view, name="user_preferences"),
    path("api/preferences/", views.user_preferences_ajax, name="user_preferences_ajax"),
    path("councils/", views.council_list, name="council_list"),
    path(
        "councils/<slug:slug>/counters/",
        views.council_counters,
        name="council_counters",
    ),
    path(
        "councils/<slug:slug>/share/",
        views.generate_share_link,
        name="generate_share_link",
    ),
    path(
        "councils/<slug:slug>/edit-table/",
        views.edit_figures_table,
        name="edit_figures_table",
    ),
    path(
        "councils/<slug:slug>/log/",
        views.council_change_log,
        name="council_change_log",
    ),
    path("councils/<slug:slug>/", views.council_detail, name="council_detail"),
    # Common menu pages
    path("leaderboards/", views.leaderboards, name="leaderboards"),
    path("lists/", views.my_lists, name="my_lists"),
    path("lists/favourites/add/", views.add_favourite, name="add_favourite"),
    path("lists/favourites/remove/", views.remove_favourite, name="remove_favourite"),
    path("lists/<int:list_id>/add/", views.add_to_list, name="add_to_list_api"),
    path("lists/<int:list_id>/remove/", views.remove_from_list, name="remove_from_list_api"),
    path("lists/move/", views.move_between_lists, name="move_between_lists"),
    path("lists/<int:list_id>/metric/", views.list_metric, name="list_metric"),
    path("compare/add/<slug:slug>/", views.add_to_compare, name="add_to_compare"),
    path("compare/remove/<slug:slug>/", views.remove_from_compare, name="remove_from_compare"),
    path("compare/row/", views.compare_row, name="compare_row"),
    path("compare/", views.compare_basket, name="compare_basket"),
    path("following/", views.following, name="following"),
    path("follow/<slug:slug>/", views.follow_council, name="follow_council"),
    path("unfollow/<slug:slug>/", views.unfollow_council, name="unfollow_council"),
    path("updates/<int:update_id>/like/", views.like_update, name="like_update"),
    path("updates/<int:update_id>/comment/", views.comment_update, name="comment_update"),
    path("contribute/", views.contribute, name="contribute"),
    path("contribute/api/data/", views.contribute_api_data, name="contribute_api_data"),
    path("contribute/api/stats/", views.contribute_api_stats, name="contribute_api_stats"),
    path("contribute/issues/", views.data_issues_table, name="data_issues_table"),
    path("contribute/stats/", views.contribute_stats, name="contribute_stats"),
    path("contribute/submit/", views.submit_contribution, name="submit_contribution"),
    path("contribute/field-options/<slug:slug>/", views.list_field_options, name="contribute_field_options"),
    path("fields/<slug:slug>/options/", views.list_field_options, name="list_field_options"),
    path("contribute/<int:pk>/<str:action>/", views.review_contribution, name="review_contribution"),
    path("contribute/mod-panel/", views.moderator_panel, name="moderator_panel"),
    path("submit/", views.contribute),
    path("profile/", views.my_profile, name="my_profile"),
    path("about/", views.about, name="about"),
    path("terms/", views.terms_of_use, name="terms_of_use"),
    path("privacy/", views.privacy_cookies, name="privacy_cookies"),
    path("corrections/", views.corrections, name="corrections"),
    # Management views for counters
    path("manage/counters/", views.counter_definition_list, name="counter_definitions"),
    path("manage/counters/site/", views.site_counter_list, name="site_counter_list"),
    path("manage/counters/site/add/", views.site_counter_form, name="site_counter_add"),
    path("manage/counters/site/<slug:slug>/", views.site_counter_form, name="site_counter_edit"),
    path("manage/counters/groups/", views.group_counter_list, name="group_counter_list"),
    path("manage/counters/groups/add/", views.group_counter_form, name="group_counter_add"),
    path("manage/counters/groups/<slug:slug>/", views.group_counter_form, name="group_counter_edit"),
    path("manage/counters/add/", views.counter_definition_form, name="counter_add"),
    # The preview endpoint must appear before the dynamic slug path so Django
    # doesn't interpret "preview" as a slug. Without this ordering a request to
    # "/manage/counters/preview/" would be routed to the counter edit view and
    # return a 404 if no counter actually has the slug "preview".
    path(
        "manage/counters/preview/",
        views.preview_counter_value,
        name="preview_counter_value",
    ),
    path(
        "manage/counters/preview-aggregate/",
        views.preview_aggregate_counter,
        name="preview_aggregate_counter",
    ),
    path(
        "manage/counters/<slug:slug>/",
        views.counter_definition_form,
        name="counter_edit",
    ),
    # Management views for fields
    path("manage/fields/", views.field_list, name="field_list"),
    path("manage/fields/add/", views.field_form, name="field_add"),
    path("manage/fields/<slug:slug>/", views.field_form, name="field_edit"),
    path("manage/fields/<slug:slug>/delete/", views.field_delete, name="field_delete"),
    path("manage/factoids/", views.factoid_list, name="factoid_list"),
    path("manage/factoids/add/", views.factoid_form, name="factoid_add"),
    path("manage/factoids/preview/", views.preview_factoid, name="preview_factoid"),
    path("manage/factoids/<slug:slug>/", views.factoid_form, name="factoid_edit"),
    path(
        "manage/factoids/<slug:slug>/delete/",
        views.factoid_delete,
        name="factoid_delete",
    ),
    path("god-mode/", views.god_mode, name="god_mode"),
    path("god-mode/activity-log/", views.activity_log_entries, name="activity_log_entries"),
    path("contribute/issue/<int:issue_id>/mark-invalid/", views.mark_issue_invalid, name="mark_issue_invalid"),
]
