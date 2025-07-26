"""
Activity Logging Utilities

Enhanced activity logging functions for the Council Finance system with backward compatibility.
Provides comprehensive audit trails for all user and system actions.
"""
import json
import inspect
from .models import ActivityLog


def log_activity(*args, **kwargs):
    """
    Enhanced activity logging function with backward compatibility.
    
    Supports both old and new calling conventions:
    - Old: log_activity(user, action, model_name, object_id)
    - New: log_activity(request, activity="...", log_type="...", etc.)
    """
    
    # Handle old calling convention: log_activity(user, action, model_name, object_id)
    if len(args) >= 2 and not hasattr(args[0], 'user'):
        user, action = args[0], args[1]
        model_name = args[2] if len(args) > 2 else None
        object_id = args[3] if len(args) > 3 else None
        
        # Determine the calling function for context
        caller_frame = inspect.currentframe().f_back
        calling_function = caller_frame.f_code.co_name if caller_frame else "unknown"
          # Store using modern ActivityLog system with old-style data
        details = {
            'legacy_call': True,
            'calling_function': calling_function,
        }
        if model_name:
            details['model_name'] = model_name
        if object_id:
            details['object_id'] = object_id
            
        # Determine activity type based on action
        if 'created' in action.lower():
            activity_type = 'create'
        elif 'updated' in action.lower() or 'edited' in action.lower():
            activity_type = 'update'
        elif 'deleted' in action.lower():
            activity_type = 'delete'
        else:
            activity_type = 'system'
            
        ActivityLog.log_activity(
            activity_type=activity_type,
            description=action,
            user=user if user and user.is_authenticated else None,
            status='completed',
            details=details
        )
        return
    
    # Handle new calling convention: log_activity(request, *, activity="", ...)
    if len(args) >= 1:
        request = args[0]
    else:
        raise TypeError("log_activity() missing required argument: 'request' or 'user'")
    
    # Extract keyword arguments with defaults
    council = kwargs.get('council')
    activity = kwargs.get('activity', "")
    log_type = kwargs.get('log_type', "user")
    action = kwargs.get('action', "")
    request_data = kwargs.get('request_data')
    response = kwargs.get('response', "")
    extra = kwargs.get('extra')
    
    if isinstance(extra, dict) or extra is None:
        extra_data = extra or {}
    else:
        extra_data = {"message": str(extra)}

    # Determine the calling function for context
    caller_frame = inspect.currentframe().f_back
    calling_function = caller_frame.f_code.co_name if caller_frame else "unknown"    # Map old log_type to modern activity_type
    activity_type_mapping = {
        "user": "contribution",
        "admin": "system", 
        "system": "system",
        "error": "system",
        "debug": "system"
    }
    modern_activity_type = activity_type_mapping.get(log_type, "system")

    # Store using modern ActivityLog system
    log_entry = ActivityLog.log_activity(
        activity_type=modern_activity_type,
        description=f"{activity}: {action}" if action else activity,
        user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        related_council=council,
        status='completed',
        details={'legacy_data': extra_data, 'calling_function': calling_function}
    )
    
    # Also populate legacy fields for backward compatibility
    log_entry.activity = activity
    log_entry.action = action
    log_entry.log_type = log_type
    if extra_data:
        log_entry.extra = json.dumps(extra_data)
    log_entry.save()
