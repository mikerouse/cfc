from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/councils/search/', views.search_councils, name='search_councils'),
    path('admin/', admin.site.urls),
    path('plugins/', include('core.urls')),
    # Authentication endpoints
    path('accounts/login/',
         LoginView.as_view(template_name='registration/login.html'),
         name='login'),
    path('accounts/logout/',
         LogoutView.as_view(template_name='registration/logged_out.html'),
         name='logout'),
    path('accounts/signup/', views.signup_view, name='signup'),
    path('accounts/confirm/<str:token>/', views.confirm_email, name='confirm_email'),
    path('accounts/resend-confirmation/', views.resend_confirmation, name='resend_confirmation'),
    path('accounts/profile/postcode/', views.update_postcode, name='update_postcode'),
    path('accounts/profile/change/<str:token>/', views.confirm_profile_change, name='confirm_profile_change'),
    path('accounts/notifications/', views.notifications_page, name='notifications'),
    path('accounts/notifications/dismiss/<int:notification_id>/', views.dismiss_notification, name='dismiss_notification'),
    # Show information about the logged in user.
    path('accounts/profile/', views.profile_view, name='profile'),
    path('councils/', views.council_list, name='council_list'),
    path('councils/<slug:slug>/', views.council_detail, name='council_detail'),
    # Common menu pages
    path('leaderboards/', views.leaderboards, name='leaderboards'),
    path('lists/', views.my_lists, name='my_lists'),
    path('following/', views.following, name='following'),
    path('submit/', views.submit, name='submit'),
    path('profile/', views.my_profile, name='my_profile'),
    path('about/', views.about, name='about'),
    path('terms/', views.terms_of_use, name='terms_of_use'),
    path('privacy/', views.privacy_cookies, name='privacy_cookies'),
    path('corrections/', views.corrections, name='corrections'),
]
