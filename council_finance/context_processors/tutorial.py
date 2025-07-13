"""
Django context processor for tutorial engine.

This makes tutorial configuration available to all templates
without needing to pass it explicitly in every view.
"""

from .tutorial_engine import tutorial_engine


def tutorial_context(request):
    """
    Add tutorial engine context to all template renders.
    
    This context processor makes the tutorial engine available
    in templates as 'tutorial_engine'.
    """
    return {
        'tutorial_engine': tutorial_engine,
        'debug_tutorials': tutorial_engine.debug_mode or tutorial_engine.force_debug_tutorials,
    }
