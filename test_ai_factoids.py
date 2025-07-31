"""
Test script for AI Factoids system

Tests the complete AI factoids pipeline:
1. Service initialization
2. Data gathering
3. API endpoints
4. Error handling
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council
from council_finance.services.ai_factoid_generator import AIFactoidGenerator, CouncilDataGatherer
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

def test_ai_factoid_service():
    """Test the AI factoid generator service."""
    print("\n1. Testing AI Factoid Generator Service")
    print("=" * 50)
    
    try:
        # Initialize generator
        generator = AIFactoidGenerator()
        print(f"[OK] AIFactoidGenerator initialized")
        print(f"  OpenAI client available: {generator.client is not None}")
        
        # Test data gatherer
        gatherer = CouncilDataGatherer()
        print(f"[OK] CouncilDataGatherer initialized")
        
        # Get a test council
        council = Council.objects.first()
        if not council:
            print("[FAIL] No councils found in database")
            return False
            
        print(f"[OK] Test council: {council.name} ({council.slug})")
        
        # Test data gathering
        council_data = gatherer.gather_council_data(council)
        print(f"[OK] Council data gathered")
        print(f"  Keys: {list(council_data.keys())}")
        
        # Test AI factoid generation (will use fallback if no OpenAI key)
        factoids = generator.generate_insights(council_data, limit=2)
        print(f"[OK] Generated {len(factoids)} factoids")
        
        for i, factoid in enumerate(factoids):
            print(f"  Factoid {i+1}: {factoid.get('text', '')}")
            print(f"    Type: {factoid.get('insight_type', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_factoid_api():
    """Test the AI factoid API endpoint."""
    print("\n2. Testing AI Factoid API")
    print("=" * 50)
    
    try:
        from council_finance.api.ai_factoid_api import ai_council_factoids
        
        # Get a test council
        council = Council.objects.first()
        if not council:
            print("[FAIL] No councils found for API test")
            return False
        
        # Create test request
        factory = RequestFactory()
        request = factory.get(f'/api/factoids/ai/{council.slug}/')
        request.user = AnonymousUser()
        
        # Test API endpoint
        print(f"[OK] Testing API for council: {council.slug}")
        response = ai_council_factoids(request, council.slug)
        
        print(f"[OK] API responded with status: {response.status_code}")
        
        if hasattr(response, 'data'):
            data = response.data
            print(f"[OK] Response data keys: {list(data.keys())}")
            
            if 'factoids' in data:
                factoids = data['factoids']
                print(f"[OK] API returned {len(factoids)} factoids")
                
                for i, factoid in enumerate(factoids[:2]):  # Show first 2
                    print(f"  API Factoid {i+1}: {factoid.get('text', '')}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_system_status():
    """Test system status and configuration."""
    print("\n3. Testing System Status")
    print("=" * 50)
    
    try:
        # Check environment
        openai_key = os.getenv('OPENAI_API_KEY')
        print(f"[OK] OpenAI API key configured: {'Yes' if openai_key else 'No (fallback mode)'}")
        
        # Check Django settings
        from django.conf import settings
        
        drf_settings = getattr(settings, 'REST_FRAMEWORK', {})
        throttle_rates = drf_settings.get('DEFAULT_THROTTLE_RATES', {})
        ai_rate = throttle_rates.get('ai_factoids', 'Not configured')
        
        print(f"[OK] AI factoids throttle rate: {ai_rate}")
        
        # Check database
        council_count = Council.objects.count()
        print(f"[OK] Database councils available: {council_count}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Status test failed: {e}")
        return False

def main():
    """Run all AI factoid tests."""
    print("AI Factoids System Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(test_ai_factoid_service())
    results.append(test_ai_factoid_api())
    results.append(test_system_status())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[SUCCESS] All {total} tests PASSED")
        print("\nAI Factoids system is ready!")
        return True
    else:
        print(f"[FAIL] {total - passed} of {total} tests FAILED")
        print("\nSome issues need to be resolved.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)