from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('plugins/', include('core.urls')),
    # Authentication endpoints
    path('accounts/login/',
         LoginView.as_view(template_name='registration/login.html'),
         name='login'),
    path('accounts/logout/',
         LogoutView.as_view(template_name='registration/logged_out.html'),
         name='logout'),
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
