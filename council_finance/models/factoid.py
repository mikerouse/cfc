from django.db import models
from .counter import CounterDefinition
from .site_counter import SiteCounter, GroupCounter
from .council import Council
from .council_type import CouncilType
from .council import FinancialYear


class FactoidTemplate(models.Model):
    """Template for generating dynamic factoids with rich content and animations"""
    
    FACTOID_TYPES = [
        ("percent_change", "📊 Percentage Change"),
        ("ranking", "🏆 Council Ranking"),  
        ("comparison", "⚖️ Peer Comparison"),
        ("trend", "📈 Multi-Year Trend"),
        ("ratio", "🔢 Financial Ratio"),
        ("per_capita", "👤 Per Capita Analysis"),
        ("sustainability", "🌱 Financial Health"),
        ("milestone", "🎯 Milestone Achievement"),
        ("anomaly", "⚠️ Data Anomaly"),
        ("context", "📋 Contextual Information"),
    ]
    
    COLOR_SCHEMES = [
        ('green', '🟢 Positive (Green)'),
        ('red', '🔴 Negative (Red)'),
        ('blue', '🔵 Neutral (Blue)'),
        ('orange', '🟠 Warning (Orange)'),
        ('purple', '🟣 Special (Purple)'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    factoid_type = models.CharField(max_length=20, choices=FACTOID_TYPES)
    
    # Rich template system
    template_text = models.TextField(help_text="Use {{variables}} for dynamic content")
    emoji = models.CharField(max_length=10, blank=True, help_text="Primary emoji for this factoid")
    
    # Visual properties  
    color_scheme = models.CharField(max_length=20, choices=COLOR_SCHEMES, default='blue')
    
    # Animation properties
    animation_duration = models.PositiveIntegerField(default=5000, help_text="Display duration in milliseconds")
    flip_animation = models.BooleanField(default=True, help_text="Enable flip animation")
    
    # Targeting
    counters = models.ManyToManyField(CounterDefinition, blank=True)
    site_counters = models.ManyToManyField(SiteCounter, blank=True)
    group_counters = models.ManyToManyField(GroupCounter, blank=True)
    council_types = models.ManyToManyField(CouncilType, blank=True)
    priority = models.IntegerField(default=0, help_text="Higher priority shows first")
    
    # Conditions for display
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    requires_previous_year = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-priority', 'name']
        verbose_name = "Factoid Template"
        verbose_name_plural = "Factoid Templates"

    def __str__(self):
        return f"{self.name} ({self.get_factoid_type_display()})"

    def save(self, *args, **kwargs):
        """Ensure a unique slug is generated if one isn't supplied."""
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)
            slug = base
            i = 1
            while FactoidTemplate.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class FactoidPlaylist(models.Model):
    """Manages factoid rotation for specific counter/council combinations"""
    
    counter = models.ForeignKey(CounterDefinition, on_delete=models.CASCADE)
    council = models.ForeignKey(Council, on_delete=models.CASCADE, null=True, blank=True)
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    
    factoid_templates = models.ManyToManyField(FactoidTemplate, through='PlaylistItem')
    auto_generate = models.BooleanField(default=True, help_text="Auto-generate relevant factoids")
    
    # Cache computed factoids as JSON
    computed_factoids = models.JSONField(default=list, blank=True)
    last_computed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['counter', 'council', 'year']
        verbose_name = "Factoid Playlist"
        verbose_name_plural = "Factoid Playlists"

    def __str__(self):
        council_name = self.council.name if self.council else "All Councils"
        return f"{self.counter.name} - {council_name} ({self.year.label})"


class PlaylistItem(models.Model):
    """Individual item in a factoid playlist with computed data"""
    
    playlist = models.ForeignKey(FactoidPlaylist, on_delete=models.CASCADE)
    factoid_template = models.ForeignKey(FactoidTemplate, on_delete=models.CASCADE)
    
    # Computed data for this specific context
    rendered_text = models.TextField(blank=True)
    computed_data = models.JSONField(default=dict)
    is_relevant = models.BooleanField(default=True)
    
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['playlist', 'factoid_template']
        verbose_name = "Playlist Item"
        verbose_name_plural = "Playlist Items"

    def __str__(self):
        return f"{self.playlist} - {self.factoid_template.name}"


# Legacy model for backward compatibility
class Factoid(models.Model):
    """Legacy factoid model - kept for backward compatibility"""

    FACTOID_TYPES = [
        ("percent_change", "Percentage change on last year"),
        ("highest", "Highest council"),
        ("lowest", "Lowest council"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    factoid_type = models.CharField(max_length=20, choices=FACTOID_TYPES)
    text = models.CharField(max_length=255)
    counters = models.ManyToManyField(CounterDefinition, blank=True)
    site_counters = models.ManyToManyField(SiteCounter, blank=True)
    group_counters = models.ManyToManyField(GroupCounter, blank=True)

    class Meta:
        verbose_name = "Legacy Factoid"
        verbose_name_plural = "Legacy Factoids"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure a unique slug is generated if one isn't supplied."""
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)
            slug = base
            i = 1
            while Factoid.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
