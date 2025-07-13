"""
Template tags for the tutorial engine.
"""

import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def tutorial_config(engine, tutorial_id):
    """
    Get tutorial configuration as JSON for a specific tutorial ID.
    
    Usage in templates:
    {{ tutorial_engine|tutorial_config:'contribute' }}
    """
    config = engine.get_tutorial_javascript(tutorial_id)
    return mark_safe(json.dumps(config))
