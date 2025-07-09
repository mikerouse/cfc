from typing import Dict
from django.http import HttpRequest

def compare_count(request: HttpRequest) -> Dict[str, int]:
    """Expose the number of councils in the comparison basket."""
    return {"compare_count": len(request.session.get("compare_basket", []))}


def font_family(request: HttpRequest) -> Dict[str, str]:
    """Expose the user's chosen font or fall back to Cairo."""
    user = request.user
    if user.is_authenticated and hasattr(user, "profile"):
        return {"font_family": user.profile.preferred_font or "Cairo"}
    return {"font_family": "Cairo"}
