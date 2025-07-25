"""
Enhanced Factoid System Models

This module provides the core models for the new factoid system that is:
- Tightly integrated with data fields and counters
- Real-time reactive to field changes
- Built for modern React.js frontend
"""
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import re
import json


class FactoidTemplate(models.Model):
    """
    Enhanced factoid template with real-time field integration
    """
    FACTOID_TYPES = [
        ('context', '📋 Contextual Information'),
        ('comparison', '⚖️ Peer Comparison'), 
        ('trend', '📈 Multi-Year Trend'),
        ('ranking', '🏆 Council Ranking'),
        ('per_capita', '👤 Per Capita Analysis'),
        ('ratio', '🔢 Financial Ratio'),
        ('milestone', '🎯 Milestone Achievement'),
        ('sustainability', '🌱 Financial Health'),
        ('percent_change', '📊 Percentage Change'),
        ('anomaly', '⚠️ Data Anomaly'),
    ]
    
    COLOR_SCHEMES = [
        ('green', '🟢 Positive (Green)'),
        ('red', '🔴 Negative (Red)'),
        ('blue', '🔵 Neutral (Blue)'),
        ('orange', '🟠 Warning (Orange)'),
        ('purple', '🟣 Special (Purple)'),
    ]

    # Core template properties
    name = models.CharField(max_length=200, help_text="Descriptive name for this template")
    slug = models.SlugField(unique=True, blank=True)
    template_text = models.TextField(
        help_text="Template with {field} placeholders. Supports :currency, :percentage, :number formatters"
    )
    
    # Classification and appearance
    factoid_type = models.CharField(max_length=20, choices=FACTOID_TYPES, default='context')
    emoji = models.CharField(max_length=10, blank=True, help_text="Primary emoji for this factoid")
    color_scheme = models.CharField(max_length=20, choices=COLOR_SCHEMES, default='blue')
    
    # Behavior and targeting
    priority = models.IntegerField(default=50, help_text="Higher priority shows first (0-100)")
    is_active = models.BooleanField(default=True)
    
    # Value constraints (optional)
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    requires_previous_year = models.BooleanField(default=False)
    
    # Display settings
    animation_duration = models.PositiveIntegerField(
        default=5000, 
        help_text="Display duration in milliseconds"
    )
    flip_animation = models.BooleanField(default=True, help_text="Enable flip animation")
    
    # Real-time field tracking
    referenced_fields = models.JSONField(
        default=list, 
        help_text="Auto-populated list of field names referenced in template"
    )
    last_validated = models.DateTimeField(null=True, blank=True)
    validation_errors = models.JSONField(default=list)
    
    # Relationships
    council_types = models.ManyToManyField(
        'CouncilType', 
        blank=True,
        help_text="Limit to specific council types"
    )
    
    # Targeting specific counters/data
    target_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        help_text="What type of data this factoid applies to"
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target_object = GenericForeignKey('target_content_type', 'target_object_id')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_factoid_templates'
    )
    
    class Meta:
        verbose_name = "Factoid Template"
        verbose_name_plural = "Factoid Templates"
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['factoid_type', 'is_active']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Auto-extract referenced fields from template
        self.extract_referenced_fields()
        
        super().save(*args, **kwargs)
    
    def extract_referenced_fields(self):
        """
        Extract field references from template text for real-time tracking
        """
        # Pattern to match {field.name} or {field.name:format}
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, self.template_text)
        
        fields = []
        for match in matches:
            # Remove formatting (e.g., ":currency")
            field_name = match.split(':')[0]
            if field_name not in fields:
                fields.append(field_name)
        
        self.referenced_fields = fields
    
    def validate_template(self):
        """
        Validate template syntax and field references
        """
        errors = []
        
        # Check for balanced braces
        open_braces = self.template_text.count('{')
        close_braces = self.template_text.count('}')
        if open_braces != close_braces:
            errors.append("Mismatched braces in template")
        
        # Check field references exist
        from .field import DataField
        for field_name in self.referenced_fields:
            try:
                DataField.objects.get(variable_name=field_name)
            except DataField.DoesNotExist:
                errors.append(f"Referenced field '{field_name}' does not exist")
        
        self.validation_errors = errors
        return len(errors) == 0
    
    def get_applicable_councils(self):
        """
        Get councils this template applies to based on targeting rules
        """
        from .council import Council
        
        queryset = Council.objects.filter(is_live=True)
        
        if self.council_types.exists():
            queryset = queryset.filter(council_type__in=self.council_types.all())
        
        return queryset
    
    def render_for_context(self, context_data):
        """
        Render template with provided context data
        """
        template_text = self.template_text
        
        # Simple template rendering - can be enhanced with Jinja2 later
        for key, value in context_data.items():
            placeholder = f"{{{key}}}"
            if placeholder in template_text:
                template_text = template_text.replace(placeholder, str(value))
        
        return template_text
    
    def __str__(self):
        return f"{self.name} ({self.get_factoid_type_display()})"


class FactoidInstance(models.Model):
    """
    A computed factoid for a specific council/counter/year combination
    """
    template = models.ForeignKey(FactoidTemplate, on_delete=models.CASCADE)
    
    # Context
    council = models.ForeignKey('Council', on_delete=models.CASCADE)
    financial_year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE)
    
    # Optional counter context
    counter = models.ForeignKey(
        'CounterDefinition', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    # Rendered content
    rendered_text = models.TextField()
    computed_data = models.JSONField(default=dict, help_text="Source data used for rendering")
    
    # Relevance scoring
    relevance_score = models.FloatField(
        default=0.0,
        help_text="Computed relevance score (0.0-1.0)"
    )
    is_significant = models.BooleanField(default=True)
    
    # Cache control
    computed_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Factoid Instance"
        verbose_name_plural = "Factoid Instances"
        unique_together = ['template', 'council', 'financial_year', 'counter']
        indexes = [
            models.Index(fields=['council', 'financial_year']),
            models.Index(fields=['template', 'is_significant']),
            models.Index(fields=['relevance_score', '-computed_at']),
        ]
        ordering = ['-relevance_score', '-computed_at']
    
    def is_expired(self):
        """Check if this factoid instance needs recomputing"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def refresh_if_needed(self):
        """Recompute if expired or dependencies changed"""
        if self.is_expired():
            # Trigger recomputation
            from ..services.factoid_engine import FactoidEngine
            engine = FactoidEngine()
            return engine.compute_factoid_instance(self)
        return self
    
    def __str__(self):
        context = f"{self.council.name} ({self.financial_year})"
        if self.counter:
            context += f" - {self.counter.name}"
        return f"{self.template.name}: {context}"


class FactoidFieldDependency(models.Model):
    """
    Track which templates depend on which fields for real-time updates
    """
    template = models.ForeignKey(FactoidTemplate, on_delete=models.CASCADE)
    field = models.ForeignKey('DataField', on_delete=models.CASCADE)
    
    # Dependency strength
    is_critical = models.BooleanField(
        default=True,
        help_text="If true, changes to this field invalidate all instances"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['template', 'field']
        indexes = [
            models.Index(fields=['field', 'is_critical']),
        ]
    
    def __str__(self):
        return f"{self.template.name} depends on {self.field.name}"
