from django.db import migrations


def normalise_blank_values(apps, schema_editor):
    """Ensure blank values are stored consistently as empty strings."""
    FigureSubmission = apps.get_model("council_finance", "FigureSubmission")
    FigureSubmission.objects.filter(value__isnull=True).update(value="")
    FigureSubmission.objects.filter(value="").update(value="")


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0009_counter_precision"),
    ]

    operations = [
        migrations.RunPython(normalise_blank_values, migrations.RunPython.noop),
    ]
