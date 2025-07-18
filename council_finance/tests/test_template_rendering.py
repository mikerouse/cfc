from pathlib import Path
import pytest
from django.template.loader import get_template
from django.template import TemplateSyntaxError

# Rendering each template helps catch runtime issues that only surface
# when variables are resolved, beyond basic syntax errors.

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

html_templates = [p.relative_to(TEMPLATES_DIR).as_posix() for p in TEMPLATES_DIR.rglob("*.html")]

@pytest.mark.parametrize("template_name", html_templates)
def test_template_renders_without_error(template_name):
    try:
        template = get_template(template_name)
        try:
            template.render({})
        except Exception as render_exc:
            pytest.fail(f"Error rendering {template_name}: {render_exc}")
    except TemplateSyntaxError as syntax_exc:
        pytest.fail(f"Syntax error in {template_name}: {syntax_exc}")
