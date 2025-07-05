from django.db import models


class CouncilCapability(models.Model):
    """A capability that a council type might support."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Council capability"
        verbose_name_plural = "Council capabilities"

    def __str__(self) -> str:
        return self.name


class CouncilType(models.Model):
    """Represents a configurable council type (e.g. Unitary)."""

    name = models.CharField(max_length=100, unique=True)
    # Many-to-many so types can share capabilities without duplication. Blank
    # allows older data to omit this field until configured by staff.
    capabilities = models.ManyToManyField(
        CouncilCapability,
        blank=True,
        help_text="Functions this type of council performs",
    )

    class Meta:
        verbose_name = "Council type"
        verbose_name_plural = "Council types"

    def __str__(self) -> str:
        return self.name

    def display_capabilities(self) -> str:
        """Return capabilities as a comma separated string for admin lists."""
        names = [cap.name for cap in self.capabilities.all()]
        return ", ".join(names) if names else "None"
