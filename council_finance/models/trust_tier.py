from django.db import models


class TrustTier(models.Model):
    """Renameable trust levels controlling volunteer permissions.

    Each level corresponds to a volunteer "trust" rating. The
    default tier 1 represents a brand new volunteer, while higher
    tiers grant additional privileges such as approving other
    contributions. Admins can rename each level as required.
    """

    level = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["level"]

    def __str__(self) -> str:
        return f"{self.name} (Tier {self.level})"
