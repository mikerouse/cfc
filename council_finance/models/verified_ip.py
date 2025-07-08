from django.conf import settings
from django.db import models


class VerifiedIP(models.Model):
    """IP addresses that have resulted in an approved contribution."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verified_ips",
    )
    ip_address = models.GenericIPAddressField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "ip_address")
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.ip_address} for {self.user}" 
