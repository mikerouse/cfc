# Generated custom migration to populate CouncilNation slugs

from django.db import migrations
from django.utils.text import slugify

def populate_nation_slugs(apps, schema_editor):
    """Populate slug field for existing CouncilNation records."""
    CouncilNation = apps.get_model('council_finance', 'CouncilNation')
    
    for nation in CouncilNation.objects.all():
        if not nation.slug:  # Only update if slug is empty
            nation.slug = slugify(nation.name)
            nation.save()

def reverse_populate_nation_slugs(apps, schema_editor):
    """Clear slug field for rollback."""
    CouncilNation = apps.get_model('council_finance', 'CouncilNation')
    CouncilNation.objects.update(slug='')

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0082_add_slug_to_council_nation'),
    ]

    operations = [
        migrations.RunPython(populate_nation_slugs, reverse_populate_nation_slugs),
    ]