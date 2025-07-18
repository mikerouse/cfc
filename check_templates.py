#!/usr/bin/env python3
"""
Simple Django template syntax checker
Usage: python check_templates.py [template_name]

This script can be run from the command line to quickly check template syntax.
If no template name is provided, it checks all templates.
"""
import os
import sys
import django
from pathlib import Path

def setup_django():
    """Setup Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
    django.setup()

def check_template(template_path):
    """Check a single template for syntax errors"""
    from django.template.loader import get_template
    from django.template import TemplateSyntaxError
    
    try:
        template = get_template(template_path)
        print(f"✅ {template_path} - OK")
        return True
    except TemplateSyntaxError as e:
        print(f"❌ {template_path} - SYNTAX ERROR: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {template_path} - ERROR: {e}")
        return False

def find_all_templates():
    """Find all template files in the project"""
    templates = []
    template_dirs = [
        Path('council_finance/templates'),
        Path('core/templates'),
    ]
    
    for template_dir in template_dirs:
        if template_dir.exists():
            for html_file in template_dir.rglob('*.html'):
                # Get relative path from templates directory
                rel_path = html_file.relative_to(template_dir)
                templates.append(str(rel_path))
                
    return sorted(list(set(templates)))

def main():
    setup_django()
    
    if len(sys.argv) > 1:
        # Check specific template
        template_name = sys.argv[1]
        print(f"🧪 Checking template: {template_name}")
        success = check_template(template_name)
        sys.exit(0 if success else 1)
    else:
        # Check all templates
        templates = find_all_templates()
        print(f"🧪 Checking {len(templates)} templates...")
        print("-" * 50)
        
        passed = 0
        failed = 0
        
        for template in templates:
            if check_template(template):
                passed += 1
            else:
                failed += 1
        
        print("-" * 50)
        print(f"📊 Results: {passed} passed, {failed} failed")
        
        if failed > 0:
            print("❌ Some templates have syntax errors!")
            sys.exit(1)
        else:
            print("✅ All templates passed!")
            sys.exit(0)

if __name__ == '__main__':
    main()
