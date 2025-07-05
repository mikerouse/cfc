import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-change-me"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "council_finance",
    "heroicons",
]

# Dynamically discover plugins
PLUGINS_DIR = BASE_DIR / "council_finance" / "plugins"
for plugin in os.listdir(PLUGINS_DIR):
    if (
        os.path.isdir(PLUGINS_DIR / plugin)
        and (PLUGINS_DIR / plugin / "apps.py").exists()
    ):
        INSTALLED_APPS.append(f"council_finance.plugins.{plugin}")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "council_finance.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Look for templates in the project-level "templates" directory so
        # apps and built-in views can share a consistent style.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Provide the chosen Google font to every template.
                "council_finance.context_processors.font_family",
            ],
        },
    },
]

WSGI_APPLICATION = "council_finance.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

# Collect static files from our own directory plus icon packages
STATICFILES_DIRS = [BASE_DIR / "static"]
try:
    import heroicons
    from pathlib import Path

    STATICFILES_DIRS.append(Path(heroicons.__file__).resolve().parent / "static")
except Exception:
    pass

try:
    import importlib.util

    spec = importlib.util.find_spec("fontawesome-free")
    if spec and spec.submodule_search_locations:
        fa_static = Path(spec.submodule_search_locations[0]) / "static"
        STATICFILES_DIRS.append(fa_static)
except Exception:
    pass

# After a successful login send users to their profile page.
LOGIN_REDIRECT_URL = "/accounts/profile/"

# Use an in-memory email backend during development and tests.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Address used for all outgoing system emails
DEFAULT_FROM_EMAIL = "counters@mikerouse.co.uk"

# Default financial year label used across the site until updated via
# the SiteSetting admin. This ensures new pages load figures for the
# most recently finalised accounts.
DEFAULT_FINANCIAL_YEAR = "2023/24"

# Use BigAutoField so primary keys match the fields defined in existing
# migrations. Without this setting Django would default to AutoField and
# repeatedly generate spurious migration files.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
