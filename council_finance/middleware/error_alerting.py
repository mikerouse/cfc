"""
Error Alerting Middleware

Automatically sends email alerts for system errors including TemplateDoesNotExist,
SyntaxError, and other exceptions that occur during request processing.
"""

import logging
from django.template import TemplateDoesNotExist
from django.http import Http404
from django.conf import settings
from council_finance.utils.email_alerts import send_error_alert, send_template_missing_alert

logger = logging.getLogger(__name__)


class ErrorAlertingMiddleware:
    """
    Middleware that automatically sends email alerts for errors
    
    Catches various types of errors during request processing and sends
    detailed email alerts to administrators for debugging assistance.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Error types that should trigger email alerts
        self.alertable_errors = (
            TemplateDoesNotExist,
            SyntaxError,
            AttributeError,
            ImportError,
            KeyError,
            ValueError,
            TypeError,
            # Add more error types as needed
        )
        
        # Error types to ignore (too common/not actionable)
        self.ignored_errors = (
            Http404,  # 404 errors are expected
        )
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Process exceptions that occur during request handling"""
        
        # Skip ignored error types
        if isinstance(exception, self.ignored_errors):
            return None
        
        # Skip in development mode unless specifically enabled
        if settings.DEBUG and not getattr(settings, 'SEND_ERROR_ALERTS_IN_DEBUG', False):
            logger.info(f"Skipping error alert in DEBUG mode: {type(exception).__name__}")
            return None
        
        try:
            # Special handling for template errors
            if isinstance(exception, TemplateDoesNotExist):
                template_name = str(exception) if hasattr(exception, 'template_name') else str(exception)
                send_template_missing_alert(template_name, request)
                logger.info(f"Sent template missing alert for: {template_name}")
            
            # Handle other alertable errors
            elif isinstance(exception, self.alertable_errors):
                # Add extra context for specific error types
                context = self._get_error_context(exception, request)
                send_error_alert(exception, request, context)
                logger.info(f"Sent error alert for: {type(exception).__name__}")
            
            # Handle unexpected errors that aren't in our alertable list
            elif not isinstance(exception, self.ignored_errors):
                context = {
                    'alert_type': 'UnexpectedError',
                    'suggested_action': 'Review error and consider adding to alertable_errors list'
                }
                send_error_alert(exception, request, context)
                logger.info(f"Sent unexpected error alert for: {type(exception).__name__}")
                
        except Exception as alert_exception:
            # Don't let alerting errors break the main application
            logger.error(f"Failed to send error alert: {alert_exception}")
        
        # Return None to let Django handle the error normally
        return None
    
    def _get_error_context(self, exception, request):
        """Get additional context based on error type"""
        context = {}
        
        if isinstance(exception, TemplateDoesNotExist):
            context.update({
                'alert_type': 'TemplateDoesNotExist',
                'template_name': getattr(exception, 'template_name', str(exception)),
                'suggested_action': 'Create the missing template file'
            })
        
        elif isinstance(exception, SyntaxError):
            context.update({
                'alert_type': 'SyntaxError',
                'filename': getattr(exception, 'filename', 'Unknown'),
                'lineno': getattr(exception, 'lineno', 'Unknown'),
                'suggested_action': 'Fix syntax error in the reported file'
            })
        
        elif isinstance(exception, ImportError):
            context.update({
                'alert_type': 'ImportError',
                'module_name': getattr(exception, 'name', 'Unknown'),
                'suggested_action': 'Check if the module is installed or the import path is correct'
            })
        
        elif isinstance(exception, AttributeError):
            context.update({
                'alert_type': 'AttributeError',
                'suggested_action': 'Check if the attribute exists and is spelled correctly'
            })
        
        elif isinstance(exception, KeyError):
            context.update({
                'alert_type': 'KeyError',
                'missing_key': str(exception),
                'suggested_action': 'Check if the key exists in the data structure'
            })
        
        # Add request-specific context
        if request:
            context.update({
                'view_name': getattr(request.resolver_match, 'view_name', 'Unknown') if hasattr(request, 'resolver_match') else 'Unknown',
                'url_name': getattr(request.resolver_match, 'url_name', 'Unknown') if hasattr(request, 'resolver_match') else 'Unknown',
            })
        
        return context