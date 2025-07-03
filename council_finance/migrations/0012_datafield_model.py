from django.db import migrations, models

# List of built-in slugs that must always exist in the system. These are
# created during the migration so new installations start with them.
PROTECTED_SLUGS = {
    "council_type": "Council Type",
    "council_name": "Council Name",
    "population": "Population",
    "households": "Residential Households",
}


def migrate_fields(apps):
    """Create DataField objects for existing field names and map submissions."""
    FigureSubmission = apps.get_model("council_finance", "FigureSubmission")
    DataField = apps.get_model("council_finance", "DataField")

    # Track created DataField objects by slug for quick lookup.
    cache = {}
    for fs in FigureSubmission.objects.all():
        slug = getattr(fs, "field_name")
        if slug not in cache:
            cache[slug], _ = DataField.objects.get_or_create(
                slug=slug, defaults={"name": slug.replace("_", " ").title()}
            )
        fs.field = cache[slug]
        fs.save(update_fields=["field"])


def create_core_fields(apps, schema_editor):
    """Ensure protected fields exist for new installations."""
    DataField = apps.get_model("council_finance", "DataField")
    for slug, name in PROTECTED_SLUGS.items():
        DataField.objects.get_or_create(slug=slug, defaults={"name": name})

class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0011_add_needs_populating_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataField",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("category", models.CharField(max_length=20, default="general")),
                ("explanation", models.TextField(blank=True)),
                ("content_type", models.CharField(max_length=20, default="text")),
                ("formula", models.CharField(blank=True, max_length=255)),
                ("required", models.BooleanField(default=False)),
            ],
        ),
        # Attach a foreign key to the new DataField definition. We use
        # ``models.deletion.CASCADE`` to maintain parity with the old behaviour
        # when a field was removed.
        migrations.AddField(
            model_name="figuresubmission",
            name="field",
            field=models.ForeignKey(
                to="council_finance.datafield",
                on_delete=models.deletion.CASCADE,
                null=True,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(create_core_fields, migrations.RunPython.noop),
        migrations.RunPython(
            lambda apps, schema_editor: migrate_fields(apps),
            migrations.RunPython.noop,
        ),
        # Update the unique constraint before removing the old column so SQLite
        # doesn't complain about missing fields referenced by the index.
        migrations.AlterUniqueTogether(
            name="figuresubmission",
            unique_together={("council", "year", "field")},
        ),
        migrations.RemoveField(
            model_name="figuresubmission",
            name="field_name",
        ),
    ]
