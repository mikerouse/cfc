#!/usr/bin/env python
"""
Test individual URL import statements to identify the circular import issue.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

print("Testing URL imports step by step...")

# Test basic Django imports
try:
    from django.contrib import admin
    from django.contrib.auth.views import LoginView, LogoutView
    from django.urls import include, path
    from django.views.generic import RedirectView
    from django.conf import settings
    from django.conf.urls.static import static
    from django.http import HttpResponse
    print("1. Basic Django imports: OK")
except Exception as e:
    print(f"1. Basic Django imports: ERROR - {e}")
    exit(1)

# Test view imports one by one
imports_to_test = [
    ("general views", "from council_finance.views import general as general_views"),
    ("contrib views", "from council_finance.views import contributions as contrib_views"), 
    ("admin views", "from council_finance.views import admin as admin_views"),
    ("api views", "from council_finance.views import api as api_views"),
    ("auth views", "from council_finance.views import auth as auth_views"),
    ("moderation views", "from council_finance.views import moderation as mod_views"),
    ("council views", "from council_finance.views import councils as council_views"),
    ("page views", "from council_finance.views import pages as page_views"),
    ("council mgmt views", "from council_finance.views import council_management as council_mgmt_views"),
    ("email status views", "from council_finance.views import email_status as email_status_views"),
    ("factoid builder api", "from council_finance.views import factoid_builder as factoid_builder_api"),
    ("council edit api", "from council_finance.views import council_edit_api"),
]

for name, import_statement in imports_to_test:
    try:
        exec(import_statement)
        print(f"2. {name}: OK")
    except Exception as e:
        print(f"2. {name}: ERROR - {e}")

# Test individual function imports from general
print("\n3. Testing individual function imports from general...")
try:
    from council_finance.views.general import (
        my_lists, following, follow_item_api, unfollow_item_api,
        add_favourite, remove_favourite
    )
    print("3. General function imports (partial): OK")
except Exception as e:
    print(f"3. General function imports (partial): ERROR - {e}")

# Test factoid API imports
print("\n4. Testing factoid API imports...")
try:
    from council_finance.api.factoid_views import factoid_instance_api, get_factoids_for_counter_frontend
    print("4. Factoid views API: OK")
except Exception as e:
    print(f"4. Factoid views API: ERROR - {e}")

# Test AI factoid API imports
print("\n5. Testing AI factoid API imports...")
try:
    from council_finance.api.ai_factoid_api import (
        ai_council_factoids, ai_batch_factoids, clear_ai_factoid_cache, ai_factoid_status
    )
    print("5. AI factoid API: OK")
except Exception as e:
    print(f"5. AI factoid API: ERROR - {e}")

# Test AI management views
print("\n6. Testing AI management views...")
try:
    from council_finance.views.ai_factoid_management import (
        ai_factoid_management_dashboard, council_ai_data_inspector
    )
    print("6. AI management views: OK")
except Exception as e:
    print(f"6. AI management views: ERROR - {e}")

# Test AI analytics dashboard
print("\n7. Testing AI analytics dashboard...")
try:
    from council_finance.views.ai_analytics_dashboard import ai_analytics_dashboard
    print("7. AI analytics dashboard: OK")
except Exception as e:
    print(f"7. AI analytics dashboard: ERROR - {e}")

# Test AI monitoring dashboard
print("\n8. Testing AI monitoring dashboard...")
try:
    from council_finance.views.ai_monitoring_dashboard import ai_monitoring_dashboard
    print("8. AI monitoring dashboard: OK")
except Exception as e:
    print(f"8. AI monitoring dashboard: ERROR - {e}")

# Test AI tools hub
print("\n9. Testing AI tools hub...")
try:
    from council_finance.views import ai_tools_hub
    print("9. AI tools hub: OK")
except Exception as e:
    print(f"9. AI tools hub: ERROR - {e}")

print("\nAll individual imports tested!")