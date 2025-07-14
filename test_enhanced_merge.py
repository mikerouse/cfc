#!/usr/bin/env python
"""
Test script for enhanced council merge functionality with year cutoffs
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models.council import Council, FinancialYear, FigureSubmission
from council_finance.models.activity_log import ActivityLog
from council_finance.models.field import DataField

def setup_test_data():
    """Create test data for merge testing"""
    print("Setting up test data...")
    
    # Get existing financial years or create simple ones
    years = list(FinancialYear.objects.all()[:4])
    if len(years) < 4:
        print("Not enough financial years exist. Creating test years...")
        years = []
        for label in ['2020-21', '2021-22', '2022-23', '2023-24']:
            year, _ = FinancialYear.objects.get_or_create(label=label, defaults={'is_current': label == '2023-24'})
            years.append(year)
    
    # Create test councils
    source_council, _ = Council.objects.get_or_create(
        name="Test Borough Council",
        defaults={'slug': 'test-borough', 'status': 'active'}
    )
    target_council, _ = Council.objects.get_or_create(
        name="Test Unitary Council", 
        defaults={'slug': 'test-unitary', 'status': 'active'}
    )
    
    # Get any existing data field
    field = DataField.objects.first()
    if not field:
        print("No data fields exist. Please run migrations and load data first.")
        return None, None, None
    
    # Create test figure submissions
    test_values = ['1000000', '1100000', '1200000', '1300000', '5000000', '5100000']
    
    # Clear any existing test data
    FigureSubmission.objects.filter(
        council__in=[source_council, target_council]
    ).delete()
    
    # Create submissions for source council (all years)
    for i, year in enumerate(years):
        FigureSubmission.objects.create(
            council=source_council,
            year=year,
            field=field,
            value=test_values[i]
        )
    
    # Create overlapping submissions for target council (last 2 years)
    for i, year in enumerate(years[-2:]):
        FigureSubmission.objects.create(
            council=target_council,
            year=year,
            field=field,
            value=test_values[i + 4]
        )
    
    print(f"Created test data:")
    print(f"  Source council: {source_council.name}")
    print(f"  Target council: {target_council.name}")
    print(f"  Financial years: {[y.label for y in years]}")
    print(f"  Field: {field.name}")
    print(f"  Overlapping data in last 2 years")
    
    return source_council, target_council, years[2]  # Merge from 3rd year (2022-23)

def test_merge_logic():
    """Test the enhanced merge logic"""
    print("\n" + "="*60)
    print("TESTING ENHANCED MERGE LOGIC")
    print("="*60)
    
    source_council, target_council, merge_from_year = setup_test_data()
    
    print(f"\nBefore merge:")
    print(f"Source council ({source_council.name}) submissions:")
    for sub in source_council.figuresubmission_set.all().order_by('year__label'):
        print(f"  {sub.year.label}: {sub.field.name} = £{int(sub.value):,}")
    
    print(f"\nTarget council ({target_council.name}) submissions:")
    for sub in target_council.figuresubmission_set.all().order_by('year__label'):
        print(f"  {sub.year.label}: {sub.field.name} = £{int(sub.value):,}")
    
    # Simulate the merge logic
    print(f"\nSimulating merge from {merge_from_year.label} onwards...")
    
    from django.db import transaction
    
    try:
        with transaction.atomic():
            # Get figure submissions to merge (from specified year onwards)
            # Get all years from the merge year onwards by comparing IDs
            merge_year_and_later = FinancialYear.objects.filter(id__gte=merge_from_year.id)
            figures_to_merge = source_council.figuresubmission_set.filter(
                year__in=merge_year_and_later
            )
            
            print(f"Figures to merge: {figures_to_merge.count()}")
            
            # Check for conflicts and handle them
            conflicts_resolved = 0
            figures_moved = 0
            
            for figure in figures_to_merge:
                existing = target_council.figuresubmission_set.filter(
                    year=figure.year,
                    field=figure.field
                ).first()
                
                if existing:
                    print(f"  CONFLICT: {figure.year.label} {figure.field.name} - updating £{int(existing.value):,} → £{int(figure.value):,}")
                    # Update existing submission with source data
                    existing.value = figure.value
                    existing.save()
                    # Delete the source submission
                    figure.delete()
                    conflicts_resolved += 1
                else:
                    print(f"  MOVE: {figure.year.label} {figure.field.name} = £{int(figure.value):,}")
                    # Move the submission
                    figure.council = target_council
                    figure.save()
                    figures_moved += 1
            
            # Mark source council as defunct
            source_council.status = 'defunct'
            source_council.save()
            
            print(f"\nMerge completed!")
            print(f"  Figures moved: {figures_moved}")
            print(f"  Conflicts resolved: {conflicts_resolved}")
            print(f"  Source council status: {source_council.status}")
            
    except Exception as e:
        print(f"ERROR during merge: {str(e)}")
        return
    
    print(f"\nAfter merge:")
    print(f"Source council ({source_council.name}) submissions:")
    for sub in source_council.figuresubmission_set.all().order_by('year__label'):
        print(f"  {sub.year.label}: {sub.field.name} = £{int(sub.value):,}")
    
    print(f"\nTarget council ({target_council.name}) submissions:")
    for sub in target_council.figuresubmission_set.all().order_by('year__label'):
        print(f"  {sub.year.label}: {sub.field.name} = £{int(sub.value):,}")
    
    print(f"\nHistorical data preservation:")
    historical_data = source_council.figuresubmission_set.filter(
        year__id__lt=merge_from_year.id
    )
    print(f"  {historical_data.count()} submissions remain with source council for historical reference")

def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "="*60)
    print("CLEANING UP TEST DATA")
    print("="*60)
    
    # Delete test submissions
    FigureSubmission.objects.filter(
        council__name__in=["Test Borough Council", "Test Unitary Council"]
    ).delete()
    
    # Delete test councils
    Council.objects.filter(
        name__in=["Test Borough Council", "Test Unitary Council"]
    ).delete()
    
    print("Test data cleaned up")

if __name__ == "__main__":
    try:
        test_merge_logic()
    finally:
        cleanup_test_data()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("The enhanced merge functionality should now handle:")
    print("1. Year-based cutoffs for data migration")
    print("2. Conflict resolution by updating target data")
    print("3. Historical data preservation")
    print("4. Proper status management")
