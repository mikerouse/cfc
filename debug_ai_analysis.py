#!/usr/bin/env python3
"""
Debug AI Analysis Service
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council, FinancialYear, AIAnalysisConfiguration
from council_finance.services.ai_analysis_service import AIAnalysisService
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_ai_analysis():
    print("=== AI Analysis Debug Test ===")
    
    try:
        # Get a test council and year
        council = Council.objects.first()
        if not council:
            print("ERROR: No councils found in database")
            return
        
        year = FinancialYear.objects.first()
        if not year:
            print("ERROR: No financial years found in database")
            return
            
        configuration = AIAnalysisConfiguration.objects.filter(is_active=True, is_default=True).first()
        if not configuration:
            print("ERROR: No active default configuration found")
            return
            
        print(f"Testing with: {council.name} - {year.label}")
        print(f"Configuration: {configuration.name}")
        print(f"Model: {configuration.model.name}")
        print(f"Template: {configuration.template.name}")
        
        # Initialize AI service
        ai_service = AIAnalysisService()
        
        # Check OpenAI client
        if not ai_service.openai_client:
            print("ERROR: OpenAI client not initialized")
            print(f"OpenAI API key present: {bool(os.getenv('OPENAI_API_KEY'))}")
            return
        else:
            print("PASS: OpenAI client initialized")
        
        # Test data gathering
        print("\n--- Testing Data Gathering ---")
        try:
            financial_data = ai_service._gather_financial_data(council, year)
            print(f"PASS: Financial data gathered: {len(financial_data)} sections")
            print(f"Available data keys: {list(financial_data.keys())}")
        except Exception as e:
            print(f"ERROR in data gathering: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test context building
        print("\n--- Testing Context Building ---")
        try:
            context = ai_service._build_analysis_context(council, year, financial_data, configuration.template)
            print(f"PASS: Context built, length: {len(context)} characters")
            print(f"Context preview: {context[:200]}...")
        except Exception as e:
            print(f"ERROR in context building: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test AI analysis creation (without calling OpenAI)
        print("\n--- Testing Analysis Creation ---")
        try:
            analysis = ai_service.get_or_create_analysis(
                council=council,
                year=year,
                configuration=configuration,
                force_refresh=True
            )
            
            if analysis:
                print(f"PASS: Analysis created with status: {analysis.status}")
                if analysis.error_message:
                    print(f"Error message: {analysis.error_message}")
            else:
                print("ERROR: get_or_create_analysis returned None")
                
        except Exception as e:
            print(f"ERROR in analysis creation: {e}")
            import traceback
            traceback.print_exc()
            return
            
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_analysis()