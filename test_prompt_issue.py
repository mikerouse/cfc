#!/usr/bin/env python
"""
Find where financial data is being lost in the prompt generation.
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


def test_prompt_generation():
    print("Testing AI Prompt Generation")
    print("=" * 60)
    
    # Get Worcestershire council
    council = Council.objects.get(slug='worcestershire')
    
    # Gather data
    gatherer = CouncilDataGatherer()
    council_data = gatherer.gather_council_data(council)
    
    print(f"\n1. Council data gathered:")
    print(f"   - Keys: {list(council_data.keys())}")
    print(f"   - Financial fields: {len(council_data.get('financial_time_series', {}))}")
    
    # Create AI generator and build prompt
    ai_gen = AIFactoidGenerator()
    
    # Call the private method directly to see the prompt
    prompt = ai_gen._build_analysis_prompt(council_data, limit=3, style='news_ticker')
    
    print(f"\n2. Prompt generated, length: {len(prompt)} chars")
    
    # Extract and parse the JSON from the prompt
    if "COMPLETE FINANCIAL DATASET (JSON):" in prompt:
        start = prompt.find("COMPLETE FINANCIAL DATASET (JSON):") + len("COMPLETE FINANCIAL DATASET (JSON):")
        end = prompt.find("\n\nANALYSIS REQUIREMENTS:")
        json_str = prompt[start:end].strip()
        
        print(f"\n3. Extracted JSON from prompt:")
        print("-" * 40)
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
        print("-" * 40)
        
        try:
            prompt_data = json.loads(json_str)
            print(f"\n4. Parsed JSON structure:")
            print(f"   - financial_data fields: {len(prompt_data.get('financial_data', {}))}")
            print(f"   - financial_data keys: {list(prompt_data.get('financial_data', {}).keys())[:5]}")
            
            # Check if financial_data is empty
            if not prompt_data.get('financial_data'):
                print("\n[ERROR] financial_data is EMPTY in the prompt!")
                
                # Debug: Check what's in council_data
                print("\n5. Debug - checking council_data.financial_time_series:")
                fts = council_data.get('financial_time_series', {})
                print(f"   - Type: {type(fts)}")
                print(f"   - Length: {len(fts)}")
                if fts:
                    print(f"   - First key: {list(fts.keys())[0]}")
                    print(f"   - First value type: {type(list(fts.values())[0])}")
        except Exception as e:
            print(f"\n[ERROR] Could not parse JSON: {e}")
    else:
        print("\n[ERROR] Could not find JSON section in prompt")
    
    print("\n6. Full prompt:")
    print("=" * 60)
    print(prompt)
    print("=" * 60)


if __name__ == '__main__':
    test_prompt_generation()