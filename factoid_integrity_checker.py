#!/usr/bin/env python
"""
End-to-End Factoid System Integrity Checker

This script validates the entire factoid pipeline from councils and counters
to templates, data fields, and final rendering to catch production issues.
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.test import Client
from council_finance.models.factoid import FactoidTemplate, FactoidInstance
from council_finance.models.counter import CounterDefinition
from council_finance.models.council import Council, FinancialYear
from council_finance.models.field import DataField
from council_finance.services.factoid_engine import FactoidEngine
import json


class FactoidIntegrityChecker:
    """Comprehensive factoid system integrity checker"""
    
    def __init__(self):
        self.client = Client()
        self.engine = FactoidEngine()
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def log_issue(self, category, message, details=None):
        """Log a critical issue"""
        issue = {
            'category': category,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.issues.append(issue)
        print(f"❌ ISSUE [{category}]: {message}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def log_warning(self, category, message, details=None):
        """Log a warning"""
        warning = {
            'category': category,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.warnings.append(warning)
        print(f"⚠️  WARNING [{category}]: {message}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def log_success(self, category, message, details=None):
        """Log a success"""
        success = {
            'category': category,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.successes.append(success)
        print(f"✅ SUCCESS [{category}]: {message}")
    
    def check_basic_models(self):
        """Check that basic models exist and are configured"""
        print("\n🔍 Checking Basic Models...")
        
        # Check councils
        councils = Council.objects.all()
        if not councils.exists():
            self.log_issue("MODELS", "No councils found in database")
        else:
            self.log_success("MODELS", f"Found {councils.count()} councils")
        
        # Check financial years
        years = FinancialYear.objects.all()
        if not years.exists():
            self.log_issue("MODELS", "No financial years found in database")
        else:
            self.log_success("MODELS", f"Found {years.count()} financial years")
        
        # Check counters
        counters = CounterDefinition.objects.all()
        if not counters.exists():
            self.log_issue("MODELS", "No counter definitions found")
        else:
            self.log_success("MODELS", f"Found {counters.count()} counter definitions")
        
        # Check factoid templates
        templates = FactoidTemplate.objects.filter(is_active=True)
        if not templates.exists():
            self.log_issue("MODELS", "No active factoid templates found")
        else:
            self.log_success("MODELS", f"Found {templates.count()} active factoid templates")
        
        return councils.exists() and years.exists() and counters.exists() and templates.exists()
    
    def check_counter_factoid_assignments(self):
        """Check that counters have factoid templates assigned"""
        print("\n🔍 Checking Counter-Factoid Assignments...")
        
        counters = CounterDefinition.objects.all()
        
        for counter in counters:
            assigned_templates = FactoidTemplate.objects.filter(
                counters=counter, 
                is_active=True
            )
            
            if assigned_templates.exists():
                self.log_success(
                    "ASSIGNMENTS", 
                    f"Counter '{counter.name}' has {assigned_templates.count()} factoid templates",
                    {"counter_slug": counter.slug, "template_count": assigned_templates.count()}
                )
            else:
                self.log_warning(
                    "ASSIGNMENTS", 
                    f"Counter '{counter.name}' has no factoid templates assigned",
                    {"counter_slug": counter.slug}
                )
    
    def check_template_field_dependencies(self):
        """Check that factoid templates reference valid fields"""
        print("\n🔍 Checking Template Field Dependencies...")
        
        # Define virtual/computed fields that are handled by the engine
        virtual_fields = {
            'council_name': 'Council name (computed)',
            'year_label': 'Financial year label (computed)', 
            'council_slug': 'Council slug (computed)',
            'council_type': 'Council type (computed)'
        }
        
        templates = FactoidTemplate.objects.filter(is_active=True)
        
        for template in templates:
            for field_name in template.referenced_fields:
                if field_name in virtual_fields:
                    self.log_success(
                        "FIELDS", 
                        f"Template '{template.name}' virtual field '{field_name}' is handled by engine",
                        {"template_slug": template.slug, "field_name": field_name, "type": "virtual"}
                    )
                else:
                    try:
                        field = DataField.from_variable_name(field_name)
                        self.log_success(
                            "FIELDS", 
                            f"Template '{template.name}' field '{field_name}' is valid",
                            {"template_slug": template.slug, "field_name": field_name, "type": "database"}
                        )
                    except DataField.DoesNotExist:
                        self.log_issue(
                            "FIELDS", 
                            f"Template '{template.name}' references non-existent field '{field_name}'",
                            {"template_slug": template.slug, "field_name": field_name}
                        )
    
    def check_data_availability(self):
        """Check that required data is available for factoid computation"""
        print("\n🔍 Checking Data Availability...")
        
        # Test with a known council and year
        try:
            council = Council.objects.first()
            year = FinancialYear.objects.first()
            
            if not council or not year:
                self.log_issue("DATA", "No council or financial year available for testing")
                return
            
            # Check some key fields including computed ones
            test_fields = [
                ('current_liabilities', 'database'),
                ('long_term_liabilities', 'database'), 
                ('council_name', 'computed'),
                ('year_label', 'computed')
            ]
            
            for field_name, field_type in test_fields:
                value = self.engine.get_field_value(field_name, council, year)
                if value is not None:
                    self.log_success(
                        "DATA", 
                        f"Field '{field_name}' ({field_type}) has data for {council.name} {year.label}",
                        {"council": council.slug, "year": year.label, "value": str(value)[:50], "type": field_type}
                    )
                else:
                    self.log_warning(
                        "DATA", 
                        f"Field '{field_name}' ({field_type}) has no data for {council.name} {year.label}",
                        {"council": council.slug, "year": year.label, "type": field_type}
                    )
        
        except Exception as e:
            self.log_issue("DATA", f"Error checking data availability: {e}")
    
    def check_factoid_computation(self):
        """Check that factoids can be computed successfully"""
        print("\n🔍 Checking Factoid Computation...")
        
        try:
            # Test with total-debt counter if it exists
            council = Council.objects.filter(slug='worcestershire').first()
            year = FinancialYear.objects.filter(label='2024/25').first()
            counter = CounterDefinition.objects.filter(slug='total-debt').first()
            
            if not all([council, year, counter]):
                self.log_warning("COMPUTATION", "Cannot test with Worcestershire/2024-25/total-debt - using defaults")
                council = Council.objects.first()
                year = FinancialYear.objects.first()
                counter = CounterDefinition.objects.first()
            
            if all([council, year, counter]):
                factoids = self.engine.get_factoids_for_counter(counter, council, year)
                
                if factoids:
                    self.log_success(
                        "COMPUTATION", 
                        f"Successfully computed {len(factoids)} factoids",
                        {
                            "council": council.name,
                            "year": year.label,
                            "counter": counter.name,
                            "factoid_count": len(factoids)
                        }
                    )
                    
                    # Check factoid quality
                    for factoid in factoids[:3]:  # Check first 3
                        if 'N/A' in factoid.rendered_text:
                            self.log_warning(
                                "QUALITY",
                                f"Factoid contains 'N/A' values: {factoid.template.name}",
                                {"template": factoid.template.slug, "text": factoid.rendered_text[:100]}
                            )
                        else:
                            self.log_success(
                                "QUALITY",
                                f"Factoid has valid data: {factoid.template.name}",
                                {"template": factoid.template.slug}
                            )
                else:
                    self.log_issue(
                        "COMPUTATION", 
                        "No factoids computed",
                        {"council": council.name, "year": year.label, "counter": counter.name}
                    )
            else:
                self.log_issue("COMPUTATION", "Cannot find test data for factoid computation")
        
        except Exception as e:
            self.log_issue("COMPUTATION", f"Error during factoid computation: {e}")
    
    def check_api_endpoints(self):
        """Check that API endpoints are working"""
        print("\n🔍 Checking API Endpoints...")
        
        # Test the new counter-based endpoint
        test_urls = [
            '/api/factoids/counter/total-debt/worcestershire/2024-25/',
            '/api/factoid/counter/worcestershire/total-debt/',
            '/api/factoid/counter/worcestershire/total-debt/2024/25/',
        ]
        
        for url in test_urls:
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    data = json.loads(response.content)
                    if isinstance(data, dict) and (data.get('success') or data.get('count') is not None):
                        factoid_count = data.get('count', len(data.get('factoids', [])))
                        self.log_success(
                            "API", 
                            f"Endpoint {url} working correctly",
                            {"status": response.status_code, "factoid_count": factoid_count}
                        )
                    else:
                        self.log_warning("API", f"Endpoint {url} returned unexpected format", {"response": str(data)[:200]})
                elif response.status_code == 404:
                    self.log_warning("API", f"Endpoint {url} not found", {"status": response.status_code})
                else:
                    self.log_issue("API", f"Endpoint {url} failed", {"status": response.status_code})
            
            except Exception as e:
                self.log_issue("API", f"Error testing endpoint {url}: {e}")
    
    def check_frontend_integration(self):
        """Check that frontend can load the council detail page"""
        print("\n🔍 Checking Frontend Integration...")
        
        try:
            # Test council detail page
            response = self.client.get('/councils/worcestershire/')
            if response.status_code == 200:
                content = response.content.decode()
                if 'counter-factoid' in content:
                    self.log_success("FRONTEND", "Council detail page contains factoid containers")
                else:
                    self.log_warning("FRONTEND", "Council detail page missing factoid containers")
            else:
                self.log_issue("FRONTEND", f"Council detail page failed to load", {"status": response.status_code})
        
        except Exception as e:
            self.log_issue("FRONTEND", f"Error checking frontend: {e}")
    
    def run_full_check(self):
        """Run all integrity checks"""
        print("🚀 Starting Factoid System Integrity Check...")
        print("=" * 60)
        
        # Run all checks
        if self.check_basic_models():
            self.check_counter_factoid_assignments()
            self.check_template_field_dependencies()
            self.check_data_availability()
            self.check_factoid_computation()
            self.check_api_endpoints()
            self.check_frontend_integration()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 INTEGRITY CHECK SUMMARY")
        print("=" * 60)
        
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Issues: {len(self.issues)}")
        
        if self.issues:
            print("\n🚨 CRITICAL ISSUES TO FIX:")
            for issue in self.issues:
                print(f"  - [{issue['category']}] {issue['message']}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS TO REVIEW:")
            for warning in self.warnings:
                print(f"  - [{warning['category']}] {warning['message']}")
        
        # Overall status
        if not self.issues:
            if not self.warnings:
                print("\n🎉 ALL CHECKS PASSED! System is healthy.")
            else:
                print("\n✅ NO CRITICAL ISSUES. Some warnings to review.")
        else:
            print("\n🚨 CRITICAL ISSUES FOUND. System needs attention.")
        
        return len(self.issues) == 0


if __name__ == "__main__":
    checker = FactoidIntegrityChecker()
    success = checker.run_full_check()
    sys.exit(0 if success else 1)
