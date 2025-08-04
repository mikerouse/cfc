from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator

class CouncilNation(models.Model):
    """Represents the UK nation a council belongs to."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="URL-friendly version of name")
    
    # Population and scale data
    total_population = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Total population of this nation (for nation-level per capita calculations)"
    )
    council_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True, 
        help_text="Number of local authorities in this nation"
    )
    
    # Geographic data
    capital_city = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Administrative center/capital city"
    )
    total_area_km2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Total geographic area in square kilometres"
    )
    
    # Display and financial settings
    display_colour = models.CharField(
        max_length=7,
        blank=True,
        default="#1d70b8",
        help_text="Hex color code for charts and data visualization (e.g. #1d70b8)"
    )
    currency_code = models.CharField(
        max_length=3,
        default="GBP",
        help_text="ISO currency code (GBP for UK nations)"
    )

    class Meta:
        verbose_name = "Council nation"
        verbose_name_plural = "Council nations"

    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property 
    def population_density(self):
        """Calculate population density per km² if both values available."""
        if self.total_population and self.total_area_km2:
            return round(self.total_population / float(self.total_area_km2), 2)
        return None
    
    @property
    def average_council_population(self):
        """Calculate average population per council if both values available."""
        if self.total_population and self.council_count:
            return round(self.total_population / self.council_count)
        return None
    
    def get_councils(self):
        """Get all councils belonging to this nation."""
        return self.council_set.filter(status='active')
