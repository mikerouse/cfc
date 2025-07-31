#!/usr/bin/env python
"""
Intercept and log the actual prompt being sent to OpenAI.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.services.ai_factoid_generator import AIFactoidGenerator
import json

# Store the original method
original_create = None

def log_openai_call(*args, **kwargs):
    """Intercept OpenAI API calls to log the prompt."""
    print("\n" + "="*60)
    print("INTERCEPTED OPENAI API CALL")
    print("="*60)
    
    # Extract the prompt from the messages
    messages = kwargs.get('messages', [])
    if messages and len(messages) > 0:
        prompt = messages[0].get('content', '')
        print("\nPROMPT BEING SENT TO OPENAI:")
        print("-"*60)
        print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        print("-"*60)
        
        # Check for financial data
        if "COMPLETE FINANCIAL DATASET (JSON):" in prompt:
            start = prompt.find("COMPLETE FINANCIAL DATASET (JSON):") + len("COMPLETE FINANCIAL DATASET (JSON):")
            end = prompt.find("\n\nANALYSIS REQUIREMENTS:")
            if end > start:
                json_str = prompt[start:end].strip()
                try:
                    data = json.loads(json_str)
                    fd = data.get('financial_data', {})
                    print(f"\nFINANCIAL DATA IN PROMPT:")
                    print(f"  - Fields: {len(fd)}")
                    print(f"  - Keys: {list(fd.keys())[:5]}")
                    if not fd:
                        print("  [WARNING] FINANCIAL DATA IS EMPTY!")
                except:
                    print("  [ERROR] Could not parse JSON from prompt")
    
    # Call the original method
    return original_create(*args, **kwargs)


def test_with_interception():
    print("Testing AI Factoid Generation with Interception")
    print("=" * 60)
    
    # Apply monkey patch
    ai_gen = AIFactoidGenerator()
    if ai_gen.client:
        global original_create
        original_create = ai_gen.client.chat.completions.create
        ai_gen.client.chat.completions.create = log_openai_call
        print("[OK] OpenAI API calls will be intercepted")
    else:
        print("[ERROR] No OpenAI client - cannot intercept")
        return
    
    # Now test through the API
    from django.test import Client
    client = Client()
    
    # Clear cache
    from django.core.cache import cache
    cache.delete('ai_factoids:worcestershire')
    cache.delete('ai_council_data:worcestershire')
    print("[OK] Cache cleared")
    
    print("\nMaking API request to /api/factoids/ai/worcestershire/...")
    response = client.get('/api/factoids/ai/worcestershire/')
    
    print(f"\n[OK] Response status: {response.status_code}")
    
    data = json.loads(response.content)
    if data.get('factoids'):
        print(f"[OK] Generated {len(data['factoids'])} factoids")
        for i, f in enumerate(data['factoids'][:2]):
            print(f"  {i+1}. {f.get('text', 'No text')}")


if __name__ == '__main__':
    test_with_interception()