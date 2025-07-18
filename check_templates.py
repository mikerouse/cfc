#!/usr/bin/env python3
"""
Enhanced Django template syntax checker
Usage: python check_templates.py [template_name] [--verbose] [--strict]

This script can be run from the command line to quickly check template syntax.
If no template name is provided, it checks all templates.

Options:
  --verbose    Show detailed analysis and warnings
  --strict     Treat warnings as errors
"""
import os
import sys
import django
import re
from pathlib import Path
from collections import defaultdict

def setup_django():
    """Set up the Django environment once."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "council_finance.settings")
    django.setup()

def parse_arguments():
    """Parse command line arguments"""
    args = {
        'template_name': None,
        'verbose': False,
        'strict': False
    }
    
    for arg in sys.argv[1:]:
        if arg == '--verbose':
            args['verbose'] = True
        elif arg == '--strict':
            args['strict'] = True
        elif not arg.startswith('--'):
            args['template_name'] = arg
    
    return args

def validate_html_structure(content, template_path):
    """Validate HTML structure for common issues"""
    issues = []
    
    # Check for unclosed HTML tags
    html_tag_pattern = r'<(\w+)(?:\s[^>]*)?>'
    closing_tag_pattern = r'</(\w+)>'
    
    # Self-closing tags that don't need closing tags
    self_closing = {'img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}
    
    # Find all opening and closing tags
    opening_tags = re.findall(html_tag_pattern, content)
    closing_tags = re.findall(closing_tag_pattern, content)
    
    # Count tags
    tag_counts = defaultdict(int)
    for tag in opening_tags:
        if tag.lower() not in self_closing:
            tag_counts[tag.lower()] += 1
    
    for tag in closing_tags:
        tag_counts[tag.lower()] -= 1
    
    # Report unclosed tags
    for tag, count in tag_counts.items():
        if count > 0:
            issues.append(f"Unclosed HTML tag: <{tag}> (missing {count} closing tag(s))")
        elif count < 0:
            issues.append(f"Extra closing tag: </{tag}> (extra {abs(count)} closing tag(s))")
    
    return issues

def validate_django_template_structure(content, template_path):
    """Validate Django template tag structure"""
    issues = []
    
    # Django template tags that require closing tags
    block_tags = {
        'if': 'endif',
        'for': 'endfor',
        'with': 'endwith',
        'block': 'endblock',
        'comment': 'endcomment',
        'filter': 'endfilter',
        'spaceless': 'endspaceless',
        'verbatim': 'endverbatim',
        'autoescape': 'endautoescape',
        'blocktrans': 'endblocktrans',
        'trans': None,  # No closing tag needed
        'load': None,   # No closing tag needed
        'extends': None,  # No closing tag needed
        'include': None,  # No closing tag needed
    }
    
    # Find all Django template tags
    django_tag_pattern = r'{%\s*(\w+)(?:\s[^%]*)?%}'
    matches = re.finditer(django_tag_pattern, content)
    
    tag_stack = []
    line_number = 1
    
    for match in matches:
        tag = match.group(1)
        
        # Count line numbers up to this match
        line_number += content[:match.start()].count('\n') - (line_number - 1)
        
        if tag.startswith('end'):
            # This is a closing tag
            expected_tag = tag[3:]  # Remove 'end' prefix
            if not tag_stack:
                issues.append(f"Line {line_number}: Unexpected closing tag {{% {tag} %}} - no matching opening tag")
            else:
                opening_tag, opening_line = tag_stack.pop()
                if opening_tag != expected_tag:
                    issues.append(f"Line {line_number}: Mismatched closing tag {{% {tag} %}} - expected {{% end{opening_tag} %}} (opened at line {opening_line})")
        
        elif tag in block_tags:
            # This is an opening tag that needs a closing tag
            if block_tags[tag] is not None:
                tag_stack.append((tag, line_number))
        
        elif tag in ['else', 'elif', 'elseif', 'empty']:
            # These tags should only appear within certain blocks
            if not tag_stack:
                issues.append(f"Line {line_number}: {{% {tag} %}} tag used outside of a block")
            else:
                current_block, _ = tag_stack[-1]
                if tag in ['else', 'elif', 'elseif'] and current_block not in ['if', 'for']:
                    issues.append(f"Line {line_number}: {{% {tag} %}} tag used outside of if/for block")
                elif tag == 'empty' and current_block != 'for':
                    issues.append(f"Line {line_number}: {{% empty %}} tag used outside of for loop")
    
    # Check for unclosed tags
    for tag, line_number in tag_stack:
        issues.append(f"Line {line_number}: Unclosed Django tag {{% {tag} %}} - missing {{% end{tag} %}}")
    
    return issues

def validate_template_syntax(content, template_path):
    """Validate template for various syntax issues"""
    issues = []
    
    # Check for common Django template syntax errors
    
    # 1. Malformed template tags
    malformed_tags = re.findall(r'{%[^%]*[^%}](?:%}|$)', content)
    if malformed_tags:
        issues.append(f"Malformed template tags found: {len(malformed_tags)} instances")
    
    # 2. Malformed template variables
    malformed_vars = re.findall(r'{{[^}]*[^}](?:}}|$)', content)
    if malformed_vars:
        issues.append(f"Malformed template variables found: {len(malformed_vars)} instances")
    
    # 3. Check for common typos in template tags
    common_typos = {
        'endfi': 'endif',
        'endof': 'endfor',
        'edfor': 'endfor',
        'edif': 'endif',
        'eles': 'else',
        'esle': 'else',
    }
    
    for typo, correction in common_typos.items():
        if re.search(r'{%\s*' + typo + r'\s*%}', content):
            issues.append(f"Possible typo: '{typo}' should be '{correction}'")
    
    # 4. Check for unescaped quotes in template variables
    unescaped_quotes = re.findall(r'{{[^}]*"[^"]*"[^}]*}}', content)
    if unescaped_quotes:
        issues.append(f"Potential unescaped quotes in template variables: {len(unescaped_quotes)} instances")
    
    # 5. Check for missing load tags for filters
    if re.search(r'\|humanize\b', content) and not re.search(r'{%\s*load\s+humanize\s*%}', content):
        issues.append("Using 'humanize' filter without {% load humanize %}")
    
    if re.search(r'\|static\b', content) and not re.search(r'{%\s*load\s+static\s*%}', content):
        issues.append("Using 'static' filter without {% load static %}")
    
    return issues

def check_template_advanced(template_path, verbose=False, strict=False):
    """Check a template for syntax errors and additional issues"""
    from django.template.loader import get_template
    from django.template import TemplateSyntaxError
    
    issues = []
    warnings = []
    
    try:
        # First, try to load the template (basic syntax check)
        template = get_template(template_path)
        
        # Read the template content for additional checks
        template_file = None
        for template_dir in [Path('council_finance/templates'), Path('core/templates')]:
            potential_path = template_dir / template_path
            if potential_path.exists():
                template_file = potential_path
                break
        
        if template_file:
            content = template_file.read_text(encoding='utf-8')
            
            # Perform additional validations
            html_issues = validate_html_structure(content, template_path)
            django_issues = validate_django_template_structure(content, template_path)
            syntax_issues = validate_template_syntax(content, template_path)
            
            issues.extend(html_issues)
            issues.extend(django_issues)
            issues.extend(syntax_issues)
            
            # Check for potential warnings
            if len(content.split('\n')) > 1000:
                warnings.append("Template is very long (>1000 lines) - consider breaking it up")
            
            if content.count('{{') > 100:
                warnings.append("Template has many variables (>100) - consider optimization")
            
            if content.count('{%') > 50:
                warnings.append("Template has many template tags (>50) - consider simplification")
        
        # Report results
        if issues:
            print(f"❌ {template_path} - {len(issues)} ERROR(S)")
            if verbose:
                for issue in issues:
                    print(f"   ERROR: {issue}")
            return False
        elif warnings and (verbose or strict):
            print(f"⚠️  {template_path} - {len(warnings)} WARNING(S)")
            if verbose:
                for warning in warnings:
                    print(f"   WARNING: {warning}")
            return not strict  # Return False if strict mode treats warnings as errors
        else:
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
    args = parse_arguments()
    
    if args['template_name']:
        # Check specific template
        template_name = args['template_name']
        print(f"🧪 Checking template: {template_name}")
        print("-" * 60)
        success = check_template_advanced(template_name, verbose=args['verbose'], strict=args['strict'])
        sys.exit(0 if success else 1)
    else:
        # Check all templates
        templates = find_all_templates()
        print(f"🧪 Enhanced Django Template Checker")
        print("=" * 60)
        print(f"Checking {len(templates)} templates...")
        
        if args['verbose']:
            print("Running in VERBOSE mode - showing detailed analysis")
        if args['strict']:
            print("Running in STRICT mode - treating warnings as errors")
        
        print("-" * 60)
        
        passed = 0
        failed = 0
        
        for template in templates:
            if check_template_advanced(template, verbose=args['verbose'], strict=args['strict']):
                passed += 1
            else:
                failed += 1
        
        print("-" * 60)
        print(f"📊 Results: {passed} passed, {failed} failed")
        
        if failed > 0:
            print("❌ Some templates have issues!")
            sys.exit(1)
        else:
            print("✅ All templates passed!")
            sys.exit(0)

if __name__ == '__main__':
    main()
