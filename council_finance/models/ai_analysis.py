"""
AI Analysis Models for Council Finance Analysis System
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class AIProvider(models.Model):
    """AI Provider configuration (OpenAI, Anthropic, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    api_endpoint = models.URLField(blank=True, help_text="Custom API endpoint if needed")
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "AI Provider"
        verbose_name_plural = "AI Providers"

    def __str__(self):
        return self.name


class AIModel(models.Model):
    """AI Model configuration for analysis"""
    provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=200)
    model_id = models.CharField(max_length=200, help_text="API model identifier (e.g., gpt-4, claude-3-opus)")
    max_tokens = models.IntegerField(default=2000, validators=[MinValueValidator(100), MaxValueValidator(8000)])
    temperature = models.FloatField(default=0.7, validators=[MinValueValidator(0.0), MaxValueValidator(2.0)])
    is_active = models.BooleanField(default=True)
    cost_per_token = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['provider__name', 'name']
        unique_together = ['provider', 'model_id']
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"

    def __str__(self):
        return f"{self.provider.name} - {self.name}"


class AIAnalysisTemplate(models.Model):
    """System prompt templates for different types of analysis"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    system_prompt = models.TextField(
        help_text="System prompt with Django template variables available: {{council}}, {{current_year}}, {{previous_year}}, {{financial_data}}, etc."
    )
    context_fields = models.JSONField(
        default=list,
        help_text="List of data fields to include in analysis context (e.g., ['total_debt', 'current_liabilities'])"
    )
    analysis_type = models.CharField(max_length=50, choices=[
        ('financial_health', 'Financial Health Analysis'),
        ('year_comparison', 'Year-over-Year Comparison'),
        ('debt_analysis', 'Debt Position Analysis'),
        ('budget_analysis', 'Budget Analysis'),
        ('risk_assessment', 'Risk Assessment'),
        ('peer_comparison', 'Peer Council Comparison'),
        ('general', 'General Analysis'),
    ], default='general')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "AI Analysis Template"
        verbose_name_plural = "AI Analysis Templates"

    def __str__(self):
        return self.name


class AIAnalysisConfiguration(models.Model):
    """Configuration for AI analysis system"""
    name = models.CharField(max_length=200, unique=True)
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    template = models.ForeignKey(AIAnalysisTemplate, on_delete=models.CASCADE)
    cache_duration_minutes = models.IntegerField(
        default=60,
        validators=[MinValueValidator(5), MaxValueValidator(1440)],
        help_text="How long to cache analysis results (5-1440 minutes)"
    )
    max_retries = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    timeout_seconds = models.IntegerField(default=30, validators=[MinValueValidator(10), MaxValueValidator(120)])
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        verbose_name = "AI Analysis Configuration"
        verbose_name_plural = "AI Analysis Configurations"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default configuration
            AIAnalysisConfiguration.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.model})"


class CouncilAIAnalysis(models.Model):
    """Generated AI analysis results for councils"""
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='ai_analyses')
    year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE)
    configuration = models.ForeignKey(AIAnalysisConfiguration, on_delete=models.CASCADE)
    
    # Analysis content
    analysis_text = models.TextField()
    analysis_summary = models.TextField(blank=True, help_text="Brief summary for sidebar display")
    key_insights = models.JSONField(default=list, help_text="List of key insight strings")
    risk_factors = models.JSONField(default=list, help_text="List of identified risk factors")
    recommendations = models.JSONField(default=list, help_text="List of recommendations")
    
    # Metadata
    input_data = models.JSONField(help_text="Financial data used for analysis")
    tokens_used = models.IntegerField(null=True, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    cost_estimate = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cached', 'From Cache'),
    ], default='pending')
    error_message = models.TextField(blank=True)
    
    created = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this analysis expires and should be regenerated")

    class Meta:
        ordering = ['-created']
        unique_together = ['council', 'year', 'configuration']
        verbose_name = "Council AI Analysis"
        verbose_name_plural = "Council AI Analyses"

    def __str__(self):
        return f"{self.council.name} - {self.year.label} - {self.configuration.name}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def get_formatted_insights(self):
        """Return insights formatted for display"""
        if not self.key_insights:
            return []
        return [insight.strip() for insight in self.key_insights if insight.strip()]