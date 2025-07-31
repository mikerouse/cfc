#!/usr/bin/env python
"""
Trace the exact flow of data through the AI factoid generation process.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import CouncilDataGatherer, AIFactoidGenerator
import json


# Monkey patch to see what's happening
original_build_prompt = AIFactoidGenerator._build_analysis_prompt

def traced_build_prompt(self, data, limit, style):
    print("\n[TRACE] _build_analysis_prompt called with:")
    print(f"  - data keys: {list(data.keys())}")
    print(f"  - financial_time_series present: {'financial_time_series' in data}")
    if 'financial_time_series' in data:
        print(f"  - financial_time_series fields: {len(data['financial_time_series'])}")
    
    # Call original
    prompt = original_build_prompt(self, data, limit, style)
    
    # Extract the JSON part from the prompt
    if "COMPLETE FINANCIAL DATASET (JSON):" in prompt:
        start = prompt.find("COMPLETE FINANCIAL DATASET (JSON):") + len("COMPLETE FINANCIAL DATASET (JSON):")
        end = prompt.find("\n\nANALYSIS REQUIREMENTS:")
        json_str = prompt[start:end].strip()
        
        try:
            prompt_data = json.loads(json_str)
            print(f"\n[TRACE] Prompt JSON financial_data fields: {len(prompt_data.get('financial_data', {}))}")
            if not prompt_data.get('financial_data'):
                print("[WARNING] financial_data is empty in prompt!")
        except:
            print("[ERROR] Could not parse JSON from prompt")
    
    return prompt

# Apply the monkey patch
AIFactoidGenerator._build_analysis_prompt = traced_build_prompt


def test_trace():
    print("AI Factoid Generation Trace")
    print("=" * 60)
    
    # Get Worcestershire council
    council = Council.objects.get(slug='worcestershire')
    print(f"\nCouncil: {council.name}")
    
    # Test through API endpoint simulation
    from council_finance.api.ai_factoid_api import get_ai_factoids
    from django.test import RequestFactory
    
    factory = RequestFactory()
    request = factory.get(f'/api/factoids/ai/{council.slug}/')
    
    # Clear cache first
    from django.core.cache import cache
    cache.delete(f'ai_factoids:{council.slug}')
    cache.delete(f'ai_council_data:{council.slug}')
    
    print("\n[TRACE] Calling API endpoint...")
    
    # Import and call the view function directly
    from django.http import HttpRequest
    mock_request = HttpRequest()
    mock_request.method = 'GET'
    
    response = get_ai_factoids(mock_request, council.slug)
    
    print(f"\n[TRACE] Response status: {response.status_code}")
    
    response_data = json.loads(response.content)
    if response_data.get('factoids'):
        print(f"[TRACE] Generated {len(response_data['factoids'])} factoids")
        for i, f in enumerate(response_data['factoids'][:2]):
            print(f"  {i+1}. {f.get('text', 'No text')}")


if __name__ == '__main__':
    test_trace()