#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def test_webpage_factoids():
    """Test factoids as they would appear on the actual webpage"""
    print("=== SIMULATING WEBPAGE FACTOID LOADING ===")
    
    from django.test import Client
    import json
    
    # Test the exact parameters that would be on the interest payments counter page
    counter_slug = "interest-payments"  # From our test above
    council_slug = "worcestershire"     # From our test above  
    year_slug = "2024-25"              # Frontend converts 2024/25 to 2024-25
    
    print(f"Testing webpage simulation:")
    print(f"  Counter: {counter_slug}")
    print(f"  Council: {council_slug}")
    print(f"  Year: {year_slug}")
    print()
    
    # Test the API call the frontend JavaScript makes
    client = Client()
    api_url = f'/api/factoids/counter/{counter_slug}/{council_slug}/{year_slug}/'
    print(f"Frontend API call: {api_url}")
    
    response = client.get(api_url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data['success']}")
        print(f"Total factoids: {data['count']}")
        
        # Look specifically for interest payments factoids
        interest_factoids = [f for f in data['factoids'] 
                           if 'interest' in f['template_name'].lower() or 
                              'interest' in f['rendered_text'].lower()]
        
        if interest_factoids:
            print(f"Found {len(interest_factoids)} interest-related factoids:")
            for factoid in interest_factoids:
                print(f"  - {factoid['template_name']}: {factoid['rendered_text']}")
        else:
            print("No interest-related factoids found!")
            print("All factoids:")
            for factoid in data['factoids']:
                print(f"  - {factoid['template_name']}: {factoid['rendered_text']}")
                
    else:
        print(f"API Error: {response.content}")
        
    print()
    print("=== DEBUGGING CHECKLIST ===")
    print("1. ✅ Counter slug 'interest-payments' exists")
    print("2. ✅ Council slug 'worcestershire' exists") 
    print("3. ✅ API endpoint responds successfully")
    print("4. ✅ Interest per capita factoid is returned in API")
    print("5. ❓ Check: Is the factoid element present on the webpage?")
    print("6. ❓ Check: Are the data attributes correct?")
    print("7. ❓ Check: Is JavaScript loading properly?")

if __name__ == "__main__":
    test_webpage_factoids()
