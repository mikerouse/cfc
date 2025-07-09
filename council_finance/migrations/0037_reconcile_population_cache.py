from django.db import migrations, transaction


def forwards(apps, schema_editor):
    """Update cached population figures using historical models."""
    Council = apps.get_model("council_finance", "Council")
    DataField = apps.get_model("council_finance", "DataField")
    FigureSubmission = apps.get_model("council_finance", "FigureSubmission")

    pop_field = DataField.objects.filter(slug="population").first()
    if not pop_field:
        return

    with transaction.atomic():
        for council in Council.objects.all():
            latest = (
                FigureSubmission.objects.filter(council=council, field=pop_field)
                .select_related("year")
                .order_by("-year__label")
                .first()
            )
            if latest:
                try:
                    value = int(float(latest.value))
                except (TypeError, ValueError):
                    value = None
            else:
                value = None
            if council.latest_population != value:
                council.latest_population = value
                council.save(update_fields=["latest_population"])


class Migration(migrations.Migration):
    dependencies = [
        ("council_finance", "0036_population_cache"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

