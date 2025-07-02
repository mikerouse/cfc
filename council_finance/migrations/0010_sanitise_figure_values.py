from django.db import migrations


def clean_blank_values(apps, schema_editor):
    """Replace blank or null FigureSubmission values with '0'."""
    FigureSubmission = apps.get_model('council_finance', 'FigureSubmission')
    FigureSubmission.objects.filter(value__isnull=True).update(value='0')
    FigureSubmission.objects.filter(value='').update(value='0')


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0009_counter_precision"),
    ]

    operations = [
        migrations.RunPython(clean_blank_values, migrations.RunPython.noop),
    ]
