import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', "django-insecure-change-me")
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Production-ready security configuration
if DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
else:
    ALLOWED_HOSTS = [
        'councilfinancecounters.onrender.com',
        'localhost',
        '127.0.0.1',
        'testserver',
        '[::1]'
    ]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # Add humanize for template filters
    "core",
    "council_finance",
    "channels",
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
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add WhiteNoise for static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "council_finance.middleware.error_alerting.ErrorAlertingMiddleware",  # Email alerts for errors
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
                # Provide comprehensive user preferences including font, theme, and accessibility
                "council_finance.context_processors.user_preferences",
                "council_finance.context_processors.compare_count",
                "council_finance.context_processors.debug_flag",
                "council_finance.context_processors.tutorial_context",
            ],
        },
    },
]

WSGI_APPLICATION = "council_finance.wsgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv('DATABASE_URL', 'postgresql://localhost/councilfinancecounters'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# AI Service Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# SQLite configuration (for rollback if needed)
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#         "OPTIONS": {"timeout": 20},
#     }
# }

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

# Email Alert Configuration using Brevo API
BREVO_API_KEY = os.getenv('BREVO_API_KEY')
ERROR_ALERTS_EMAIL_ADDRESS = os.getenv('ERROR_ALERTS_EMAIL_ADDRESS')

# Default financial year label used across the site until updated via
# the SiteSetting admin. This ensures new pages load figures for the
# most recently finalised accounts.
DEFAULT_FINANCIAL_YEAR = "2023/24"

# Use BigAutoField so primary keys match the fields defined in existing
# migrations. Without this setting Django would default to AutoField and
# repeatedly generate spurious migration files.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Channels configuration for WebSocket support
ASGI_APPLICATION = "council_finance.asgi.application"
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}

# Auto-approval defaults used when creating new user accounts. These values
# can be overridden via the ``SiteSetting`` admin by storing integer values
# under the matching keys.
AUTO_APPROVE_MIN_VERIFIED_IPS = 1
AUTO_APPROVE_MIN_APPROVED = 3

# Static files configuration
import os
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# Production static files settings (uncomment for production)
# STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
