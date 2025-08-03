#!/usr/bin/env python
"""
Debug circular import by testing imports step by step.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

print("Testing imports from main URLs file one by one...")

# Test basic imports first
basic_imports = [
    "from django.contrib import admin",
    "from django.contrib.auth.views import LoginView, LogoutView", 
    "from django.urls import include, path",
    "from django.views.generic import RedirectView",
    "from django.conf import settings",
    "from django.conf.urls.static import static",
    "from django.http import HttpResponse"
]

for imp in basic_imports:
    try:
        exec(imp)
        print(f"OK: {imp}")
    except Exception as e:
        print(f"ERROR: {imp} - {e}")

# Test view imports systematically
view_imports = [
    "from council_finance.views import general as general_views",
    "from council_finance.views import contributions as contrib_views",
    "from council_finance.views import admin as admin_views",
    "from council_finance.views import api as api_views",
    "from council_finance.views import auth as auth_views",
    "from council_finance.views import moderation as mod_views",
    "from council_finance.views import councils as council_views", 
    "from council_finance.views import pages as page_views",
    "from council_finance.views import council_management as council_mgmt_views",
    "from council_finance.views import email_status as email_status_views",
    "from council_finance.views import factoid_builder as factoid_builder_api",
    "from council_finance.views import council_edit_api",
]

for imp in view_imports:
    try:
        exec(imp)
        print(f"OK: {imp}")
    except Exception as e:
        print(f"ERROR: {imp} - {e}")

# Test complex imports from general
print("\nTesting complex general imports...")
try:
    from council_finance.views.general import (
        my_lists,
        following,
        follow_item_api,
        unfollow_item_api,
        add_favourite,
        remove_favourite,
        add_to_list,
        remove_from_list,
        move_between_lists,
        list_metric,
        add_to_compare,
        remove_from_compare,
        compare_row,
        compare_basket,
        detailed_comparison,
        clear_compare_basket,
        follow_council,
        unfollow_council,
        like_update,
        comment_update,
        interact_with_update_api,
        comment_on_update_api,
        update_feed_preferences_api,
        get_feed_updates_api,
        comment_on_activity_log,
        get_activity_log_comments,
        like_activity_log_comment,
    )
    print("OK: Complex general imports successful")
except Exception as e:
    print(f"ERROR: Complex general imports - {e}")

# Test API imports
api_imports = [
    "from council_finance.api.factoid_views import factoid_instance_api, get_factoids_for_counter_frontend",
    "from council_finance.api.ai_factoid_api import ai_council_factoids, ai_batch_factoids, clear_ai_factoid_cache, ai_factoid_status",
    "from council_finance.api.sitewide_factoid_api import get_sitewide_factoids, get_sitewide_factoids_health, sitewide_factoids_view",
    "from council_finance.api import comparison_api",
    "from council_finance.api.leaderboard_api import get_leaderboard, get_council_rankings, get_categories, leaderboard_view"
]

for imp in api_imports:
    try:
        exec(imp)
        print(f"OK: {imp}")
    except Exception as e:
        print(f"ERROR: {imp} - {e}")

# Test AI management imports
ai_imports = [
    "from council_finance.views.ai_factoid_management import ai_factoid_management_dashboard, council_ai_data_inspector, test_ai_generation, clear_factoid_cache, warmup_council_cache, council_financial_data_viewer, ai_configuration, sitewide_factoid_inspector, test_sitewide_generation, clear_sitewide_cache"
]

for imp in ai_imports:
    try:
        exec(imp)
        print(f"OK: {imp}")
    except Exception as e:
        print(f"ERROR: {imp} - {e}")

print("\nAll imports tested individually!")