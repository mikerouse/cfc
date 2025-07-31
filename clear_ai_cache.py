#!/usr/bin/env python
"""
Clear all AI-related cache for a specific council or all councils.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.core.cache import cache
from council_finance.models import Council


def clear_ai_caches(council_slug=None):
    """Clear AI caches for a specific council or all councils."""
    
    if council_slug:
        councils = [Council.objects.get(slug=council_slug)]
        print(f"Clearing AI caches for {council_slug}")
    else:
        councils = Council.objects.all()
        print("Clearing AI caches for all councils")
    
    cleared_keys = []
    
    for council in councils:
        # Clear factoids cache
        factoid_key = f"ai_factoids:{council.slug}"
        if cache.delete(factoid_key):
            cleared_keys.append(factoid_key)
        
        # Clear council data cache  
        data_key = f"ai_council_data:{council.slug}"
        if cache.delete(data_key):
            cleared_keys.append(data_key)
    
    print(f"Cleared {len(cleared_keys)} cache keys:")
    for key in cleared_keys:
        print(f"  - {key}")
    
    if not cleared_keys:
        print("No cache keys found to clear")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Clear AI caches')
    parser.add_argument('--council', help='Council slug to clear (default: all councils)')
    args = parser.parse_args()
    
    clear_ai_caches(args.council)