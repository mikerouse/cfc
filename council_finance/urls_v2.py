"""
URL patterns for the new data architecture views.
These URLs handle the improved contribution system.
"""

from django.urls import path
from . import views_v2

urlpatterns = [
    # New contribution system
    path('contribute/submit_v2/', views_v2.submit_contribution_v2, name='submit_contribution_v2'),
    path('contribute/approve_v2/<int:contribution_id>/', views_v2.approve_contribution_v2, name='approve_contribution_v2'),
    path('contribute/reject_v2/<int:contribution_id>/', views_v2.reject_contribution_v2, name='reject_contribution_v2'),
    path('contribute/pending_v2/', views_v2.pending_contributions_v2, name='pending_contributions_v2'),
    path('api/council_data_v2/<int:council_id>/', views_v2.get_council_data_v2, name='get_council_data_v2'),
]
