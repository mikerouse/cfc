"""Basic import tests for views modules."""

import importlib

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "home",
        "dashboard",
        "contact",
        "council_list",
        "council_detail",
        "help_center",
    ],
)
def test_view_imports(name):
    """Ensure views can be imported directly from council_finance.views."""
    module = importlib.import_module("council_finance.views")
    view = getattr(module, name)
    assert callable(view)
