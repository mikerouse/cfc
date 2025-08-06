from django.apps import AppConfig

class CouncilFinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'council_finance'
    verbose_name = 'Council Finance'

    def ready(self):
        # Ensure model signals are registered when the app loads.
        from . import signals  # noqa: F401
        
        # Import factoid signals for real-time updates
        try:
            from .signals import factoid_signals  # noqa: F401
        except ImportError:
            pass
        
        # Import counter cache invalidation signals
        try:
            from .services import counter_invalidation_service  # noqa: F401
        except ImportError:
            pass
