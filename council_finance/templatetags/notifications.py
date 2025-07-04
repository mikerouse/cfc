from django import template
from django.db.utils import OperationalError

register = template.Library()

@register.simple_tag(takes_context=True)
def unread_count(context):
    user = context['user']
    if user.is_authenticated:
        try:
            # Gracefully handle cases where migrations haven't been run yet.
            return user.notifications.filter(read=False).count()
        except OperationalError:
            # Notification table missing - return zero so the site still works.
            return 0
    return 0


@register.simple_tag(takes_context=True)
def recent_notifications(context, limit=5):
    """Return the latest notifications for the current user."""
    user = context['user']
    if user.is_authenticated:
        try:
            return user.notifications.order_by('-created')[:limit]
        except OperationalError:
            # Table missing - return empty list to avoid runtime errors
            return []
    return []


@register.simple_tag(takes_context=True)
def profile_progress(context):
    """Return completion percentage for the logged in user's profile."""
    user = context["user"]
    if user.is_authenticated and hasattr(user, "profile"):
        try:
            return user.profile.completion_percent()
        except OperationalError:
            return 0
    return 0
