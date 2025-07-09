import importlib
import os
import shutil
import sys
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings
from django.test import TestCase
from django.urls import include, path

django.setup()

class PluginDiscoveryTests(TestCase):
    def test_temp_plugin_view_responds(self):
        """Dynamically create a plugin and ensure its view loads."""
        plugin_name = "temp_plugin"
        module_path = f"council_finance.plugins.{plugin_name}"
        plugin_dir = Path(settings.PLUGINS_DIR) / plugin_name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal plugin files
        (plugin_dir / "__init__.py").write_text("")
        (plugin_dir / "apps.py").write_text(
            "from django.apps import AppConfig\n"
            f"class TempPluginConfig(AppConfig):\n"
            f"    name = '{module_path}'\n"
        )
        (plugin_dir / "views.py").write_text(
            "from django.http import HttpResponse\n"
            "def home(request):\n"
            "    return HttpResponse('dynamic plugin')\n"
        )
        (plugin_dir / "urls.py").write_text(
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [path('', views.home, name='home')]\n"
        )

        added_pattern = path("temp-plugin/", include(f"{module_path}.urls"))

        try:
            # Reload the app registry with the new plugin included
            apps.set_installed_apps(settings.INSTALLED_APPS + [module_path])

            from council_finance import urls
            urls.urlpatterns.append(added_pattern)

            response = self.client.get("/temp-plugin/")
            self.assertEqual(response.status_code, 200)
        finally:
            # Revert URL and app registry modifications
            apps.unset_installed_apps()
            from council_finance import urls
            if added_pattern in urls.urlpatterns:
                urls.urlpatterns.remove(added_pattern)
            # Remove temporary plugin files and modules
            shutil.rmtree(plugin_dir)
            for mod in [module_path, module_path + ".apps", module_path + ".urls", module_path + ".views"]:
                if mod in sys.modules:
                    del sys.modules[mod]

