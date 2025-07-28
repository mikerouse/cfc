"""
Data Quality Monitoring System

Provides runtime monitoring and alerting for data consistency issues,
helping to catch problems like the characteristics key mismatch early.
"""

import logging
from typing import Dict, Any, List, Optional
from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from council_finance.models import Council, DataField, FinancialYear
from council_finance.calculators import get_data_context_for_council
from council_finance.utils.data_context_validator import DataContextValidator

logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """Monitors data quality and consistency across the application."""
    
    def __init__(self):
        self.issues_found = []
        self.councils_checked = 0
        self.data_contexts_validated = 0
        
    def check_data_context_consistency(self, sample_size: int = 10) -> Dict[str, Any]:
        """
        Check data context consistency across a sample of councils.
        
        Args:
            sample_size: Number of councils to check (default 10)
            
        Returns:
            Dict with check results and any issues found
        """
        councils = Council.objects.all()[:sample_size]
        years = FinancialYear.objects.all()[:3]  # Check recent years
        
        issues = []
        total_checks = 0
        
        for council in councils:
            self.councils_checked += 1
            
            for year in years:
                total_checks += 1
                self.data_contexts_validated += 1
                
                try:
                    # Get data context
                    context = get_data_context_for_council(council, year=year)
                    
                    # Validate structure
                    validation_errors = DataContextValidator.validate_data_context(
                        context, f"monitor_check_{council.slug}_{year.label}"
                    )
                    
                    if validation_errors:
                        issues.append({
                            'council': council.name,
                            'council_slug': council.slug,
                            'year': year.label,
                            'type': 'validation_error',
                            'errors': validation_errors,
                            'timestamp': timezone.now()
                        })
                        
                    # Check for common issues
                    if 'characteristics' in context:  # Wrong plural form
                        issues.append({
                            'council': council.name,
                            'council_slug': council.slug,
                            'year': year.label,
                            'type': 'incorrect_key',
                            'issue': "Found 'characteristics' key instead of 'characteristic'",
                            'timestamp': timezone.now()
                        })
                        
                    # Check for empty data sections
                    empty_sections = []
                    for section in ['characteristic', 'financial', 'calculated']:
                        if section in context and not context[section]:
                            empty_sections.append(section)
                            
                    if empty_sections:
                        issues.append({
                            'council': council.name,
                            'council_slug': council.slug,
                            'year': year.label,
                            'type': 'empty_sections',
                            'empty_sections': empty_sections,
                            'timestamp': timezone.now()
                        })
                        
                except Exception as e:
                    issues.append({
                        'council': council.name,
                        'council_slug': council.slug,
                        'year': year.label,
                        'type': 'exception',
                        'error': str(e),
                        'timestamp': timezone.now()
                    })
                    
        self.issues_found.extend(issues)
        
        return {
            'total_checks': total_checks,
            'issues_count': len(issues),
            'issues': issues,
            'councils_checked': len(councils),
            'years_checked': len(years)
        }
    
    def check_field_naming_consistency(self) -> Dict[str, Any]:
        """Check field naming consistency across all data fields."""
        from council_finance.utils.field_naming import FieldNamingValidator
        
        fields = DataField.objects.all()
        issues = []
        
        for field in fields:
            # Validate slug
            slug_errors = FieldNamingValidator.validate_field_slug(field.slug)
            if slug_errors:
                issues.append({
                    'field_id': field.id,
                    'field_name': field.name,
                    'field_slug': field.slug,
                    'type': 'invalid_slug',
                    'errors': slug_errors,
                    'timestamp': timezone.now()
                })
                
            # Check slug/variable_name consistency
            expected_var_name = FieldNamingValidator.slug_to_variable_name(field.slug)
            if hasattr(field, 'variable_name') and field.variable_name != expected_var_name:
                issues.append({
                    'field_id': field.id,
                    'field_name': field.name,
                    'field_slug': field.slug,
                    'type': 'naming_inconsistency',
                    'expected_variable_name': expected_var_name,
                    'actual_variable_name': getattr(field, 'variable_name', 'N/A'),
                    'timestamp': timezone.now()
                })
                
        self.issues_found.extend(issues)
        
        return {
            'total_fields': len(fields),
            'issues_count': len(issues),
            'issues': issues
        }
    
    def check_formula_field_references(self) -> Dict[str, Any]:
        """Check that formula field references are valid."""
        from council_finance.utils.field_naming import FormulaFieldExtractor
        
        # Get fields with formulas
        formula_fields = DataField.objects.filter(category='calculated').exclude(formula__isnull=True).exclude(formula='')
        counter_fields = []
        
        try:
            from council_finance.models import CounterDefinition
            counter_fields = CounterDefinition.objects.exclude(formula__isnull=True).exclude(formula='')
        except ImportError:
            pass
            
        # Get all available field names
        all_fields = DataField.objects.all()
        available_fields = {}
        for field in all_fields:
            available_fields[field.slug] = field
            if hasattr(field, 'variable_name'):
                available_fields[field.variable_name] = field
                
        issues = []
        
        # Check calculated fields
        for field in formula_fields:
            validation_result = FormulaFieldExtractor.validate_formula_fields(
                field.formula, available_fields
            )
            
            if validation_result['invalid']:
                issues.append({
                    'field_type': 'calculated_field',
                    'field_id': field.id,
                    'field_name': field.name,
                    'field_slug': field.slug,
                    'formula': field.formula,
                    'type': 'invalid_references',
                    'invalid_references': validation_result['invalid'],
                    'timestamp': timezone.now()
                })
                
        # Check counter definitions
        for counter in counter_fields:
            validation_result = FormulaFieldExtractor.validate_formula_fields(
                counter.formula, available_fields
            )
            
            if validation_result['invalid']:
                issues.append({
                    'field_type': 'counter_definition',
                    'counter_id': counter.id,
                    'counter_name': counter.name,
                    'counter_slug': counter.slug,
                    'formula': counter.formula,
                    'type': 'invalid_references',
                    'invalid_references': validation_result['invalid'],
                    'timestamp': timezone.now()
                })
                
        self.issues_found.extend(issues)
        
        return {
            'calculated_fields_checked': len(formula_fields),
            'counter_definitions_checked': len(counter_fields),
            'issues_count': len(issues),
            'issues': issues
        }
    
    def generate_report(self) -> str:
        """Generate a human-readable report of all issues found."""
        if not self.issues_found:
            return "✅ No data quality issues found!"
            
        report_lines = [
            f"📊 Data Quality Monitor Report",
            f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Councils checked: {self.councils_checked}",
            f"Data contexts validated: {self.data_contexts_validated}",
            f"Total issues found: {len(self.issues_found)}",
            "",
            "🔍 Issues by Type:",
        ]
        
        # Group issues by type
        issues_by_type = {}
        for issue in self.issues_found:
            issue_type = issue['type']
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
            
        for issue_type, issues in issues_by_type.items():
            report_lines.append(f"  • {issue_type}: {len(issues)} issues")
            
        report_lines.append("")
        report_lines.append("📋 Detailed Issues:")
        
        for i, issue in enumerate(self.issues_found[:20], 1):  # Limit to first 20
            report_lines.append(f"{i}. {issue['type']} - {issue.get('council', 'N/A')}")
            if 'errors' in issue:
                for error in issue['errors'][:3]:  # Limit errors shown
                    report_lines.append(f"   Error: {error}")
            if 'issue' in issue:
                report_lines.append(f"   Issue: {issue['issue']}")
                
        if len(self.issues_found) > 20:
            report_lines.append(f"... and {len(self.issues_found) - 20} more issues")
            
        return "\n".join(report_lines)
    
    def send_alert_if_critical(self):
        """Send email alert if critical issues are found."""
        critical_types = ['validation_error', 'incorrect_key', 'exception']
        critical_issues = [i for i in self.issues_found if i['type'] in critical_types]
        
        if critical_issues and hasattr(settings, 'ADMINS') and settings.ADMINS:
            subject = f"🚨 Critical Data Quality Issues Found ({len(critical_issues)} issues)"
            message = self.generate_report()
            
            try:
                mail_admins(subject, message, fail_silently=False)
                logger.info(f"Data quality alert sent to admins: {len(critical_issues)} critical issues")
            except Exception as e:
                logger.error(f"Failed to send data quality alert: {e}")


class Command(BaseCommand):
    """Django management command to run data quality monitoring."""
    
    help = 'Run data quality monitoring checks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-size',
            type=int,
            default=10,
            help='Number of councils to check (default: 10)'
        )
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Send email alerts for critical issues'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        monitor = DataQualityMonitor()
        
        self.stdout.write("🔍 Starting data quality monitoring...")
        
        # Run all checks
        context_results = monitor.check_data_context_consistency(options['sample_size'])
        naming_results = monitor.check_field_naming_consistency()
        formula_results = monitor.check_formula_field_references()
        
        # Generate report
        report = monitor.generate_report()
        
        if options['verbose']:
            self.stdout.write(report)
        else:
            self.stdout.write(f"✅ Monitoring complete. {len(monitor.issues_found)} issues found.")
            
        # Send alerts if requested
        if options['send_alerts']:
            monitor.send_alert_if_critical()
            
        # Return non-zero exit code if issues found
        if monitor.issues_found:
            self.stdout.write(
                self.style.WARNING(f"⚠️ Found {len(monitor.issues_found)} data quality issues")
            )
            return 1
        else:
            self.stdout.write(self.style.SUCCESS("✅ No data quality issues found"))
            return 0
