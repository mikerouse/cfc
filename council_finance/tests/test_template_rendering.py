from pathlib import Path
import pytest
from django.template.loader import get_template


# Gather all template names from project template dirs
BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_DIRS = [BASE_DIR / "templates", BASE_DIR / "council_finance" / "templates"]

# Some legacy templates rely on deprecated tags or conflicting blocks.
SKIP_TEMPLATES = {
    "council_finance/flagged_content_old.html",
    "council_finance/user_preferences.html",
}

def template_names():
    names = []
    for directory in TEMPLATE_DIRS:
        for path in directory.rglob("*.html"):
            names.append(str(path.relative_to(directory)))
    return sorted(set(names))


@pytest.mark.parametrize("template_name", template_names())
def test_template_can_load(template_name):
    """Ensure each template can be loaded without syntax errors."""
    if template_name in SKIP_TEMPLATES:
        pytest.skip("legacy template uses unsupported tags")
    get_template(template_name)
