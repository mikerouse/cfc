#!/usr/bin/env python
"""
Test minimal URL configuration to identify the issue.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

print("Testing minimal URL configuration...")

# Try to create a minimal urlpatterns
try:
    from django.urls import path
    from django.http import HttpResponse
    from council_finance.views import ai_tools_hub
    
    def test_view(request):
        return HttpResponse("Test")
    
    # Create minimal urlpatterns
    urlpatterns = [
        path("test/", test_view, name="test"),
        path("ai-tools/", ai_tools_hub.ai_tools_hub, name="ai_tools_hub"),
    ]
    
    print(f"Minimal urlpatterns created successfully with {len(urlpatterns)} patterns")
    
    # Test if we can import the actual urls module without executing it
    import importlib.util
    spec = importlib.util.spec_from_file_location("council_finance.urls", 
                                                  "F:/mikerouse/Documents/Projects/Council Finance Counters/v3/cfc/council_finance/urls.py")
    urls_module = importlib.util.module_from_spec(spec)
    
    print("About to execute the URLs module...")
    spec.loader.exec_module(urls_module)
    
    if hasattr(urls_module, 'urlpatterns'):
        print(f"SUCCESS: Real urlpatterns found with {len(urls_module.urlpatterns)} patterns")
    else:
        print("ERROR: Real urlpatterns not found")
        print("Available attributes:", [attr for attr in dir(urls_module) if not attr.startswith('_')])
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()