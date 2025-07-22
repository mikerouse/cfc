"""Utility helpers for sending emails through Brevo."""

import os
import logging

from django.urls import reverse
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.conf import settings

import brevo_python
from brevo_python.api import TransactionalEmailsApi
from brevo_python.models import SendSmtpEmail
from brevo_python.rest import ApiException

from .models import UserProfile

logger = logging.getLogger(__name__)


def send_email(subject: str, message: str, recipient: str) -> None:
    """Send a plain text email via the Brevo transactional API."""
    configuration = brevo_python.Configuration()
    configuration.api_key["api-key"] = os.environ["BREVO_API_KEY"]

    api = TransactionalEmailsApi(brevo_python.ApiClient(configuration))
    email = SendSmtpEmail(
        to=[{"email": recipient}],
        subject=subject,
        text_content=message,
        # Always use our designated sender address for system emails so
        # messages appear consistent and pass DMARC checks.
        sender={"email": os.getenv("DEFAULT_FROM_EMAIL", "counters@mikerouse.co.uk")},
    )

    try:
        api.send_transac_email(email)
    except ApiException as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Brevo API error: {e}")
        raise


def send_confirmation_email(profile: UserProfile, request) -> None:
    """Send or re-send an email confirmation link to the user."""
    if not profile.confirmation_token:
        profile.confirmation_token = get_random_string(32)
        profile.save()
    confirm_link = request.build_absolute_uri(
        reverse("confirm_email", args=[profile.confirmation_token])
    )
    message = (
        "Please confirm your email by visiting the following link: "
        f"{confirm_link}"
    )
    send_email("Confirm your email", message, profile.user.email)


def send_email_enhanced(to_email: str, subject: str, template: str = None, context: dict = None, text_content: str = None) -> bool:
    """Enhanced send_email function with template support."""
    try:
        configuration = brevo_python.Configuration()
        configuration.api_key["api-key"] = os.environ.get("BREVO_API_KEY")
        
        if not configuration.api_key["api-key"]:
            logger.warning("BREVO_API_KEY not configured, logging email instead")
            logger.info(f"Would send email to {to_email}: {subject}")
            return False

        api = TransactionalEmailsApi(brevo_python.ApiClient(configuration))
        
        # Generate content
        if template and context:
            try:
                html_content = render_to_string(template, context)
                if not text_content:
                    # Simple text version - strip HTML tags
                    import re
                    text_content = re.sub('<[^<]+?>', '', html_content)
            except Exception as e:
                logger.error(f"Error rendering template {template}: {e}")
                if not text_content:
                    text_content = "Please check your email client for the full message."
                html_content = None
        else:
            html_content = None
            if not text_content:
                text_content = "Email content unavailable"

        email = SendSmtpEmail(
            to=[{"email": to_email}],
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            sender={
                "email": os.getenv("DEFAULT_FROM_EMAIL", "counters@mikerouse.co.uk"),
                "name": "Council Finance Counters"
            },
        )

        response = api.send_transac_email(email)
        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return True
        
    except ApiException as e:
        logger.error(f"Brevo API error sending to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False


# Alias for backward compatibility and the new service
def send_email_with_template(to_email: str, subject: str, template: str, context: dict) -> bool:
    """Alias for template-based email sending."""
    return send_email_enhanced(to_email=to_email, subject=subject, template=template, context=context)
