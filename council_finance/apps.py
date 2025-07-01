from django.apps import AppConfig

class CouncilFinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'council_finance'
    verbose_name = 'Council Finance'

    def ready(self):
        # Ensure model signals are registered when the app loads.
        from . import signals  # noqa: F401
