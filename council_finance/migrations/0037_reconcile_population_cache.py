from django.db import migrations


def forwards(apps, schema_editor):
    from council_finance.population import reconcile_populations

    reconcile_populations()


class Migration(migrations.Migration):
    dependencies = [
        ("council_finance", "0036_population_cache"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

