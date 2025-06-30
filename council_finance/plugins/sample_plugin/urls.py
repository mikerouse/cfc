from django.urls import path
from . import views

urlpatterns = [
    path('', views.sample_home, name='sample_home'),
]
