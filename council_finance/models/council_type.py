from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


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

    # Core identification
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="URL-friendly version of name")
    
    # Hierarchy and governance
    tier_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Tier level: 1=Unitary, 2=Upper Tier (County), 3=Lower Tier (District), 4=Parish, 5=Other"
    )
    
    # Scale and status
    council_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of councils of this type in the UK"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this council type is currently in use (allows disabling without deleting)"
    )
    
    # Display and information
    display_colour = models.CharField(
        max_length=7,
        blank=True,
        default="#1d70b8",
        help_text="Hex color code for charts and data visualization (e.g. #1d70b8)"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed explanation of what this council type does and its responsibilities"
    )
    wikipedia_url = models.URLField(
        blank=True,
        help_text="Link to Wikipedia or other educational resource about this council type"
    )
    
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
        ordering = ['tier_level', 'name']

    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def display_capabilities(self) -> str:
        """Return capabilities as a comma separated string for admin lists."""
        names = [cap.name for cap in self.capabilities.all()]
        return ", ".join(names) if names else "None"
    
    @property
    def tier_name(self):
        """Return human-readable tier level name."""
        tier_names = {
            1: "Unitary Authority",
            2: "Upper Tier (County)",
            3: "Lower Tier (District/Borough)", 
            4: "Parish/Town Council",
            5: "Other/Special Purpose"
        }
        return tier_names.get(self.tier_level, "Unknown Tier") if self.tier_level else "No Tier Assigned"
    
    def get_councils(self):
        """Get all active councils of this type."""
        return self.council_set.filter(status='active')
    
    def get_all_councils(self):
        """Get all councils of this type regardless of status."""
        return self.council_set.all()
