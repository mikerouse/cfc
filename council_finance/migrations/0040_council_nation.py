from django.db import migrations, models
import django.db.models.deletion


def create_nations(apps, schema_editor):
    """Populate default council nations and link the DataField."""
    CouncilNation = apps.get_model('council_finance', 'CouncilNation')
    DataField = apps.get_model('council_finance', 'DataField')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Default nation names
    defaults = [
        'England',
        'Wales',
        'Scotland',
        'Northern Ireland',
        'Islands',
    ]
    for name in defaults:
        CouncilNation.objects.get_or_create(name=name)

    ct_model = ContentType.objects.get_for_model(CouncilNation)
    DataField.objects.get_or_create(
        slug='council_nation',
        defaults={
            'name': 'Council nation',
            'category': 'characteristic',
            'content_type': 'list',
            'dataset_type': ct_model,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ('council_finance', '0039_characteristic_category'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='CouncilNation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': 'Council nation',
                'verbose_name_plural': 'Council nations',
            },
        ),
        migrations.AddField(
            model_name='council',
            name='council_nation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='council_finance.councilnation',
            ),
        ),
        migrations.RunPython(create_nations, migrations.RunPython.noop),
    ]
