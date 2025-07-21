"""
Activity Logging Utilities

Shared activity logging functions for the Council Finance system.
"""
import json
import inspect
from .models import ActivityLog


def log_activity(
    request,
    *,
    council=None,
    activity="",
    log_type="user",
    action="",
    request_data=None,
    response="",
    extra=None,
):
    """Helper to store troubleshooting events using the modern ActivityLog system."""
    
    if isinstance(extra, dict) or extra is None:
        extra_data = extra or {}
    else:
        extra_data = {"message": str(extra)}

    # Determine the calling function for context
    caller_frame = inspect.currentframe().f_back
    calling_function = caller_frame.f_code.co_name if caller_frame else "unknown"

    # Map old log_type to modern activity_type
    activity_type_mapping = {
        "user": "user_action",
        "admin": "admin_action", 
        "system": "system_event",
        "error": "error",
        "debug": "debug"
    }
    modern_activity_type = activity_type_mapping.get(log_type, "user_action")

    # Store using modern ActivityLog system
    ActivityLog.log_activity(
        activity_type=modern_activity_type,
        description=f"{activity}: {action}" if action else activity,
        user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        related_council=council,
        status='completed',
        details={'legacy_data': extra_data, 'calling_function': calling_function}
    )
