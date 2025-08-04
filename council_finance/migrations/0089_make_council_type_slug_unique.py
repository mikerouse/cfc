# Generated custom migration to make CouncilType slug unique

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0088_populate_council_type_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='counciltype',
            name='slug',
            field=models.SlugField(blank=True, help_text='URL-friendly version of name', max_length=100, unique=True),
        ),
    ]