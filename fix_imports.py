#!/usr/bin/env python3
"""
Script to fix relative imports in general.py after views module refactoring.
"""

import re

def fix_imports():
    filepath = r"f:\mikerouse\Documents\Projects\Council Finance Counters\v3\cfc\council_finance\views\general.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace relative imports with absolute imports
    replacements = [
        (r'from \.models import', 'from council_finance.models import'),
        (r'from \.services\.following_services import', 'from council_finance.services.following_services import'),
        (r'from \.services\.flagging_services import', 'from council_finance.services.flagging_services import'),
        (r'from \.factoids import', 'from council_finance.factoids import'),
        (r'from \.data_quality import', 'from council_finance.data_quality import'),
        (r'from \.smart_data_quality import', 'from council_finance.smart_data_quality import'),
        (r'from \.agents\.counter_agent import', 'from council_finance.agents.counter_agent import'),
        (r'from \.models\.counter import', 'from council_finance.models.counter import'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed relative imports in general.py")

if __name__ == "__main__":
    fix_imports()
