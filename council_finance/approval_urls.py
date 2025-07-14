"""
Direct URL patterns for the contribution approval fix.
Add this to the main urls.py temporarily.
"""

from django.urls import path
from council_finance.approval_fix import approve_contribution_direct, reject_contribution_direct

# Add these patterns to the main urlpatterns list:
approval_fix_patterns = [
    path('contribute/approve_direct/<int:contribution_id>/', approve_contribution_direct, name='approve_contribution_direct'),
    path('contribute/reject_direct/<int:contribution_id>/', reject_contribution_direct, name='reject_contribution_direct'),
]
