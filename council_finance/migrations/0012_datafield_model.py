from django.db import migrations, models, deletion


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
        migrations.AddField(
            model_name="figuresubmission",
            name="field",
            field=models.ForeignKey(
                to="council_finance.datafield",
                on_delete=deletion.CASCADE,
                null=True,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(
            lambda apps, schema_editor: migrate_fields(apps),
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="figuresubmission",
            name="field_name",
        ),
        migrations.AlterUniqueTogether(
            name="figuresubmission",
            unique_together={("council", "year", "field")},
        ),
    ]
