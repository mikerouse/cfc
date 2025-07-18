#!/usr/bin/env python3
"""
Test the enhanced template checker with a template containing errors
"""
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

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
    }
    
    # Find all Django template tags
    django_tag_pattern = r'{%\s*(\w+)(?:\s[^%]*)?%}'
    matches = re.finditer(django_tag_pattern, content)
    
    tag_stack = []
    content_lines = content.split('\n')
    
    for match in matches:
        tag = match.group(1)
        
        # Find line number
        line_number = content[:match.start()].count('\n') + 1
        
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
    
    # 4. Check for missing load tags for filters
    if re.search(r'{%\s*static\s', content) and not re.search(r'{%\s*load\s+static\s*%}', content):
        issues.append("Using 'static' tag without {% load static %}")
    
    return issues

def test_error_template():
    """Test the enhanced checker on a template with intentional errors"""
    
    test_file = Path('test_error_template.html')
    if not test_file.exists():
        print("❌ Test template not found!")
        return
    
    content = test_file.read_text(encoding='utf-8')
    
    print("🧪 Testing Enhanced Template Checker")
    print("=" * 50)
    print(f"Testing template: {test_file}")
    print("-" * 50)
    
    # Test HTML structure validation
    html_issues = validate_html_structure(content, str(test_file))
    print(f"\n🔍 HTML Structure Issues Found: {len(html_issues)}")
    for issue in html_issues:
        print(f"   ❌ {issue}")
    
    # Test Django template structure validation
    django_issues = validate_django_template_structure(content, str(test_file))
    print(f"\n🔍 Django Template Issues Found: {len(django_issues)}")
    for issue in django_issues:
        print(f"   ❌ {issue}")
    
    # Test template syntax validation
    syntax_issues = validate_template_syntax(content, str(test_file))
    print(f"\n🔍 Template Syntax Issues Found: {len(syntax_issues)}")
    for issue in syntax_issues:
        print(f"   ❌ {issue}")
    
    total_issues = len(html_issues) + len(django_issues) + len(syntax_issues)
    print(f"\n📊 Total Issues Found: {total_issues}")
    
    if total_issues > 0:
        print("✅ Enhanced checker successfully detected template issues!")
    else:
        print("⚠️  No issues found - check the validation logic")

if __name__ == '__main__':
    test_error_template()
