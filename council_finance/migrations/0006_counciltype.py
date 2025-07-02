from django.db import migrations, models
import django.db.models.deletion


def copy_types_forward(apps, schema_editor):
    Council = apps.get_model('council_finance', 'Council')
    CouncilType = apps.get_model('council_finance', 'CouncilType')
    for council in Council.objects.all():
        if getattr(council, 'council_type', None):
            ct, _ = CouncilType.objects.get_or_create(name=council.council_type)
            council.council_type_new = ct
            council.save(update_fields=['council_type_new'])


def populate_defaults(apps, schema_editor):
    CouncilType = apps.get_model('council_finance', 'CouncilType')
    defaults = [
        'Unitary',
        'County',
        'Combined Authority',
        'Mayoral Authority',
        'Devolved Assembly',
        'District',
        'Metropolitan Borough',
        'Non-Metropolitan Borough',
        'London Borough',
        'Parish / Town',
    ]
    for name in defaults:
        CouncilType.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0005_notification'),
    ]

    operations = [
        migrations.CreateModel(
            name='CouncilType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='council',
            name='council_type_new',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='council_finance.counciltype'),
        ),
        migrations.RunPython(populate_defaults),
        migrations.RunPython(copy_types_forward),
        migrations.RemoveField(
            model_name='council',
            name='council_type',
        ),
        migrations.RenameField(
            model_name='council',
            old_name='council_type_new',
            new_name='council_type',
        ),
    ]
