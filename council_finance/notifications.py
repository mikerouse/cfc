"""Helpers for in-app notifications."""

from django.contrib.auth import get_user_model

from .models import Notification


def create_notification(user: get_user_model(), message: str, email: bool = False) -> None:
    """Create a notification and optionally flag it for email delivery."""
    Notification.objects.create(user=user, message=message, email=email)
