from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from .models import UserProfile, TrustTier, FigureSubmission
from .models import DataIssue, Contribution
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.crypto import get_random_string
from .notifications import create_notification


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a matching profile whenever a new user is made."""
    if created:
        try:
            # Superusers default to the highest tier for full permissions
            level = 5 if instance.is_superuser else 1
            default_tier = TrustTier.objects.get(level=level)
        except TrustTier.DoesNotExist:
            default_tier = None
        UserProfile.objects.create(
            user=instance,
            confirmation_token=get_random_string(32),
            tier=default_tier,
        )


@receiver(pre_save, sender=UserProfile)
def notify_tier_change(sender, instance, **kwargs):
    """Notify users when their tier is updated."""
    if not instance.pk:
        return
    try:
        previous = UserProfile.objects.get(pk=instance.pk)
    except UserProfile.DoesNotExist:
        return
    if previous.tier_id != instance.tier_id:
        create_notification(
            instance.user,
            f"Your trust tier is now {instance.tier.name}",
        )


@receiver([post_save, post_delete], sender=FigureSubmission)
def refresh_population_cache(sender, instance, **kwargs):
    """Update the council's cached population figure."""
    if instance.field.slug != "population":
        return
    instance.council.update_latest_population()


def _broadcast_update(model_name: str) -> None:
    """Send a simple notification to connected websocket clients."""
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        "contribute",
        {"type": "contribute.update", "data": {"model": model_name}},
    )


@receiver([post_save, post_delete], sender=DataIssue)
def notify_issue_change(sender, **kwargs):
    """Trigger a websocket event when DataIssue rows change."""
    _broadcast_update("DataIssue")


@receiver([post_save, post_delete], sender=Contribution)
def notify_contrib_change(sender, **kwargs):
    """Trigger a websocket event when contributions change."""
    _broadcast_update("Contribution")
