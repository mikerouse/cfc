from django.apps import AppConfig

class SamplePluginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'council_finance.plugins.sample_plugin'
    verbose_name = 'Sample Plugin'
