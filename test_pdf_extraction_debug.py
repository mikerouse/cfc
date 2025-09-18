#!/usr/bin/env python3
"""
PDF Extraction Debug Tool

Tests the PDF processing pipeline to understand why only 3 fields 
are being extracted when more should be found.

Usage:
    python test_pdf_extraction_debug.py
"""

import os
import django
import logging
from typing import Dict, Any

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.services.pdf_processing import TikaFinancialExtractor
from council_finance.models import DataField

# Set up logging to see detailed debug info
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_field_mapping_coverage():
    """Test how many database fields vs extraction fields we have"""
    print("\n🔍 TESTING FIELD MAPPING COVERAGE")
    print("=" * 50)
    
    # Get all financial fields from database
    financial_fields = DataField.objects.filter(
        category__in=['balance_sheet', 'income', 'spending']
    ).values('slug', 'name', 'category')
    
    print(f"📊 Database has {financial_fields.count()} financial fields:")
    for field in financial_fields:
        print(f"  • {field['slug']} ({field['category']}) - {field['name']}")
    
    # Check API field mapping
    api_field_mapping = {
        'revenue_income': 'total-income',
        'total_expenditure': 'total-expenditure', 
        'current_assets': 'current-assets',
        'current_liabilities': 'current-liabilities',
        'long_term_liabilities': 'long-term-liabilities',
        'total_debt': 'total-debt',
        'interest_payments': 'interest-paid',
        'reserves': 'total-reserves'
    }
    
    print(f"\n📤 API only maps {len(api_field_mapping)} fields:")
    for internal_field, api_field in api_field_mapping.items():
        print(f"  • {internal_field} → {api_field}")
    
    # Check which database fields are missing from API mapping
    mapped_api_fields = set(api_field_mapping.values())
    db_field_slugs = set(field['slug'] for field in financial_fields)
    
    unmapped_fields = db_field_slugs - mapped_api_fields
    if unmapped_fields:
        print(f"\n⚠️  DATABASE FIELDS NOT MAPPED BY API ({len(unmapped_fields)}):")
        for field_slug in sorted(unmapped_fields):
            field_info = next((f for f in financial_fields if f['slug'] == field_slug), None)
            if field_info:
                print(f"  • {field_slug} ({field_info['category']}) - {field_info['name']}")
    
    return len(financial_fields), len(api_field_mapping), len(unmapped_fields)


def test_regex_extraction_patterns():
    """Test regex extraction patterns against sample council financial text"""
    print("\n🔍 TESTING REGEX EXTRACTION PATTERNS")
    print("=" * 50)
    
    # Sample text that mimics UK council financial statements
    sample_texts = [
        # Birmingham-style balance sheet
        """
        Entity Group Entity Group
        Current liabilities
        (268.9) (247.3) (326.8) (289.5)
        
        Long-term liabilities  
        (577.8) (665.8) (443.2) (531.6)
        
        Total reserves
        3,059.6 3,158.3 2,845.9 2,944.6
        """,
        
        # Standard UK council format
        """
        Total income: £245.7 million
        Total expenditure: £234.1 million
        Current assets: £89.2 million
        Current liabilities: £67.4 million
        Long-term borrowing: £156.8 million
        Total debt: £224.2 million
        Interest payments: £8.9 million
        Total reserves: £178.5 million
        """,
        
        # Alternative format
        """
        Revenue income (132,743 thousands)
        Net expenditure 129,856 thousands
        Total borrowing £89.2m
        Usable reserves £45.6m
        """
    ]
    
    extractor = TikaFinancialExtractor()
    
    for i, sample_text in enumerate(sample_texts, 1):
        print(f"\n📄 Testing Sample Text {i}:")
        print("─" * 30)
        print(sample_text.strip())
        
        # Test enhanced regex extraction
        results = extractor._extract_financial_data_enhanced(sample_text)
        
        print(f"\n📊 Extracted {len([k for k, v in results.items() if v is not None and isinstance(v, (int, float)) and v > 0])} numeric fields:")
        
        for field, value in results.items():
            if isinstance(value, (int, float)) and value > 0:
                # Format value in millions for readability  
                value_millions = value / 1000000
                print(f"  • {field}: £{value_millions:.1f}m (£{value:,})")
        
        # Show metadata if available
        metadata = results.get('_metadata', {})
        if metadata:
            print(f"\n📋 Extraction Metadata:")
            for field, meta in metadata.items():
                print(f"  • {field}:")
                print(f"    - Source: {meta.get('source_text', 'N/A')}")
                print(f"    - Page: {meta.get('page_number', 'N/A')}")


def test_confidence_thresholds():
    """Test how confidence scoring affects field filtering"""
    print("\n🔍 TESTING CONFIDENCE THRESHOLDS")
    print("=" * 50)
    
    # Simulate different confidence scenarios
    sample_data = {
        'current_liabilities': 247300000,  # £247.3m
        'total_debt': 156800000,          # £156.8m  
        'reserves': 178500000,            # £178.5m
        'revenue_income': 245700000,      # £245.7m
        'total_expenditure': 234100000,   # £234.1m
    }
    
    confidence_scenarios = [
        {'name': 'High Confidence', 'base_confidence': 0.9},
        {'name': 'Medium Confidence', 'base_confidence': 0.7},
        {'name': 'Low Confidence', 'base_confidence': 0.4},
        {'name': 'Mixed Confidence', 'base_confidence': 0.8, 'variance': 0.3}
    ]
    
    for scenario in confidence_scenarios:
        print(f"\n📊 {scenario['name']} Scenario:")
        
        confidence_scores = {}
        for field in sample_data:
            base = scenario['base_confidence']
            if 'variance' in scenario:
                # Add some variance for mixed scenario
                import random
                variance = scenario['variance']
                confidence = max(0.1, min(1.0, base + random.uniform(-variance, variance)))
            else:
                confidence = base
            confidence_scores[field] = confidence
        
        # Show how fields would be categorized
        high_conf_fields = [f for f, c in confidence_scores.items() if c >= 0.8]
        med_conf_fields = [f for f, c in confidence_scores.items() if 0.6 <= c < 0.8] 
        low_conf_fields = [f for f, c in confidence_scores.items() if c < 0.6]
        
        print(f"  • High confidence (≥0.8): {len(high_conf_fields)} fields")
        print(f"  • Medium confidence (0.6-0.8): {len(med_conf_fields)} fields")
        print(f"  • Low confidence (<0.6): {len(low_conf_fields)} fields")
        
        for field, conf in confidence_scores.items():
            category = "🟢 High" if conf >= 0.8 else "🟡 Medium" if conf >= 0.6 else "🔴 Low"
            print(f"    - {field}: {conf:.2f} ({category})")


def test_quality_assessment():
    """Test the quality assessment that filters extraction results"""
    print("\n🔍 TESTING QUALITY ASSESSMENT")
    print("=" * 50)
    
    sample_text = """
    Financial indicators found: income, expenditure, assets, liabilities, debt, reserves
    Total income: £245.7 million
    Current liabilities: £67.4 million  
    Total debt: £224.2 million
    """
    
    # Test different extraction scenarios
    scenarios = [
        {
            'name': 'Good Extraction',
            'data': {
                'revenue_income': 245700000,
                'current_liabilities': 67400000,
                'total_debt': 224200000,
                'reserves': 89200000,
                'total_expenditure': 234100000
            }
        },
        {
            'name': 'Minimal Extraction',
            'data': {
                'current_liabilities': 67400000,
                'total_debt': 224200000,
                'reserves': 89200000
            }
        },
        {
            'name': 'Ambiguous Values',
            'data': {
                'revenue_income': 250000000,  # Exactly 250m - suspiciously round
                'total_debt': 100000000,     # Exactly 100m - suspiciously round
                'current_liabilities': 67400000  # Normal value
            }
        }
    ]
    
    extractor = TikaFinancialExtractor()
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['name']}:")
        
        # Test quality assessment
        quality = extractor._assess_extraction_quality(scenario['data'], sample_text)
        
        print(f"  • Confidence: {quality['confidence']:.2f}")
        print(f"  • Fields extracted: {quality['extracted_field_count']}")
        print(f"  • Missing critical: {quality['missing_critical_fields']}")
        print(f"  • Ambiguous fields: {len(quality['ambiguous_fields'])}")
        print(f"  • Recommendation: {quality['recommendation']}")
        
        if quality['ambiguous_fields']:
            print(f"  • Flagged as ambiguous: {', '.join(quality['ambiguous_fields'])}")


def main():
    """Run all diagnostic tests"""
    print("🔧 PDF EXTRACTION DIAGNOSTIC TOOL")
    print("=" * 60)
    
    try:
        # Test 1: Field mapping coverage
        db_fields, api_fields, unmapped = test_field_mapping_coverage()
        
        # Test 2: Regex pattern testing
        test_regex_extraction_patterns()
        
        # Test 3: Confidence threshold testing
        test_confidence_thresholds()
        
        # Test 4: Quality assessment testing
        test_quality_assessment()
        
        # Summary
        print("\n📋 DIAGNOSTIC SUMMARY")
        print("=" * 50)
        print(f"• Database has {db_fields} financial fields")
        print(f"• API only maps {api_fields} fields")
        print(f"• {unmapped} fields are not mapped to the API")
        
        if unmapped > 0:
            print(f"\n⚠️  LIKELY ISSUE: Limited API field mapping")
            print(f"   The API field_mapping only includes {api_fields} fields")
            print(f"   even though the database has {db_fields} financial fields.")
            print(f"   This means {unmapped} fields won't be returned even if extracted.")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Expand the field_mapping in process_pdf_api()")
        print(f"   2. Test regex patterns against actual council PDFs")
        print(f"   3. Review confidence scoring thresholds")
        print(f"   4. Add debug logging to see what gets filtered out")
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
