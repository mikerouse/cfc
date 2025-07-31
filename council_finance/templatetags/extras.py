from django import template

# Register a new template library instance for custom filters.
register = template.Library()

@register.filter
def get_item(obj, key):
    """Return ``obj[key]`` safely when ``obj`` is a dict."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None

@register.filter
def lookup(list_obj, index):
    """Look up an item in a list by index."""
    try:
        return list_obj[int(index)]
    except (ValueError, TypeError, IndexError):
        return None
