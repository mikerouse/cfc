from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def unread_count(context):
    user = context['user']
    if user.is_authenticated:
        return user.notifications.filter(read=False).count()
    return 0


@register.simple_tag(takes_context=True)
def recent_notifications(context, limit=5):
    """Return the latest notifications for the current user."""
    user = context['user']
    if user.is_authenticated:
        return user.notifications.order_by('-created')[:limit]
    return []
