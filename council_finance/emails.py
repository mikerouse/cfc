from django.core.mail import send_mail
from django.urls import reverse
from django.utils.crypto import get_random_string

from .models import UserProfile


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
    send_mail(
        "Confirm your email",
        message,
        None,
        [profile.user.email],
    )
