from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    """Retrieve dictionary value by key in templates."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None
