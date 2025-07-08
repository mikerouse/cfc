from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Factoid = apps.get_model('council_finance', 'Factoid')
    for factoid in Factoid.objects.filter(slug=''):
        base = slugify(factoid.name)
        slug = base
        i = 1
        while Factoid.objects.filter(slug=slug).exclude(pk=factoid.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        factoid.slug = slug
        factoid.save()

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0032_factoid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='factoid',
            name='slug',
            field=models.SlugField(unique=True, blank=True),
        ),
        migrations.RunPython(populate_slugs),
    ]
