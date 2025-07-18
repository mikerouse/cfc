#!/usr/bin/env python3
"""Fix relative imports in ``general.py`` after refactoring.

Usage::

    python fix_imports.py

The script locates ``general.py`` relative to its own location and replaces
old relative imports with absolute ones under ``council_finance``. This is
useful when modules are moved and import paths need updating.
"""

import re
from pathlib import Path

def fix_imports():
    # Compute the path to ``general.py`` relative to this script. This keeps the
    # script portable regardless of the working directory.
    script_dir = Path(__file__).resolve().parent
    filepath = script_dir / "council_finance" / "views" / "general.py"
    
    # Read the current file contents.
    with filepath.open("r", encoding="utf-8") as f:
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
    
    # Overwrite the file with the updated imports.
    with filepath.open("w", encoding="utf-8") as f:
        f.write(content)
    
    print("Fixed relative imports in general.py")

if __name__ == "__main__":
    fix_imports()
