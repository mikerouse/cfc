from django.db import models

class BlockedIP(models.Model):
    """Record IP addresses that are blocked from submitting."""

    ip_address = models.GenericIPAddressField(unique=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.ip_address
