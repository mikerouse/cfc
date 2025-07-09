from django.db import migrations


def rename_field(apps, schema_editor):
    DataField = apps.get_model('council_finance', 'DataField')
    DataField.objects.filter(slug='council_location').update(slug='council_hq_post_code')


class Migration(migrations.Migration):
    dependencies = [
        ('council_finance', '0040_council_nation'),
    ]

    operations = [
        migrations.RunPython(rename_field, migrations.RunPython.noop),
    ]
