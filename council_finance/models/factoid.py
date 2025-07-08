from django.db import models
from .counter import CounterDefinition
from .site_counter import SiteCounter, GroupCounter


class Factoid(models.Model):
    """Short snippet of contextual information for counters."""

    FACTOID_TYPES = [
        ("percent_change", "Percentage change on last year"),
        ("highest", "Highest council"),
        ("lowest", "Lowest council"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    factoid_type = models.CharField(max_length=20, choices=FACTOID_TYPES)
    text = models.CharField(max_length=255)
    counters = models.ManyToManyField(CounterDefinition, blank=True)
    site_counters = models.ManyToManyField(SiteCounter, blank=True)
    group_counters = models.ManyToManyField(GroupCounter, blank=True)

    def __str__(self):
        return self.name
