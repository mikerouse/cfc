#!/usr/bin/env python
"""
Debug the inspector prompt generation issue.
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
from django.core.cache import cache


def test_inspector_data():
    print("Debugging Inspector Prompt Generation")
    print("=" * 60)
    
    # Clear cache
    cache.delete('ai_factoids:worcestershire')
    cache.delete('ai_council_data:worcestershire')
    print("[OK] Cache cleared")
    
    # Get council
    council = Council.objects.get(slug='worcestershire')
    
    # Test data gathering
    print("\n1. Testing data gathering directly...")
    gatherer = CouncilDataGatherer()
    council_data = gatherer.gather_council_data(council)
    
    fts = council_data.get('financial_time_series', {})
    print(f"   Financial time series fields: {len(fts)}")
    if fts:
        first_key = list(fts.keys())[0]
        print(f"   First field: {first_key}")
        print(f"   Structure: {fts[first_key]}")
    
    # Test prompt generation
    print("\n2. Testing prompt generation directly...")
    generator = AIFactoidGenerator()
    prompt = generator._build_analysis_prompt(council_data, limit=3, style='news_ticker')
    
    # Check the prompt
    if '"financial_data": {}' in prompt:
        print("   [ERROR] Empty financial_data in prompt!")
        
        # Debug the prompt building
        print("\n3. Debugging prompt building step by step...")
        
        # What's in data?
        print(f"   data keys: {list(council_data.keys())}")
        print(f"   data['financial_time_series'] type: {type(council_data.get('financial_time_series'))}")
        print(f"   data['financial_time_series'] length: {len(council_data.get('financial_time_series', {}))}")
        
        # Check what happens in the prompt builder
        financial_data = council_data.get('financial_time_series', {})
        print(f"\n   financial_data type: {type(financial_data)}")
        print(f"   financial_data length: {len(financial_data)}")
        print(f"   financial_data keys: {list(financial_data.keys())[:3]}")
        
        # Build the JSON structure manually
        council_json_data = {
            "council": {
                "name": council.name,
                "slug": council.slug,
                "type": str(getattr(council, 'council_type', 'Council')),
                "nation": 'Unknown'
            },
            "population": "Population: 609,216 residents",
            "financial_data": financial_data,
            "data_summary": {
                "total_fields": len(financial_data),
                "fields_with_data": list(financial_data.keys()),
            }
        }
        
        print(f"\n   council_json_data['financial_data'] length: {len(council_json_data['financial_data'])}")
        
        # Convert to JSON
        json_str = json.dumps(council_json_data, indent=2)
        print(f"\n   JSON string length: {len(json_str)}")
        print("\n   First 500 chars of JSON:")
        print(json_str[:500])
    else:
        print("   [OK] financial_data has content in prompt")
        
        # Extract JSON to verify
        start = prompt.find("COMPLETE FINANCIAL DATASET (JSON):") + len("COMPLETE FINANCIAL DATASET (JSON):")
        end = prompt.find("\n\nANALYSIS REQUIREMENTS:")
        json_str = prompt[start:end].strip()
        
        try:
            data = json.loads(json_str)
            print(f"   Financial data fields: {len(data.get('financial_data', {}))}")
        except:
            print("   [ERROR] Could not parse JSON from prompt")
    
    # Now test what the inspector view sees
    print("\n4. Testing inspector view context...")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/ai-factoids/inspect/worcestershire/')
    admin = User.objects.filter(is_staff=True).first()
    request.user = admin
    
    # We can't easily get the context from the view, but we've already tested above
    print("   [INFO] View would use same data gathering and prompt building")


if __name__ == '__main__':
    test_inspector_data()