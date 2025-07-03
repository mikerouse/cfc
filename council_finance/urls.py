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
    path("councils/", views.council_list, name="council_list"),
    path(
        "councils/<slug:slug>/counters/",
        views.council_counters,
        name="council_counters",
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
    path("following/", views.following, name="following"),
    path("submit/", views.submit, name="submit"),
    path("profile/", views.my_profile, name="my_profile"),
    path("about/", views.about, name="about"),
    path("terms/", views.terms_of_use, name="terms_of_use"),
    path("privacy/", views.privacy_cookies, name="privacy_cookies"),
    path("corrections/", views.corrections, name="corrections"),
    # Staff-only views for managing counters
    path("staff/counters/", views.counter_definition_list, name="counter_definitions"),
    path("staff/counters/add/", views.counter_definition_form, name="counter_add"),
    # The preview endpoint must appear before the dynamic slug path so Django
    # doesn't interpret "preview" as a slug. Without this ordering a request to
    # "/staff/counters/preview/" would be routed to the counter edit view and
    # return a 404 if no counter actually has the slug "preview".
    path(
        "staff/counters/preview/",
        views.preview_counter_value,
        name="preview_counter_value",
    ),
    path(
        "staff/counters/<slug:slug>/",
        views.counter_definition_form,
        name="counter_edit",
    ),
    # Staff views for managing fields
    path("staff/fields/", views.field_list, name="field_list"),
    path("staff/fields/add/", views.field_form, name="field_add"),
    path("staff/fields/<slug:slug>/", views.field_form, name="field_edit"),
    path("staff/fields/<slug:slug>/delete/", views.field_delete, name="field_delete"),
]
