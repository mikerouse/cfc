#!/usr/bin/env python3
"""Simple test for the enhanced_edit_figures_table.html template"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.template.loader import get_template

try:
    template = get_template('council_finance/enhanced_edit_figures_table.html')
    print("✅ Template loads successfully - no syntax errors")
except Exception as e:
    print(f"❌ Template error: {e}")
    sys.exit(1)
