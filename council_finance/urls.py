from django.contrib import admin
from django.urls import path, include
# Import Django's built-in authentication views so we can easily
# provide login and logout functionality.
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('plugins/', include('core.urls')),
    # Authentication endpoints for administrators and visitors.
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
    # Show information about the logged in user.
    path('accounts/profile/', views.profile_view, name='profile'),
    path('councils/', views.council_list, name='council_list'),
    path('councils/<slug:slug>/', views.council_detail, name='council_detail'),
]
