from django import template

# Register a new template library instance for custom filters.
register = template.Library()

@register.filter
def get_item(obj, key):
    """Return ``obj[key]`` safely when ``obj`` is a dict."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None
