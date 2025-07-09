from django.db import migrations

CHARACTERISTIC_SLUGS = [
    "council_type",
    "council_name",
    "population",
    "households",
    "council_website",
    "council_location",
]

def assign_characteristic_category(apps, schema_editor):
    DataField = apps.get_model("council_finance", "DataField")
    DataField.objects.filter(slug__in=CHARACTERISTIC_SLUGS).update(category="characteristic")

class Migration(migrations.Migration):
    dependencies = [
        ("council_finance", "0038_data_issue_model"),
    ]

    operations = [migrations.RunPython(assign_characteristic_category, migrations.RunPython.noop)]
