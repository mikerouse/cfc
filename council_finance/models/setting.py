from django.db import models

class SiteSetting(models.Model):
    """Key/value store for configurable site options."""
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"

    @staticmethod
    def get(key: str, default: str | None = None) -> str | None:
        """Convenience helper to retrieve a setting value."""
        obj = SiteSetting.objects.filter(key=key).first()
        return obj.value if obj else default
