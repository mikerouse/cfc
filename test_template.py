#!/usr/bin/env python3
"""
Quick test script to verify the enhanced_edit_figures_table.html template compiles without errors
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.template.loader import get_template
from django.template import Context

def test_template():
    try:
        # Try to load the template
        template = get_template('council_finance/enhanced_edit_figures_table.html')
        print("✅ Template loaded successfully")
        
        # Try to render with minimal context
        context = {
            'figures': [],
            'pending_pairs': set(),
        }
        
        rendered = template.render(context)
        print("✅ Template rendered successfully")
        print(f"   Rendered length: {len(rendered)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Template error: {e}")
        return False

if __name__ == '__main__':
    print("Testing enhanced_edit_figures_table.html template...")
    success = test_template()
    sys.exit(0 if success else 1)
