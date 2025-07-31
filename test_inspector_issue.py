#!/usr/bin/env python
"""
Test what the AI data inspector is actually showing.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from bs4 import BeautifulSoup
import json


def test_inspector():
    print("Testing AI Data Inspector for Worcestershire")
    print("=" * 60)
    
    # Create test client and login as admin
    client = Client()
    admin = User.objects.filter(is_staff=True).first()
    if not admin:
        print("[ERROR] No staff user found")
        return
    
    client.force_login(admin)
    print(f"[OK] Logged in as {admin.username}")
    
    # Clear cache first
    from django.core.cache import cache
    cache.delete('ai_factoids:worcestershire')
    cache.delete('ai_council_data:worcestershire')
    print("[OK] Cache cleared")
    
    # Access the inspector page
    print("\nAccessing /ai-factoids/inspect/worcestershire/...")
    response = client.get('/ai-factoids/inspect/worcestershire/')
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the AI prompt content
        prompt_pre = soup.find('pre', id='ai-prompt-content')
        if prompt_pre:
            prompt_text = prompt_pre.text.strip()
            print("\nAI Prompt found in HTML:")
            print("-" * 60)
            
            # Extract JSON section
            if "COMPLETE FINANCIAL DATASET (JSON):" in prompt_text:
                start = prompt_text.find("COMPLETE FINANCIAL DATASET (JSON):") + len("COMPLETE FINANCIAL DATASET (JSON):")
                end = prompt_text.find("\n\nANALYSIS REQUIREMENTS:")
                if end > start:
                    json_str = prompt_text[start:end].strip()
                    print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
                    
                    try:
                        data = json.loads(json_str)
                        fd = data.get('financial_data', {})
                        print("\n" + "-" * 60)
                        print(f"Financial data fields: {len(fd)}")
                        if fd:
                            print(f"Fields: {list(fd.keys())[:5]}")
                        else:
                            print("[WARNING] Financial data is EMPTY!")
                    except Exception as e:
                        print(f"\n[ERROR] Could not parse JSON: {e}")
            else:
                print("Could not find JSON section in prompt")
        else:
            print("\n[ERROR] Could not find AI prompt in HTML")
        
        # Check if financial data is shown in the overview
        financial_section = soup.find('h3', string='Financial Time Series Data')
        if financial_section:
            print("\n[OK] Financial Time Series section found in page")
            # Find the table
            table = financial_section.find_parent('div').find('table')
            if table:
                rows = table.find('tbody').find_all('tr')
                print(f"[OK] Found {len(rows)} financial metrics in table")
        else:
            print("\n[WARNING] No Financial Time Series section in page")
    else:
        print(f"\n[ERROR] Page returned status {response.status_code}")
        print("Content:", response.content[:500])


if __name__ == '__main__':
    test_inspector()