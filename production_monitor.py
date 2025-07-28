#!/usr/bin/env python
"""
Production Factoid System Monitor

This script provides ongoing monitoring of the factoid system 
and alerts if critical issues are detected in production.
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from factoid_integrity_checker import FactoidIntegrityChecker


class ProductionMonitor:
    """Production monitoring for factoid system"""
    
    def __init__(self):
        self.checker = FactoidIntegrityChecker()
    
    def run_quick_health_check(self):
        """Run a quick health check focusing on critical issues"""
        print("🔍 Running Production Health Check...")
        
        # Check API endpoints are working
        self.checker.check_api_endpoints()
        
        # Check critical functionality
        self.checker.check_factoid_computation()
        
        # Summary for production
        critical_issues = len(self.checker.issues)
        
        if critical_issues == 0:
            print("✅ PRODUCTION STATUS: HEALTHY")
            return True
        else:
            print(f"🚨 PRODUCTION STATUS: {critical_issues} CRITICAL ISSUES")
            for issue in self.checker.issues:
                print(f"  ERROR: {issue['message']}")
            return False
    
    def generate_health_report(self):
        """Generate a health report for logging/monitoring systems"""
        success = self.run_quick_health_check()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if success else "unhealthy",
            "critical_issues": len(self.checker.issues),
            "warnings": len(self.checker.warnings),
            "successes": len(self.checker.successes),
            "issues": self.checker.issues,
            "warnings": self.checker.warnings
        }
        
        return report


if __name__ == "__main__":
    monitor = ProductionMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Output JSON for monitoring systems
        report = monitor.generate_health_report()
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["status"] == "healthy" else 1)
    else:
        # Human-readable output
        success = monitor.run_quick_health_check()
        sys.exit(0 if success else 1)
