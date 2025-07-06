from django.db import models

from .counter import CounterDefinition
from .council import Council
from .council_type import CouncilType
from .council_list import CouncilList


class SiteCounter(models.Model):
    """Counter that totals a metric across all councils for a year."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    counter = models.ForeignKey(CounterDefinition, on_delete=models.CASCADE)
    explanation = models.TextField(
        blank=True,
        help_text="Optional description shown via info icon on the home page",
    )
    year = models.ForeignKey(
        'FinancialYear',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Limit to a single year or leave blank to sum all years",
    )
    duration = models.PositiveIntegerField(default=2000)
    precision = models.PositiveIntegerField(default=0)
    show_currency = models.BooleanField(default=True, help_text="Prefix with £ and include comma separators")
    friendly_format = models.BooleanField(default=False, help_text="Use short forms e.g. £1m")
    promote_homepage = models.BooleanField(default=False, help_text="Show on the home page")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Generate slug from name when creating."""
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)
            slug = base
            i = 1
            while SiteCounter.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class GroupCounter(models.Model):
    """Counter that totals a metric across a subset of councils."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    counter = models.ForeignKey(CounterDefinition, on_delete=models.CASCADE)
    councils = models.ManyToManyField(Council, blank=True)
    council_list = models.ForeignKey(CouncilList, null=True, blank=True, on_delete=models.SET_NULL)
    council_types = models.ManyToManyField(CouncilType, blank=True)
    year = models.ForeignKey(
        "FinancialYear",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Limit to a single year or leave blank to sum all years",
    )
    duration = models.PositiveIntegerField(default=2000)
    precision = models.PositiveIntegerField(default=0)
    show_currency = models.BooleanField(default=True, help_text="Prefix with £ and include comma separators")
    friendly_format = models.BooleanField(default=False, help_text="Use short forms e.g. £1m")
    promote_homepage = models.BooleanField(default=False, help_text="Show on the home page")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Generate slug from name when creating."""
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)
            slug = base
            i = 1
            while GroupCounter.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
