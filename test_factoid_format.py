#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def test_factoid_data_format():
    """Test the format transformation needed for factoids"""
    print("=== TESTING FACTOID DATA FORMAT ===")
    
    from django.test import Client
    import json
    
    # Get the API response
    client = Client()
    response = client.get('/api/factoids/counter/interest-payments/worcestershire/2023-24/')
    
    if response.status_code == 200:
        data = response.json()
        print(f"API returned {data['count']} factoids")
        
        # Show the original API format
        if data['factoids']:
            print("\nOriginal API format (first factoid):")
            first_factoid = data['factoids'][0]
            for key, value in first_factoid.items():
                print(f"  {key}: {value}")
            
            print("\nAfter JavaScript transformation should be:")
            transformed = {
                'text': first_factoid['rendered_text'],
                'emoji': first_factoid.get('emoji', '📊'),
                'color': first_factoid.get('color', 'blue'),
                'id': first_factoid['id'],
                'template_name': first_factoid['template_name'],
                'relevance_score': first_factoid['relevance_score']
            }
            for key, value in transformed.items():
                print(f"  {key}: {value}")
            
            # Test specifically for the interest payments factoid
            interest_factoid = None
            for factoid in data['factoids']:
                if 'interest-payments-per-capita' in factoid['template_slug']:
                    interest_factoid = factoid
                    break
            
            if interest_factoid:
                print(f"\nInterest payments factoid:")
                print(f"  Original: rendered_text = '{interest_factoid['rendered_text']}'")
                print(f"  Transformed: text = '{interest_factoid['rendered_text']}'")
                
                if 'N/A' in interest_factoid['rendered_text']:
                    print("  ⚠️  WARNING: Interest factoid shows 'N/A' - field computation issue!")
                else:
                    print("  ✅ Interest factoid has actual data")
            else:
                print("\n❌ No interest payments factoid found!")
    else:
        print(f"API Error: {response.status_code}")

if __name__ == "__main__":
    test_factoid_data_format()
