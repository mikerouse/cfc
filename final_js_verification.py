#!/usr/bin/env python3
"""
Final JavaScript Error Verification Script
This script checks for common JavaScript error patterns that could cause null reference errors.
"""

import os
import re
from pathlib import Path

def check_js_file(file_path):
    """Check a JavaScript file for potential null reference issues."""
    issues = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for DOM element access without null checks
            if re.search(r'document\.getElementById\([^)]+\)\.[a-zA-Z]', line):
                if not re.search(r'if\s*\([^)]*document\.getElementById', line) and \
                   not re.search(r'document\.getElementById[^;]*&&', line) and \
                   not re.search(r'const\s+\w+\s*=\s*document\.getElementById', line):
                    issues.append(f"Line {i}: Potential null reference - {line.strip()}")
            
            # Check for querySelector access without null checks
            if re.search(r'document\.querySelector\([^)]+\)\.[a-zA-Z]', line):
                if not re.search(r'if\s*\([^)]*document\.querySelector', line) and \
                   not re.search(r'document\.querySelector[^;]*&&', line) and \
                   not re.search(r'const\s+\w+\s*=\s*document\.querySelector', line):
                    issues.append(f"Line {i}: Potential null reference - {line.strip()}")
            
            # Check for .value assignments without null checks
            if re.search(r'\w+\.value\s*=', line):
                var_name = re.search(r'(\w+)\.value\s*=', line)
                if var_name:
                    var = var_name.group(1)
                    # Look for earlier declaration with null safety
                    declaration_found = False
                    for j in range(max(0, i-20), i):
                        if f'if ({var})' in lines[j] or f'if({var})' in lines[j]:
                            declaration_found = True
                            break
                    if not declaration_found:
                        issues.append(f"Line {i}: Potential null reference on {var}.value - {line.strip()}")
    
    return issues

def check_template_js(file_path):
    """Check JavaScript inside HTML templates."""
    issues = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Find script tags
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, content, re.DOTALL)
        
        for script_content in scripts:
            lines = script_content.split('\n')
            for i, line in enumerate(lines, 1):
                # Same checks as JS files
                if re.search(r'document\.getElementById\([^)]+\)\.[a-zA-Z]', line):
                    if not re.search(r'if\s*\([^)]*document\.getElementById', line) and \
                       not re.search(r'document\.getElementById[^;]*&&', line):
                        issues.append(f"Template script line {i}: Potential null reference - {line.strip()}")
    
    return issues

def main():
    """Run the verification."""
    print("🔍 Final JavaScript Error Verification")
    print("=====================================")
    
    # Check JavaScript files
    js_dir = Path("council_finance/static/js")
    static_js_dir = Path("static/js")
    
    js_files = []
    if js_dir.exists():
        js_files.extend(js_dir.glob("*.js"))
    if static_js_dir.exists():
        js_files.extend(static_js_dir.glob("*.js"))
    
    total_issues = 0
    
    for js_file in js_files:
        print(f"\n📄 Checking {js_file}")
        issues = check_js_file(js_file)
        if issues:
            print(f"  ⚠️  Found {len(issues)} potential issues:")
            for issue in issues:
                print(f"    • {issue}")
            total_issues += len(issues)
        else:
            print("  ✅ No issues found")
    
    # Check template files
    template_dirs = [
        Path("council_finance/templates"),
        Path("templates")
    ]
    
    for template_dir in template_dirs:
        if template_dir.exists():
            for template_file in template_dir.rglob("*.html"):
                issues = check_template_js(template_file)
                if issues:
                    print(f"\n📄 Template {template_file}")
                    print(f"  ⚠️  Found {len(issues)} potential issues:")
                    for issue in issues:
                        print(f"    • {issue}")
                    total_issues += len(issues)
    
    print(f"\n📊 Summary")
    print(f"Total potential issues found: {total_issues}")
    
    if total_issues == 0:
        print("🎉 No potential null reference issues detected!")
        print("✅ JavaScript files appear to have proper null safety checks.")
    else:
        print("⚠️  Some potential issues found. Review the files listed above.")
    
    # Check specific council edit functionality
    print(f"\n🧪 Quick Functionality Check")
    print("=============================")
    
    council_edit_js = Path("council_finance/static/js/council_edit.js")
    if council_edit_js.exists():
        with open(council_edit_js, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for key safety patterns
            checks = [
                ("Modal null check", "if (modal)" in content),
                ("Form null check", "if (editForm)" in content),
                ("Button null checks", "if (closeModalBtn)" in content),
                ("Element safety in functions", "if (helperText)" in content),
                ("Input container safety", "if (inputContainer)" in content),
            ]
            
            for check_name, found in checks:
                status = "✅" if found else "❌"
                print(f"  {status} {check_name}")
    
    print(f"\n🔧 Recommendations")
    print("==================")
    print("1. Test the application in browser console for any remaining errors")
    print("2. Check browser developer tools Network tab for failed API calls")
    print("3. Verify that the Financial Data panel loads properly")
    print("4. Test the edit modal functionality on council detail pages")

if __name__ == "__main__":
    main()
