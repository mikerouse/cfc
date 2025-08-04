from django.db import models
from django.utils.text import slugify

class CouncilNation(models.Model):
    """Represents the UK nation a council belongs to."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="URL-friendly version of name")

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
