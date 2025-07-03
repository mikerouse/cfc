from django.db import migrations, models
import django.contrib.contenttypes.models


def set_council_type_dataset(apps, schema_editor):
    """Attach the CouncilType model as the dataset for the council_type field."""
    DataField = apps.get_model("council_finance", "DataField")
    ContentType = apps.get_model("contenttypes", "ContentType")
    CouncilType = apps.get_model("council_finance", "CouncilType")
    # ``get_for_model`` will create the content type if it does not yet exist,
    # which avoids ordering issues during initial migrations.
    ct_model = ContentType.objects.get_for_model(CouncilType)
    DataField.objects.filter(slug="council_type").update(dataset_type=ct_model, content_type="list")


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0012_datafield_model"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="datafield",
            name="dataset_type",
            field=models.ForeignKey(
                blank=True,
                help_text="Model providing options for list values",
                null=True,
                on_delete=models.deletion.SET_NULL,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="datafield",
            name="content_type",
            field=models.CharField(
                choices=[
                    ("monetary", "Monetary"),
                    ("integer", "Integer"),
                    ("text", "Text"),
                    ("url", "URL"),
                    ("list", "List"),
                ],
                default="text",
                max_length=20,
            ),
        ),
        migrations.RunPython(set_council_type_dataset, migrations.RunPython.noop),
    ]

