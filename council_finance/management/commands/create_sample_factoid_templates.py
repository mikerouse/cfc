"""
Management command to create sample factoid templates for testing the enhanced factoid system.
"""
from django.core.management.base import BaseCommand
from council_finance.models import FactoidTemplate, CounterDefinition, CouncilType


class Command(BaseCommand):
    help = 'Create sample factoid templates for testing the enhanced factoid system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing templates before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing factoid templates...')
            FactoidTemplate.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing templates'))

        # Sample factoid templates
        templates_data = [
            {
                'name': 'Year-over-year percentage change',
                'factoid_type': 'percent_change',
                'template_text': '**{{change}}%** {{change_direction}} vs last year ({{previous_formatted}} → {{formatted}})',
                'emoji': '📈',
                'color_scheme': 'green',
                'priority': 100,
                'requires_previous_year': True,
                'animation_duration': 6000,
                'is_active': True
            },
            {
                'name': 'Per capita financial impact',
                'factoid_type': 'per_capita',
                'template_text': '**{{per_capita}}** per resident in {{council_name}}',
                'emoji': '👤',
                'color_scheme': 'purple',
                'priority': 90,
                'animation_duration': 7000,
                'is_active': True
            },
            {
                'name': 'Council ranking position',
                'factoid_type': 'ranking',
                'template_text': 'Ranks **{{position}}** out of {{total}} councils',
                'emoji': '🏆',
                'color_scheme': 'blue',
                'priority': 80,
                'animation_duration': 5000,
                'is_active': True
            },
            {
                'name': 'Large debt warning',
                'factoid_type': 'anomaly',
                'template_text': 'This represents a significant financial commitment for {{council_name}}',
                'emoji': '⚠️',
                'color_scheme': 'orange',
                'priority': 95,
                'min_value': 50000000,  # £50M
                'animation_duration': 8000,
                'is_active': True
            },
            {
                'name': 'Financial context',
                'factoid_type': 'context',
                'template_text': 'Based on {{council_name}}\'s {{year_label}} financial statements',
                'emoji': '📋',
                'color_scheme': 'blue',
                'priority': 70,
                'animation_duration': 6000,
                'is_active': True
            },
            {
                'name': 'Positive trend indicator',
                'factoid_type': 'trend',
                'template_text': 'Strong financial position compared to previous years',
                'emoji': '📈',
                'color_scheme': 'green',
                'priority': 75,
                'animation_duration': 7000,
                'is_active': True
            },
            {
                'name': 'Council type comparison',
                'factoid_type': 'comparison',
                'template_text': 'Typical for a {{council_type}} council of this size',
                'emoji': '⚖️',
                'color_scheme': 'blue',
                'priority': 65,
                'animation_duration': 6500,
                'is_active': True
            },
            {
                'name': 'Milestone achievement',
                'factoid_type': 'milestone',
                'template_text': 'Represents a significant milestone in council financing',
                'emoji': '🎯',
                'color_scheme': 'green',
                'priority': 85,
                'min_value': 100000000,  # £100M
                'animation_duration': 8000,
                'is_active': True
            },
            {
                'name': 'Sustainability insight',
                'factoid_type': 'sustainability',
                'template_text': 'Part of {{council_name}}\'s long-term financial sustainability strategy',
                'emoji': '🌱',
                'color_scheme': 'green',
                'priority': 60,
                'animation_duration': 7500,
                'is_active': True
            },
            {
                'name': 'Ratio analysis',
                'factoid_type': 'ratio',
                'template_text': 'This represents {{percentage}}% of {{council_name}}\'s total annual budget',
                'emoji': '🔢',
                'color_scheme': 'purple',
                'priority': 70,
                'animation_duration': 6000,
                'is_active': True
            }
        ]

        created_templates = []
        for template_data in templates_data:
            template, created = FactoidTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_templates.append(template)
                self.stdout.write(f'Created template: {template.name}')

        # Associate templates with all counters for testing
        all_counters = CounterDefinition.objects.all()
        for template in created_templates:
            template.counters.set(all_counters)
            self.stdout.write(f'Associated "{template.name}" with {all_counters.count()} counters')

        # Associate some templates with specific council types
        district_councils = CouncilType.objects.filter(name__icontains='district')
        county_councils = CouncilType.objects.filter(name__icontains='county')
        
        for template in created_templates[:3]:  # First 3 templates
            if district_councils.exists():
                template.council_types.add(district_councils.first())
            if county_councils.exists():
                template.council_types.add(county_councils.first())

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(created_templates)} factoid templates!'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                'Templates are now associated with all counters. '
                'You can modify associations in the admin interface.'
            )
        )