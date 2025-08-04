# Generated custom migration to populate CouncilNation enhanced fields with UK data

from django.db import migrations
from decimal import Decimal

def populate_nation_data(apps, schema_editor):
    """Populate enhanced fields for UK nations with realistic data."""
    CouncilNation = apps.get_model('council_finance', 'CouncilNation')
    
    # UK nation data - ONS official population figures (67.6M total UK population)
    nation_data = {
        'England': {
            'total_population': 57106000,  # ONS official figure
            'council_count': 343,  # Including districts, unitaries, counties, London boroughs
            'capital_city': 'London',
            'total_area_km2': Decimal('130279.0'),
            'display_colour': '#1d70b8',  # GOV.UK blue
        },
        'Scotland': {
            'total_population': 5448000,  # ONS official figure
            'council_count': 32,
            'capital_city': 'Edinburgh',
            'total_area_km2': Decimal('77933.0'),
            'display_colour': '#005eb8',  # Scottish blue
        },
        'Wales': {
            'total_population': 3132000,  # ONS official figure
            'council_count': 22,
            'capital_city': 'Cardiff',
            'total_area_km2': Decimal('20735.0'),
            'display_colour': '#d4351c',  # Welsh red
        },
        'Northern Ireland': {
            'total_population': 1911000,  # ONS official figure
            'council_count': 11,
            'capital_city': 'Belfast',
            'total_area_km2': Decimal('13562.0'),
            'display_colour': '#00703c',  # Northern Ireland green
        },
        'Islands': {
            'total_population': 165000,  # Approximate for Crown dependencies
            'council_count': 3,  # Isle of Man, Jersey, Guernsey
            'capital_city': 'Douglas',  # Isle of Man as largest
            'total_area_km2': Decimal('572.0'),
            'display_colour': '#f47738',  # Orange for distinctiveness
        }
    }
    
    for nation in CouncilNation.objects.all():
        if nation.name in nation_data:
            data = nation_data[nation.name]
            nation.total_population = data['total_population']
            nation.council_count = data['council_count']
            nation.capital_city = data['capital_city']
            nation.total_area_km2 = data['total_area_km2']
            nation.display_colour = data['display_colour']
            nation.currency_code = 'GBP'  # All UK nations use GBP
            nation.save()

def reverse_populate_nation_data(apps, schema_editor):
    """Clear enhanced fields for rollback."""
    CouncilNation = apps.get_model('council_finance', 'CouncilNation')
    
    CouncilNation.objects.update(
        total_population=None,
        council_count=None,
        capital_city='',
        total_area_km2=None,
        display_colour='#1d70b8',  # Reset to default
        currency_code='GBP'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0085_add_enhanced_fields_to_council_nation'),
    ]

    operations = [
        migrations.RunPython(populate_nation_data, reverse_populate_nation_data),
    ]