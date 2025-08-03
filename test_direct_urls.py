#!/usr/bin/env python
"""
Test direct URL import to identify the issue.
"""

import os
import sys

# Setup Python path
sys.path.insert(0, 'F:/mikerouse/Documents/Projects/Council Finance Counters/v3/cfc')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')

print("Testing direct import...")

try:
    # Test direct import of the minimal URLs file
    import django
    django.setup()
    
    print("Django setup complete")
    
    # Now try to import the URLs module
    import council_finance.urls as urls_module
    
    print(f"URLs module imported: {urls_module}")
    print(f"Has urlpatterns: {hasattr(urls_module, 'urlpatterns')}")
    
    if hasattr(urls_module, 'urlpatterns'):
        print(f"urlpatterns type: {type(urls_module.urlpatterns)}")
        print(f"urlpatterns length: {len(urls_module.urlpatterns)}")
        print("SUCCESS: URLs module works!")
    else:
        print("ERROR: No urlpatterns found")
        print("Module attributes:", [attr for attr in dir(urls_module) if not attr.startswith('_')])
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()