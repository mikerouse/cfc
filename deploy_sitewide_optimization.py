#!/usr/bin/env python
"""
Simple deployment script for sitewide factoids optimization.
Avoids Unicode issues in management commands.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.utils import timezone
from council_finance.models import (
    SitewideFactoidSchedule, SitewideDataSummary, 
    Council, DataField, FinancialYear, FinancialFigure
)
from council_finance.services.optimized_sitewide_generator import OptimizedSitewideFactoidGenerator

def initialize_system():
    """Initialize the sitewide optimization system."""
    print("1. Initializing sitewide factoid schedule...")
    
    # Create default schedule
    schedule, created = SitewideFactoidSchedule.objects.get_or_create(
        defaults={
            'update_times': ['06:00', '10:30', '14:00', '18:30'],
            'is_active': True
        }
    )
    
    if created:
        print("   Schedule created with 4 daily update times")
    else:
        print("   Schedule already exists")
    
    print("2. Checking for financial data...")
    
    # Check if we have data to work with
    councils_count = Council.objects.count()
    fields_count = DataField.objects.count() 
    figures_count = FinancialFigure.objects.count()
    
    print(f"   Found {councils_count} councils, {fields_count} fields, {figures_count} financial figures")
    
    if figures_count == 0:
        print("   No financial data found - summaries cannot be built")
        return False
    
    print("3. Testing optimized generator...")
    
    try:
        generator = OptimizedSitewideFactoidGenerator()
        print(f"   Generator initialized with model: {generator.model}")
        print(f"   OpenAI available: {generator.client is not None}")
        
        # Test fallback generation
        fallback_factoids = generator._generate_fallback_sitewide_factoids(limit=3)
        print(f"   Generated {len(fallback_factoids)} fallback factoids")
        
        for i, factoid in enumerate(fallback_factoids, 1):
            print(f"     {i}. {factoid.get('text', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"   Error testing generator: {e}")
        return False

def create_sample_summary():
    """Create a sample summary for testing."""
    print("4. Creating sample summary data...")
    
    try:
        # Get latest year with data
        latest_year = FinancialYear.objects.filter(
            financialfigure__isnull=False
        ).distinct().order_by('-start_date').first()
        
        if not latest_year:
            print("   No financial years with data found")
            return False
        
        # Get a field with data
        field_with_data = DataField.objects.filter(
            financialfigure__year=latest_year
        ).first()
        
        if not field_with_data:
            print("   No fields with data found")
            return False
        
        # Create sample summary
        summary, created = SitewideDataSummary.objects.get_or_create(
            date_calculated=timezone.now().date(),
            year=latest_year,
            field=field_with_data,
            defaults={
                'total_councils': 10,
                'average_value': 100.0,
                'median_value': 95.0,
                'min_value': 50.0,
                'max_value': 200.0,
                'top_5_councils': [
                    {'council_name': 'Test Council 1', 'council_slug': 'test-1', 'value': 200.0},
                    {'council_name': 'Test Council 2', 'council_slug': 'test-2', 'value': 180.0},
                ],
                'bottom_5_councils': [
                    {'council_name': 'Test Council 10', 'council_slug': 'test-10', 'value': 50.0},
                ],
                'type_averages': {'County': 120.0, 'Unitary': 80.0},
                'nation_averages': {'England': 100.0, 'Scotland': 90.0},
                'data_completeness': 80.0,
                'outlier_count': 2,
                'data_hash': 'sample_hash_123'
            }
        )
        
        if created:
            print(f"   Created sample summary for {field_with_data.name} - {latest_year.label}")
        else:
            print(f"   Sample summary already exists for {field_with_data.name} - {latest_year.label}")
        
        return True
        
    except Exception as e:
        print(f"   Error creating sample summary: {e}")
        return False

def test_optimized_generation():
    """Test the optimized factoid generation."""
    print("5. Testing optimized factoid generation...")
    
    try:
        generator = OptimizedSitewideFactoidGenerator()
        factoids = generator.generate_optimized_factoids(limit=3)
        
        print(f"   Generated {len(factoids)} factoids:")
        for i, factoid in enumerate(factoids, 1):
            print(f"     {i}. {factoid.get('text', 'N/A')}")
            print(f"        Type: {factoid.get('insight_type', 'N/A')}")
            print(f"        Confidence: {factoid.get('confidence', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"   Error testing generation: {e}")
        return False

def main():
    """Main deployment function."""
    print("Deploying Sitewide Factoids Optimization System")
    print("=" * 50)
    
    success = True
    
    # Step 1: Initialize system
    if not initialize_system():
        success = False
    
    # Step 2: Create sample data
    if success and not create_sample_summary():
        success = False
    
    # Step 3: Test generation
    if success and not test_optimized_generation():
        success = False
    
    print("=" * 50)
    if success:
        print("SUCCESS: Sitewide optimization system deployed successfully!")
        print("\nNext steps:")
        print("1. Set up cron jobs for automated updates")
        print("2. Build full data summaries with: python manage.py build_sitewide_summaries --all-years")
        print("3. Test scheduling with: python manage.py update_sitewide_factoids --check-schedule --dry-run")
    else:
        print("FAILED: Deployment encountered errors")
    
    return success

if __name__ == '__main__':
    main()