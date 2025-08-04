# Generated custom migration to populate CouncilType enhanced fields

from django.db import migrations
from django.utils.text import slugify

def populate_council_type_data(apps, schema_editor):
    """Populate enhanced fields for UK council types with realistic data."""
    CouncilType = apps.get_model('council_finance', 'CouncilType')
    
    # UK council type data with tier levels and characteristics
    council_type_data = {
        'Unitary': {
            'tier_level': 1,
            'council_count': 183,  # Approximate number of unitary authorities in UK
            'display_colour': '#1d70b8',  # GOV.UK blue
            'description': 'Single-tier local authorities responsible for all local government services in their area, combining county and district functions.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/Unitary_authority'
        },
        'County': {
            'tier_level': 2,
            'council_count': 26,  # County councils in England
            'display_colour': '#00703c',  # Green for upper tier
            'description': 'Upper-tier authorities responsible for services like education, social services, transport, and strategic planning across multiple districts.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/County_council'
        },
        'District': {
            'tier_level': 3,
            'council_count': 164,  # District councils in England
            'display_colour': '#d4351c',  # Red for lower tier
            'description': 'Lower-tier authorities responsible for local services like housing, planning applications, waste collection, and local taxation.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/District_council_(England)'
        },
        'London Borough': {
            'tier_level': 1,  # Function as unitaries within London
            'council_count': 32,  # 32 London boroughs
            'display_colour': '#6f72af',  # Purple for London
            'description': 'Local authorities within Greater London, responsible for most local services except those provided by the Greater London Authority.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/London_boroughs'
        },
        'Combined Authority': {
            'tier_level': 2,  # Strategic/upper tier role
            'council_count': 10,  # Approximate number
            'display_colour': '#f47738',  # Orange for special authorities
            'description': 'Strategic authorities covering multiple council areas, focusing on economic development, transport, and strategic planning.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/Combined_authority'
        },
        'Mayoral Authority': {
            'tier_level': 2,  # Strategic level
            'council_count': 11,  # Metro mayors
            'display_colour': '#ffb81c',  # Gold for mayoral
            'description': 'Areas with directly elected mayors who have powers over transport, housing, skills, and economic development.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/Metro_mayor'
        },
        'Devolved Assembly': {
            'tier_level': 1,  # National level for devolved nations
            'council_count': 3,  # Scotland, Wales, Northern Ireland
            'display_colour': '#742c95',  # Purple for devolved
            'description': 'Devolved national governments responsible for areas like health, education, and local government within their nations.',
            'wikipedia_url': 'https://en.wikipedia.org/wiki/Devolution_in_the_United_Kingdom'
        }
    }
    
    for council_type in CouncilType.objects.all():
        # Generate slug for all types
        if not council_type.slug:
            council_type.slug = slugify(council_type.name)
        
        # Set defaults for all types
        council_type.is_active = True
        
        # Apply specific data if available
        if council_type.name in council_type_data:
            data = council_type_data[council_type.name]
            council_type.tier_level = data['tier_level']
            council_type.council_count = data['council_count']
            council_type.display_colour = data['display_colour']
            council_type.description = data['description']
            council_type.wikipedia_url = data['wikipedia_url']
        else:
            # Defaults for unknown types
            council_type.tier_level = 5  # Other/Special Purpose
            council_type.council_count = None
            council_type.display_colour = '#1d70b8'  # Default blue
            council_type.description = f'{council_type.name} local authority'
            council_type.wikipedia_url = ''
        
        council_type.save()

def reverse_populate_council_type_data(apps, schema_editor):
    """Clear enhanced fields for rollback."""
    CouncilType = apps.get_model('council_finance', 'CouncilType')
    
    CouncilType.objects.update(
        slug='',
        tier_level=None,
        council_count=None,
        is_active=True,
        display_colour='#1d70b8',
        description='',
        wikipedia_url=''
    )

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0087_add_enhanced_fields_to_council_type'),
    ]

    operations = [
        migrations.RunPython(populate_council_type_data, reverse_populate_council_type_data),
    ]