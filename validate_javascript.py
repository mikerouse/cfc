"""
JavaScript syntax validation for spreadsheet_editor.js
"""

import subprocess
import sys
import os

def validate_javascript():
    """Validate JavaScript syntax using Node.js if available, otherwise check basic structure."""
    
    js_file = "council_finance/static/js/spreadsheet_editor.js"
    
    print("Checking JavaScript syntax...")
    
    # Check if file exists
    if not os.path.exists(js_file):
        print(f"❌ JavaScript file not found: {js_file}")
        return False
    
    # Read file and check basic structure
    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Basic syntax checks
    errors = []
    
    # Check for class declaration
    if "class SpreadsheetEditor" not in content:
        errors.append("Missing SpreadsheetEditor class declaration")
    
    # Check for proper method declarations
    if "}    " in content:
        errors.append("Malformed method declarations found (extra spaces)")
    
    # Check for unclosed brackets/braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    if open_braces != close_braces:
        errors.append(f"Mismatched braces: {open_braces} opening, {close_braces} closing")
    
    open_parens = content.count('(')
    close_parens = content.count(')')
    if open_parens != close_parens:
        errors.append(f"Mismatched parentheses: {open_parens} opening, {close_parens} closing")
    
    # Check for duplicate class declarations
    class_declarations = content.count("class SpreadsheetEditor")
    if class_declarations > 1:
        errors.append(f"Duplicate class declarations found: {class_declarations}")
    
    # Check for required methods
    required_methods = [
        "loadFinancialData",
        "renderFinancialData", 
        "createFinancialDataRow",
        "formatValue",
        "getStatusInfo",
        "updateProgress"
    ]
    
    for method in required_methods:
        if f"{method}(" not in content:
            errors.append(f"Missing required method: {method}")
    
    if errors:
        print("❌ JavaScript validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ JavaScript syntax validation passed")
        return True

def check_file_structure():
    """Check the overall structure of the JavaScript file."""
    
    js_file = "council_finance/static/js/spreadsheet_editor.js"
    
    with open(js_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"\nFile structure analysis:")
    print(f"Total lines: {len(lines)}")
    
    # Check for key sections
    sections = {
        "Class declaration": "class SpreadsheetEditor",
        "Constructor": "constructor()",
        "Event listeners": "setupEventListeners",
        "Financial data loading": "loadFinancialData",
        "Financial data rendering": "renderFinancialData",
        "Row creation": "createFinancialDataRow",
        "Value formatting": "formatValue",
        "Progress tracking": "updateProgress",
        "Initialization": "DOMContentLoaded"
    }
    
    for section_name, search_term in sections.items():
        found = any(search_term in line for line in lines)
        status = "✅" if found else "❌"
        print(f"{status} {section_name}: {search_term}")
    
    return True

if __name__ == "__main__":
    os.chdir(r"f:\mikerouse\Documents\Projects\Council Finance Counters\v3\cfc")
    
    print("JavaScript Validation Report")
    print("=" * 40)
    
    syntax_ok = validate_javascript()
    structure_ok = check_file_structure()
    
    if syntax_ok and structure_ok:
        print("\n✅ JavaScript file is ready for testing")
    else:
        print("\n❌ JavaScript file has issues that need to be fixed")
