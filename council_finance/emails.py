"""Utility helpers for sending emails through Brevo."""

import os

from django.urls import reverse
from django.utils.crypto import get_random_string

import brevo_python
from brevo_python.api import TransactionalEmailsApi
from brevo_python.models import SendSmtpEmail

from .models import UserProfile


def send_email(subject: str, message: str, recipient: str) -> None:
    """Send a plain text email via the Brevo transactional API."""
    configuration = brevo_python.Configuration()
    configuration.api_key["api-key"] = os.environ["BREVO_API_KEY"]

    api = TransactionalEmailsApi(brevo_python.ApiClient(configuration))
    email = SendSmtpEmail(
        to=[{"email": recipient}],
        subject=subject,
        text_content=message,
        sender={"email": os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")},
    )

    try:
        api.send_transac_email(email)
    except brevo_python.ApiException as e:
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
