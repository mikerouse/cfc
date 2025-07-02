"""Helpers for in-app notifications."""

from django.contrib.auth import get_user_model

from .models import Notification
from django.db.utils import OperationalError


def create_notification(user: get_user_model(), message: str, email: bool = False) -> None:
    """Create a notification and optionally flag it for email delivery."""
    try:
        Notification.objects.create(user=user, message=message, email=email)
    except OperationalError:
        # If the notification table doesn't exist yet just ignore. This avoids
        # errors during initial migrations or tests where notifications aren't
        # critical.
        pass
