#!/usr/bin/env python
"""
Debug test to see the exact AI prompt being generated for Worcestershire.
This will show us why financial_data is empty in the prompt.
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import Council, FinancialFigure
from council_finance.services.ai_factoid_generator import CouncilDataGatherer, AIFactoidGenerator
import json


def test_worcestershire_prompt():
    print("AI Factoid Prompt Debug for Worcestershire")
    print("=" * 60)
    
    # Get Worcestershire council
    council = Council.objects.get(slug='worcestershire')
    print(f"\n1. Council: {council.name} ({council.slug})")
    
    # Check financial figures
    figures = FinancialFigure.objects.filter(council=council)
    print(f"\n2. Financial Figures in Database: {figures.count()}")
    for ff in figures[:3]:
        print(f"   - {ff.field.slug}: {ff.value} ({ff.year.label})")
    
    # Test data gathering
    print("\n3. Testing CouncilDataGatherer...")
    gatherer = CouncilDataGatherer()
    council_data = gatherer.gather_council_data(council)
    
    print(f"\n   Keys in council_data: {list(council_data.keys())}")
    
    financial_time_series = council_data.get('financial_time_series', {})
    print(f"\n   Financial time series fields: {len(financial_time_series)}")
    for field, data in list(financial_time_series.items())[:3]:
        print(f"   - {field}: {data}")
    
    # Test AI generator prompt building
    print("\n4. Testing AIFactoidGenerator prompt building...")
    ai_generator = AIFactoidGenerator()
    
    # Access the private method to see the prompt
    import types
    
    # We need to manually build the prompt like the generator does
    print("\n5. Building AI Prompt...")
    
    # This mimics what happens in generate_insights method
    council_obj = council_data.get('council', council)
    financial_data = council_data.get('financial_time_series', {})
    population_data = council_data.get('population_data', {})
    
    # Format population info
    population_info = "Population data unavailable"
    if population_data.get('latest'):
        population_info = f"Population: {population_data['latest']:,} residents"
    
    # Build the JSON structure that goes into the prompt
    council_json_data = {
        "council": {
            "name": council_obj.name,
            "slug": council_obj.slug,
            "type": str(getattr(council_obj, 'council_type', 'Council')),
            "nation": council_data.get('context', {}).get('nation', 'Unknown')
        },
        "population": population_info,
        "financial_data": financial_data,
        "data_summary": {
            "total_fields": len(financial_data),
            "fields_with_data": list(financial_data.keys()) if financial_data else [],
            "available_years": []
        }
    }
    
    # Extract years from financial data
    all_years = set()
    for field_data in financial_data.values():
        if isinstance(field_data, dict) and 'years' in field_data:
            all_years.update(field_data['years'].keys())
    council_json_data['data_summary']['available_years'] = sorted(all_years)
    
    print("\n6. PROMPT DATA STRUCTURE:")
    print(json.dumps(council_json_data, indent=2))
    
    # Now test actual generation to see what OpenAI receives
    print("\n7. Testing actual AI generation...")
    try:
        # Try to generate insights
        factoids = ai_generator.generate_insights(
            council_data=council_data,
            limit=1,
            style='news_ticker'
        )
        print(f"\nGenerated {len(factoids)} factoid(s)")
        if factoids:
            print(f"First factoid: {factoids[0].get('text', 'No text')}")
    except Exception as e:
        print(f"\nError during generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_worcestershire_prompt()