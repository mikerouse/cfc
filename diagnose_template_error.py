#!/usr/bin/env python3
"""
Diagnostic script to identify and debug TemplateSyntaxError issues.
Specifically designed to diagnose the /list URL template issue.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.template import Template, Context, TemplateSyntaxError
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist
from django.contrib.auth.models import User
from council_finance.models import Council, CouncilList, DataField, FinancialYear


def diagnose_template(template_path):
    """Diagnose a specific template for syntax errors."""
    print(f"\n{'='*70}")
    print(f"DIAGNOSING TEMPLATE: {template_path}")
    print(f"{'='*70}\n")
    
    try:
        # Step 1: Try to load the template
        print("Step 1: Loading template...")
        template = get_template(template_path)
        print("[OK] Template loaded successfully!")
        
        # Step 2: Check template source for common issues
        print("\nStep 2: Checking template source...")
        template_source = template.source
        
        # Common syntax error patterns
        error_patterns = [
            ('{% endblock', 'Missing closing %}'),
            ('{% block', 'Missing closing %}'),
            ('{% if ', 'Missing closing %}'),
            ('{% for ', 'Missing closing %}'),
            ('{{', 'Unclosed variable tag'),
            ('{%', 'Unclosed template tag'),
            ('{% end ', 'Space before end tag'),
        ]
        
        lines = template_source.split('\n')
        issues_found = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for unclosed tags
            if line.count('{{') != line.count('}}'):
                issues_found.append(f"Line {line_num}: Mismatched variable tags {{{{ }}}}")
            if line.count('{%') != line.count('%}'):
                issues_found.append(f"Line {line_num}: Mismatched template tags {{% %}}")
                
            # Check for common typos
            if '{% end' in line and 'end ' in line:
                issues_found.append(f"Line {line_num}: Space after 'end' in tag")
            if '{%load' in line:
                issues_found.append(f"Line {line_num}: Missing space after {{% tag")
        
        if issues_found:
            print("[WARNING] Potential issues found:")
            for issue in issues_found:
                print(f"   - {issue}")
        else:
            print("[OK] No obvious syntax issues detected")
        
        # Step 3: Try to render with minimal context
        print("\nStep 3: Attempting to render with minimal context...")
        
        # Create minimal context
        context = {
            'user': None,
            'request': None,
            'lists': [],
            'favourites': [],
            'default_list': None,
            'form': None,
            'years': [],
            'default_year': None,
            'populations': {},
            'pop_totals': {},
            'metric_choices': [],
            'default_metric': 'total_debt',
            'list_meta': [],
            'page_title': 'My Lists',
        }
        
        try:
            rendered = template.render(context)
            print(f"[OK] Template rendered successfully! ({len(rendered)} characters)")
        except Exception as render_error:
            print(f"[ERROR] Rendering failed: {type(render_error).__name__}: {render_error}")
            
            # Try to get more specific error location
            if hasattr(render_error, 'token') and render_error.token:
                print(f"   Error token: {render_error.token}")
            if hasattr(render_error, 'template_debug'):
                print(f"   Debug info: {render_error.template_debug}")
        
        # Step 4: Check for template inheritance issues
        print("\nStep 4: Checking template inheritance...")
        
        # Look for extends tag
        extends_found = False
        base_template = None
        for line in lines[:10]:  # Check first 10 lines
            if '{% extends' in line:
                extends_found = True
                # Extract base template name
                import re
                match = re.search(r'{%\s*extends\s*["\']([^"\']+)["\']', line)
                if match:
                    base_template = match.group(1)
                break
        
        if extends_found:
            print(f"   Template extends: {base_template}")
            if base_template:
                try:
                    base = get_template(base_template)
                    print(f"   [OK] Base template '{base_template}' found")
                except TemplateDoesNotExist:
                    print(f"   [ERROR] Base template '{base_template}' NOT FOUND!")
        else:
            print("   No template inheritance detected")
        
        # Step 5: Check for missing template tags
        print("\nStep 5: Checking for required template tags...")
        
        required_tags = ['load static', 'csrf_token']
        template_text = template_source.lower()
        
        for tag in required_tags:
            if tag in template_text or tag.replace(' ', '') in template_text:
                print(f"   [OK] Found: {tag}")
            else:
                print(f"   [WARNING] Missing: {tag} (may be in base template)")
        
        return True
        
    except TemplateSyntaxError as e:
        print(f"\n[ERROR] TEMPLATE SYNTAX ERROR DETECTED!")
        print(f"   Error: {e}")
        
        # Try to extract more details
        if hasattr(e, 'token') and e.token:
            print(f"   Token: {e.token}")
            print(f"   Token type: {e.token.token_type if hasattr(e.token, 'token_type') else 'Unknown'}")
            
        if hasattr(e, 'template_debug'):
            print(f"   Template debug: {e.template_debug}")
            
        # Try to find the error location
        error_msg = str(e)
        import re
        line_match = re.search(r'line (\d+)', error_msg, re.IGNORECASE)
        if line_match:
            line_num = int(line_match.group(1))
            print(f"\n   Error at line {line_num}:")
            
            # Try to show context around error
            try:
                with open(template.origin.name, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    start = max(0, line_num - 3)
                    end = min(len(lines), line_num + 2)
                    
                    for i in range(start, end):
                        prefix = ">>>" if i == line_num - 1 else "   "
                        print(f"   {prefix} {i+1}: {lines[i].rstrip()}")
            except:
                pass
                
        return False
        
    except TemplateDoesNotExist as e:
        print(f"\n[ERROR] TEMPLATE NOT FOUND: {e}")
        return False
        
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_related_templates():
    """Check all templates that might be related to the my_lists page."""
    print("\n" + "="*70)
    print("CHECKING RELATED TEMPLATES")
    print("="*70)
    
    related_templates = [
        'council_finance/my_lists_enhanced.html',
        'council_finance/my_lists.html',  # In case there's an old version
        'base.html',
        'council_finance/base.html',
    ]
    
    for template in related_templates:
        try:
            get_template(template)
            print(f"[OK] {template} - EXISTS")
        except TemplateDoesNotExist:
            print(f"[ERROR] {template} - NOT FOUND")
        except TemplateSyntaxError as e:
            print(f"[ERROR] {template} - SYNTAX ERROR: {e}")


def main():
    """Main diagnostic function."""
    print("\n" + "="*70)
    print("TEMPLATE SYNTAX ERROR DIAGNOSTIC TOOL")
    print("="*70)
    print("Diagnosing template issues for /lists/ URL...")
    
    # First check what template the view is trying to use
    print("\nView Information:")
    print("   URL: /lists/")
    print("   View: council_finance.views.general.my_lists")
    print("   Template: council_finance/my_lists_enhanced.html")
    
    # Check for related templates
    check_related_templates()
    
    # Diagnose the main template
    success = diagnose_template('council_finance/my_lists_enhanced.html')
    
    if success:
        print("\n[OK] No template syntax errors detected!")
        print("   The error might be:")
        print("   - A runtime error (check context variables)")
        print("   - An error in an included template")
        print("   - An error in a template tag")
    else:
        print("\n[ERROR] Template syntax error found!")
        print("   Fix the error and run this script again.")
    
    print("\n" + "="*70)
    print("Diagnostic complete.")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()