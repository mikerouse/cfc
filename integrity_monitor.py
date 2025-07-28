#!/usr/bin/env python
"""
Factoid System Integrity Monitor

Run this script periodically to ensure the factoid system is working correctly.
It checks the entire pipeline from models to frontend integration.

Usage:
    python manage.py runscript integrity_monitor
    python integrity_monitor.py  # Direct execution
"""
import os
import sys
import django

# Setup Django if running directly
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
    django.setup()

from django.test import Client
from council_finance.models.factoid import FactoidTemplate, FactoidInstance
from council_finance.models.counter import CounterDefinition
from council_finance.models.council import Council, FinancialYear
from council_finance.models.field import DataField
from council_finance.services.factoid_engine import FactoidEngine
import json


def run():
    """Main monitoring function"""
    print("🔍 Factoid System Integrity Monitor")
    print("=" * 50)
    
    issues = []
    warnings = []
    
    # 1. Check field dependencies
    print("\n1. Checking field dependencies...")
    field_issues = check_field_dependencies()
    issues.extend(field_issues)
    
    # 2. Check API endpoints
    print("2. Checking API endpoints...")
    api_issues = check_api_endpoints()
    issues.extend(api_issues)
    
    # 3. Check frontend integration
    print("3. Checking frontend integration...")
    frontend_issues = check_frontend_integration()
    issues.extend(frontend_issues)
    
    # 4. Check factoid computation
    print("4. Checking factoid computation...")
    computation_issues = check_factoid_computation()
    issues.extend(computation_issues)
    
    # 5. Check for stale instances
    print("5. Checking for stale instances...")
    stale_issues = check_stale_instances()
    warnings.extend(stale_issues)
    
    # Report results
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print(f"❌ Critical Issues: {len(issues)}")
    print(f"⚠️  Warnings: {len(warnings)}")
    
    if issues:
        print("\n🚨 CRITICAL ISSUES:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if not issues and not warnings:
        print("\n✅ All systems are working correctly!")
    
    return len(issues) == 0


def check_field_dependencies():
    """Check if all referenced fields in templates exist"""
    issues = []
    
    # Define virtual fields that are computed, not stored
    virtual_fields = {
        'council_name', 'year_label', 'council_slug', 'council_type'
    }
    
    for template in FactoidTemplate.objects.filter(is_active=True):
        for field_name in template.referenced_fields:
            field_var_name = field_name.replace('-', '_')
            
            if field_var_name in virtual_fields:
                continue  # Virtual fields are okay
                
            try:
                DataField.from_variable_name(field_var_name)
            except DataField.DoesNotExist:
                issues.append(f"Template '{template.name}' references non-existent field '{field_name}'")
    
    print(f"   Found {len(issues)} field dependency issues")
    return issues


def check_api_endpoints():
    """Check if API endpoints are working"""
    issues = []
    client = Client()
    
    endpoints = [
        '/api/factoid/counter/worcestershire/total-debt/',
        '/api/factoid/counter/worcestershire/total-debt/2024/25/',
        '/api/factoids/counter/total-debt/worcestershire/2024-25/',
    ]
    
    for endpoint in endpoints:
        try:
            response = client.get(endpoint)
            if response.status_code != 200:
                issues.append(f"API endpoint {endpoint} returned status {response.status_code}")
        except Exception as e:
            issues.append(f"API endpoint {endpoint} failed: {str(e)}")
    
    print(f"   Tested {len(endpoints)} endpoints, {len(issues)} failures")
    return issues


def check_frontend_integration():
    """Check if frontend can get factoids"""
    issues = []
    
    try:
        client = Client()
        response = client.get('/councils/worcestershire/')
        
        if response.status_code != 200:
            issues.append(f"Council detail page returned status {response.status_code}")
        else:
            content = response.content.decode()
            if 'counter-factoid' not in content:
                issues.append("Council detail page missing factoid containers")
    except Exception as e:
        issues.append(f"Frontend integration check failed: {str(e)}")
    
    print(f"   Frontend integration: {len(issues)} issues")
    return issues


def check_factoid_computation():
    """Check if factoids are computing correctly"""
    issues = []
    
    try:
        engine = FactoidEngine()
        council = Council.objects.get(slug='worcestershire')
        year = FinancialYear.objects.get(label='2024/25')
        counter = CounterDefinition.objects.get(slug='total-debt')
        
        factoids = engine.get_factoids_for_counter(counter, council, year)
        
        if len(factoids) == 0:
            issues.append("No factoids computed for total-debt counter")
        else:
            # Check for N/A values in rendered text
            na_count = sum(1 for f in factoids if 'N/A' in f.rendered_text)
            if na_count > len(factoids) * 0.5:  # More than 50% showing N/A
                issues.append(f"Too many factoids showing N/A values ({na_count}/{len(factoids)})")
    
    except Exception as e:
        issues.append(f"Factoid computation failed: {str(e)}")
    
    print(f"   Factoid computation: {len(issues)} issues")
    return issues


def check_stale_instances():
    """Check for potentially stale factoid instances"""
    warnings = []
    
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Find instances older than 1 day
        old_threshold = timezone.now() - timedelta(days=1)
        old_instances = FactoidInstance.objects.filter(computed_at__lt=old_threshold)
        
        if old_instances.count() > 50:
            warnings.append(f"Found {old_instances.count()} factoid instances older than 1 day")
        
        # Check for expired instances that haven't been cleaned up
        expired_instances = FactoidInstance.objects.filter(expires_at__lt=timezone.now())
        if expired_instances.count() > 10:
            warnings.append(f"Found {expired_instances.count()} expired instances that should be cleaned up")
    
    except Exception as e:
        warnings.append(f"Stale instance check failed: {str(e)}")
    
    print(f"   Stale instances: {len(warnings)} warnings")
    return warnings


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
