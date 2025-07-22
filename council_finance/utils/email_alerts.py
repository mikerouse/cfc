"""
Email Alert System using Brevo API

Provides utilities for sending error alerts and system notifications via email.
Designed to send actionable error information to administrators in a format
that can be easily copied and pasted into AI systems for assistance.
"""

import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

try:
    import brevo_python
    from brevo_python.api import transactional_emails_api
    from brevo_python.models import SendSmtpEmail
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False

from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger(__name__)


class EmailAlertService:
    """Service for sending email alerts via Brevo API"""
    
    def __init__(self):
        self.api_key = os.getenv('BREVO_API_KEY')
        self.alert_email = os.getenv('ERROR_ALERTS_EMAIL_ADDRESS')
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'alerts@councilfinance.com')
        self.from_name = "Council Finance Alerts"
        
        if not BREVO_AVAILABLE:
            logger.warning("brevo-python not available. Email alerts will be logged only.")
        
        if not self.api_key:
            logger.warning("BREVO_API_KEY not configured. Email alerts will be logged only.")
        
        if not self.alert_email:
            logger.warning("ERROR_ALERTS_EMAIL_ADDRESS not configured. Email alerts will be logged only.")
    
    def _get_api_instance(self):
        """Get configured Brevo API instance"""
        if not BREVO_AVAILABLE or not self.api_key:
            return None
        
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = self.api_key
        api_instance = transactional_emails_api.TransactionalEmailsApi(
            brevo_python.ApiClient(configuration)
        )
        return api_instance
    
    def _send_email(self, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send email via Brevo API"""
        if not self.alert_email:
            logger.error("No alert email address configured")
            return False
        
        api_instance = self._get_api_instance()
        if not api_instance:
            logger.warning(f"Email would be sent: {subject}")
            logger.info(text_content or html_content)
            return False
        
        try:
            send_smtp_email = SendSmtpEmail(
                to=[{"email": self.alert_email}],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                sender={"name": self.from_name, "email": self.from_email}
            )
            
            response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email alert sent successfully: {response.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            logger.info(f"Email content that failed to send: {subject}")
            logger.info(text_content or html_content)
            return False
    
    def send_error_alert(self, 
                        exception: Exception, 
                        request: Optional[HttpRequest] = None,
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send an error alert email with detailed information for AI assistance
        
        Args:
            exception: The exception that occurred
            request: Django request object (if available)
            context: Additional context information
        """
        exc_type = type(exception).__name__
        exc_message = str(exception)
        
        # Get full traceback
        tb = traceback.format_exc()
        
        # Build context information
        error_context = {
            'timestamp': datetime.now().isoformat(),
            'exception_type': exc_type,
            'exception_message': exc_message,
            'python_version': sys.version,
            'django_version': getattr(settings, 'DJANGO_VERSION', 'Unknown'),
        }
        
        # Add request information if available
        if request:
            error_context.update({
                'request_method': request.method,
                'request_path': request.path,
                'request_user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                'request_ip': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'referer': request.META.get('HTTP_REFERER', 'None'),
            })
            
            # Add POST data (sanitized)
            if request.method == 'POST' and hasattr(request, 'POST'):
                post_data = dict(request.POST)
                # Remove sensitive data
                sensitive_keys = ['password', 'token', 'csrf', 'api_key']
                for key in list(post_data.keys()):
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        post_data[key] = ['*** REDACTED ***']
                error_context['post_data'] = post_data
        
        # Add custom context
        if context:
            error_context.update(context)
        
        # Create AI-friendly error report
        subject = f"🚨 System Error: {exc_type} - {datetime.now().strftime('%H:%M:%S')}"
        
        # Text content for AI copy-paste
        text_content = self._generate_ai_friendly_report(error_context, tb)
        
        # HTML content for human reading
        html_content = self._generate_html_report(error_context, tb)
        
        return self._send_email(subject, html_content, text_content)
    
    def send_template_missing_alert(self, template_name: str, request: Optional[HttpRequest] = None) -> bool:
        """Send alert for missing template errors"""
        context = {
            'alert_type': 'TemplateDoesNotExist',
            'template_name': template_name,
            'suggested_action': f"Create missing template: {template_name}",
        }
        
        exception = Exception(f"Template does not exist: {template_name}")
        return self.send_error_alert(exception, request, context)
    
    def send_syntax_error_alert(self, error_details: str, file_path: str = None) -> bool:
        """Send alert for syntax errors"""
        context = {
            'alert_type': 'SyntaxError',
            'file_path': file_path,
            'suggested_action': "Check syntax in the reported file",
        }
        
        exception = SyntaxError(error_details)
        return self.send_error_alert(exception, None, context)
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary for display"""
        formatted = []
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                formatted.append(f"{key}: {repr(value)}")
            else:
                formatted.append(f"{key}: {value}")
        return '\n'.join(formatted)
    
    def _generate_ai_friendly_report(self, context: Dict[str, Any], traceback_str: str) -> str:
        """Generate AI-friendly error report that can be copy-pasted"""
        return f"""
ERROR REPORT - AI ASSISTANCE FORMAT
===================================

## Error Summary
- Type: {context['exception_type']}
- Message: {context['exception_message']}
- Time: {context['timestamp']}

## Environment
- Python: {context['python_version']}
- Django: {context['django_version']}

## Request Context
{self._format_request_context(context)}

## Full Traceback
```
{traceback_str}
```

## System Context
{self._format_context({k: v for k, v in context.items() if k not in ['exception_type', 'exception_message', 'timestamp', 'python_version', 'django_version']})}

---
INSTRUCTIONS FOR AI:
1. Analyze the error type and traceback
2. Identify the root cause
3. Provide specific fix recommendations
4. Consider Django best practices
5. Suggest preventive measures

PROJECT CONTEXT: This is a Django application for UK local government finance data.
The app uses PostgreSQL, has AI integration features, and includes data contribution workflows.

---
Generated by Council Finance Counters Alert System
"""
    
    def _format_request_context(self, context: Dict[str, Any]) -> str:
        """Format request-specific context"""
        request_fields = ['request_method', 'request_path', 'request_user', 'request_ip', 'user_agent', 'referer', 'post_data']
        request_info = []
        
        for field in request_fields:
            if field in context:
                request_info.append(f"- {field.replace('request_', '').title()}: {context[field]}")
        
        return '\n'.join(request_info) if request_info else "- No request context available"
    
    def _generate_html_report(self, context: Dict[str, Any], traceback_str: str) -> str:
        """Generate HTML error report for email"""
        request_section = self._generate_request_html_section(context)
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Error Alert</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #dc2626; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 20px; background: #f9fafb; }}
        .section {{ margin-bottom: 20px; }}
        .section h3 {{ color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 5px; }}
        .code {{ background: #1f2937; color: #f3f4f6; padding: 15px; border-radius: 6px; overflow-x: auto; font-family: 'SF Mono', Monaco, Consolas, monospace; font-size: 12px; }}
        .context {{ background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #3b82f6; }}
        .footer {{ background: #374151; color: white; padding: 10px 20px; text-align: center; border-radius: 0 0 8px 8px; font-size: 12px; }}
        .highlight {{ color: #dc2626; font-weight: bold; }}
        .meta {{ color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 System Error Alert</h1>
        <p class="meta">{context['timestamp']}</p>
    </div>
    
    <div class="content">
        <div class="section">
            <h3>Error Summary</h3>
            <div class="context">
                <p><strong>Type:</strong> <span class="highlight">{context['exception_type']}</span></p>
                <p><strong>Message:</strong> {context['exception_message']}</p>
                <p><strong>Environment:</strong> Python {context['python_version']}, Django {context['django_version']}</p>
            </div>
        </div>
        
        {request_section}
        
        <div class="section">
            <h3>Full Traceback</h3>
            <div class="code">{traceback_str.replace('<', '&lt;').replace('>', '&gt;')}</div>
        </div>
    </div>
    
    <div class="footer">
        <p>Council Finance Counters Alert System</p>
        <p>This alert was automatically generated and sent to help with system monitoring.</p>
    </div>
</body>
</html>"""
    
    def _generate_request_html_section(self, context: Dict[str, Any]) -> str:
        """Generate HTML section for request information"""
        request_fields = ['request_method', 'request_path', 'request_user', 'request_ip', 'user_agent', 'referer']
        
        if not any(field in context for field in request_fields):
            return ""
        
        html = '<div class="section"><h3>Request Information</h3><div class="context">'
        
        for field in request_fields:
            if field in context:
                display_name = field.replace('request_', '').replace('_', ' ').title()
                html += f'<p><strong>{display_name}:</strong> {context[field]}</p>'
        
        if 'post_data' in context and context['post_data']:
            html += f'<p><strong>POST Data:</strong></p><pre>{context["post_data"]}</pre>'
        
        html += '</div></div>'
        return html


# Global instance
email_alert_service = EmailAlertService()


# Convenience functions
def send_error_alert(exception: Exception, request: Optional[HttpRequest] = None, context: Optional[Dict] = None) -> bool:
    """Send error alert - convenience function"""
    return email_alert_service.send_error_alert(exception, request, context)


def send_template_missing_alert(template_name: str, request: Optional[HttpRequest] = None) -> bool:
    """Send template missing alert - convenience function"""
    return email_alert_service.send_template_missing_alert(template_name, request)


def send_syntax_error_alert(error_details: str, file_path: str = None) -> bool:
    """Send syntax error alert - convenience function"""  
    return email_alert_service.send_syntax_error_alert(error_details, file_path)