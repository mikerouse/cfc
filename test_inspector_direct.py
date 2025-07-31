#!/usr/bin/env python
"""
Test the data inspector view directly.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import CouncilDataGatherer, AIFactoidGenerator
from council_finance.views.ai_factoid_management import council_ai_data_inspector
from django.test import RequestFactory
from django.contrib.auth.models import User
import json


def test_inspector_view():
    print("Testing AI Data Inspector View Directly")
    print("=" * 60)
    
    # Get council
    council = Council.objects.get(slug='worcestershire')
    print(f"\nCouncil: {council.name}")
    
    # Clear cache
    from django.core.cache import cache
    cache.delete('ai_factoids:worcestershire')
    cache.delete('ai_council_data:worcestershire')
    print("[OK] Cache cleared")
    
    # Test data gathering directly
    print("\n1. Testing data gathering...")
    gatherer = CouncilDataGatherer()
    council_data = gatherer.gather_council_data(council)
    
    fts = council_data.get('financial_time_series', {})
    print(f"   Financial time series fields: {len(fts)}")
    if fts:
        print(f"   First 3 fields: {list(fts.keys())[:3]}")
    
    # Test prompt generation directly
    print("\n2. Testing prompt generation...")
    generator = AIFactoidGenerator()
    prompt = generator._build_analysis_prompt(council_data, limit=3, style='news_ticker')
    
    # Extract JSON from prompt
    if "COMPLETE FINANCIAL DATASET (JSON):" in prompt:
        start = prompt.find("COMPLETE FINANCIAL DATASET (JSON):") + len("COMPLETE FINANCIAL DATASET (JSON):")
        end = prompt.find("\n\nANALYSIS REQUIREMENTS:")
        json_str = prompt[start:end].strip()
        
        try:
            data = json.loads(json_str)
            fd = data.get('financial_data', {})
            print(f"   Financial data in prompt: {len(fd)} fields")
            if not fd:
                print("   [ERROR] Financial data is EMPTY in prompt!")
                
                # Debug the prompt building
                print("\n3. Debugging prompt building...")
                print(f"   council_data type: {type(council_data)}")
                print(f"   council_data keys: {list(council_data.keys())}")
                print(f"   financial_time_series type: {type(council_data.get('financial_time_series'))}")
                print(f"   financial_time_series length: {len(council_data.get('financial_time_series', {}))}")
        except Exception as e:
            print(f"   [ERROR] Could not parse JSON: {e}")
    
    # Now test the view
    print("\n4. Testing the inspector view...")
    
    # Create request
    factory = RequestFactory()
    request = factory.get(f'/ai-factoids/inspect/worcestershire/')
    
    # Add user
    admin = User.objects.filter(is_staff=True).first()
    request.user = admin
    
    # Call view directly (but we can't easily parse the response)
    # Just check it doesn't error
    try:
        response = council_ai_data_inspector(request, 'worcestershire')
        print(f"   View returned status: {response.status_code}")
        
        # The view renders a template, so we can't easily check the context
        # But we've already tested the data gathering and prompt generation above
    except Exception as e:
        print(f"   [ERROR] View failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_inspector_view()