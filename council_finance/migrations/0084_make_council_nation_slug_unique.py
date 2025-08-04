# Generated custom migration to make CouncilNation slug unique

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0083_populate_council_nation_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='councilnation',
            name='slug',
            field=models.SlugField(blank=True, help_text='URL-friendly version of name', max_length=100, unique=True),
        ),
    ]