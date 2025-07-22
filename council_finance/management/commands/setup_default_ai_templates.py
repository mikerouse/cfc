"""
Management command to set up default AI analysis templates and configurations
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from council_finance.models import (
    AIProvider, AIModel, AIAnalysisTemplate, AIAnalysisConfiguration
)


class Command(BaseCommand):
    help = 'Set up default AI analysis templates and configurations'

    def handle(self, *args, **options):
        # Create OpenAI provider
        openai_provider, created = AIProvider.objects.get_or_create(
            slug='openai',
            defaults={
                'name': 'OpenAI',
                'api_endpoint': 'https://api.openai.com/v1',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created OpenAI provider'))

        # Create GPT-4 model
        gpt4_model, created = AIModel.objects.get_or_create(
            provider=openai_provider,
            model_id='gpt-4',
            defaults={
                'name': 'GPT-4',
                'max_tokens': 2000,
                'temperature': 0.7,
                'cost_per_token': 0.00003,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created GPT-4 model'))

        # Create default financial analysis template
        financial_template, created = AIAnalysisTemplate.objects.get_or_create(
            slug='council-financial-analysis',
            defaults={
                'name': 'Council Financial Analysis',
                'description': 'Comprehensive financial health analysis for UK councils',
                'analysis_type': 'financial_health',
                'system_prompt': """You are a financial analyst specializing in UK local government finance. 

Analyze the financial data for {{ council_name }}, a {{ council_type }} in the UK{% if population %} serving approximately {{ population|floatformat:"0" }} residents{% endif %}.

Focus your analysis on:

KEY INSIGHTS
- Overall financial health and sustainability
- Significant changes from previous year (if available)  
- Notable trends in debt, liabilities, and assets
- Efficiency and value for money indicators

RISK FACTORS  
- Financial sustainability concerns
- High debt levels or rapid debt growth
- Budget pressures or funding challenges
- Any red flags in the financial position

RECOMMENDATIONS
- Strategic financial management suggestions
- Areas for improvement or attention
- Benchmarking against similar councils
- Future financial planning considerations

Keep your analysis:
- Accessible to general public (avoid excessive jargon)
- Focused on practical implications for residents
- Balanced and evidence-based
- Concise but insightful

Context: This analysis appears on the council's financial transparency page to help residents understand their council's financial position.""",
                'context_fields': ['total_debt', 'current_liabilities', 'long_term_liabilities'],
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created financial analysis template'))

        # Create default configuration
        config, created = AIAnalysisConfiguration.objects.get_or_create(
            name='Default Financial Analysis',
            defaults={
                'model': gpt4_model,
                'template': financial_template,
                'cache_duration_minutes': 60,
                'max_retries': 3,
                'timeout_seconds': 30,
                'is_default': True,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created default configuration'))

        # Create additional templates for different analysis types
        debt_template, created = AIAnalysisTemplate.objects.get_or_create(
            slug='debt-analysis',
            defaults={
                'name': 'Debt Position Analysis',
                'description': 'Focus on debt levels, structure, and sustainability',
                'analysis_type': 'debt_analysis',
                'system_prompt': """You are analyzing the debt position of {{ council_name }}.

Focus on:

DEBT ANALYSIS
- Total debt levels and composition
- Debt per resident calculations
- Debt trend over time
- Debt servicing capacity

SUSTAINABILITY
- Debt-to-revenue ratios
- Long-term vs short-term debt mix
- Borrowing trends and future obligations

CONTEXT
- How this compares to similar councils
- Whether debt levels are appropriate for the council type
- Impact on financial flexibility

Keep analysis practical and resident-focused.""",
                'context_fields': ['total_debt', 'long_term_liabilities', 'current_liabilities'],
                'is_active': True
            }
        )

        comparison_template, created = AIAnalysisTemplate.objects.get_or_create(
            slug='year-comparison',
            defaults={
                'name': 'Year-over-Year Analysis',
                'description': 'Compare financial performance between years',
                'analysis_type': 'year_comparison',
                'system_prompt': """Compare {{ council_name }}'s financial performance between {{ current_year }} and the previous year.

KEY CHANGES
- Most significant financial changes
- Percentage increases/decreases in major categories
- Reasons for major variations

PERFORMANCE TRENDS  
- Improving or declining financial indicators
- Debt growth or reduction
- Revenue and expenditure patterns

IMPLICATIONS
- What these changes mean for residents
- Financial trajectory of the council
- Areas of concern or improvement

Focus on the most important year-over-year changes that residents should know about.""",
                'context_fields': ['total_debt', 'current_liabilities', 'total_expenditure'],
                'is_active': True
            }
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully set up AI analysis templates and configurations')
        )