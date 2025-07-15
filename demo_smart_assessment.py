#!/usr/bin/env python
"""
Demo script to show the difference between old and smart data quality assessment.

This script demonstrates how the smart assessment system solves the problem 
of excessive false positive missing data issues.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from council_finance.models import FinancialYear, DataIssue, Council, DataField
from council_finance.data_quality import assess_data_issues_simple
from council_finance.smart_data_quality import smart_assess_data_issues, get_data_collection_priorities


def demo_data_quality_comparison():
    """Demonstrate the difference between old and smart assessment."""
    print("=" * 60)
    print("🎯 SMART DATA QUALITY ASSESSMENT DEMO")
    print("=" * 60)
    
    # Show current system state
    print("\n📊 CURRENT SYSTEM STATE:")
    print(f"  Financial Years: {FinancialYear.objects.count()}")
    print(f"  Active Councils: {Council.objects.filter(status='active').count()}")
    print(f"  Financial Fields: {DataField.objects.exclude(category='characteristic').count()}")
    print(f"  Characteristic Fields: {DataField.objects.filter(category='characteristic').count()}")
    
    # Show financial years
    print("\n📅 FINANCIAL YEARS:")
    for year in FinancialYear.objects.all().order_by('label'):
        figure_count = year.get_figure_count() if hasattr(year, 'get_figure_count') else 0
        current_flag = " (CURRENT)" if getattr(year, 'is_current', False) else ""
        print(f"  {year.label}: {figure_count} figures{current_flag}")
    
    # Calculate theoretical maximum issues
    councils = Council.objects.filter(status='active').count()
    financial_fields = DataField.objects.exclude(category='characteristic').count()
    years = FinancialYear.objects.count()
    theoretical_max = councils * financial_fields * years
    
    print(f"\n🧮 THEORETICAL COMBINATIONS:")
    print(f"  {councils} councils × {financial_fields} fields × {years} years")
    print(f"  = {theoretical_max:,} potential financial data issues")
    
    # Show current issues
    current_issues = DataIssue.objects.count()
    financial_issues = DataIssue.objects.filter(
        issue_type='missing'
    ).exclude(field__category='characteristic').count()
    char_issues = DataIssue.objects.filter(
        issue_type='missing', 
        field__category='characteristic'
    ).count()
    
    print(f"\n📋 CURRENT DATA ISSUES:")
    print(f"  Total: {current_issues:,}")
    print(f"  Missing Financial: {financial_issues:,}")
    print(f"  Missing Characteristics: {char_issues:,}")
    
    # Run smart assessment
    print(f"\n🎯 RUNNING SMART ASSESSMENT...")
    smart_count = smart_assess_data_issues()
    
    # Show results
    new_total = DataIssue.objects.count()
    new_financial = DataIssue.objects.filter(
        issue_type='missing'
    ).exclude(field__category='characteristic').count()
    new_char = DataIssue.objects.filter(
        issue_type='missing', 
        field__category='characteristic'
    ).count()
    
    print(f"\n✅ SMART ASSESSMENT RESULTS:")
    print(f"  Created Issues: {smart_count:,}")
    print(f"  Total Issues: {new_total:,}")
    print(f"  Missing Financial: {new_financial:,}")
    print(f"  Missing Characteristics: {new_char:,}")
    
    # Show the difference
    reduction = financial_issues - new_financial
    if reduction > 0:
        percentage_reduction = (reduction / max(financial_issues, 1)) * 100
        print(f"\n🎉 IMPROVEMENT:")
        print(f"  Reduced financial issues by: {reduction:,} ({percentage_reduction:.1f}%)")
        print(f"  From {financial_issues:,} → {new_financial:,}")
    
    # Show data collection priorities
    priorities = get_data_collection_priorities()
    relevant_years = priorities.get('relevant_years', [])
    current_year = priorities.get('current_year')
    
    print(f"\n🎯 DATA COLLECTION PRIORITIES:")
    print(f"  Current Year: {current_year.label if current_year else 'None set'}")
    print(f"  Relevant Years: {[y.label for y in relevant_years]}")
    
    year_stats = priorities.get('year_stats', [])
    if year_stats:
        print(f"\n📈 YEAR COMPLETENESS:")
        for stat in year_stats:
            completeness = stat['completeness']
            current_flag = " (CURRENT)" if stat['is_current'] else ""
            print(f"  {stat['year'].label}: {completeness:.1f}% complete{current_flag}")
    
    print(f"\n💡 EXPLANATION:")
    print(f"The smart assessment system only flags missing data for:")
    print(f"  • Characteristic fields (apply to all councils)")
    print(f"  • Financial fields for relevant/current years only")
    print(f"  • Years that are marked as active for data collection")
    print(f"")
    print(f"This eliminates {reduction:,} false positive issues that were")
    print(f"being generated for financial years with no actual data.")


if __name__ == '__main__':
    demo_data_quality_comparison()
