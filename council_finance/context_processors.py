"""
Context processors for council_finance app.
Provides global template context for OSA compliance and user permissions.
"""


def user_permissions(request):
    """
    Add user permission flags to template context.
    Primarily used for OSA compliance - restricting comments/feed for users under 18.
    """
    context = {
        'can_access_comments': True,  # Default for anonymous users (they see login prompt)
        'is_minor': False,
        'osa_restricted': False,
    }
    
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        
        if profile:
            # Check if user can access comments based on age and verification
            can_access = profile.can_access_comments
            is_minor = not profile.is_adult() if profile.date_of_birth and profile.age_verified else False
            
            context.update({
                'can_access_comments': can_access,
                'is_minor': is_minor,
                'osa_restricted': is_minor and not can_access,
                'user_age': profile.age() if profile.date_of_birth else None,
                'age_verified': profile.age_verified,
            })
    
    return context