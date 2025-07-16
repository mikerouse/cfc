from django.db import migrations, models
import django.contrib.contenttypes.models


def setup_list_fields(apps, schema_editor):
    """Set up council_type and council_nation as list fields with proper dataset_type."""
    DataField = apps.get_model("council_finance", "DataField")
    ContentType = apps.get_model("contenttypes", "ContentType")
    CouncilType = apps.get_model("council_finance", "CouncilType")
    CouncilNation = apps.get_model("council_finance", "CouncilNation")
    
    # Set up council_type field
    try:
        council_type_field = DataField.objects.get(slug="council_type")
        council_type_ct = ContentType.objects.get_for_model(CouncilType)
        council_type_field.content_type = "list"
        council_type_field.dataset_type = council_type_ct
        council_type_field.save()
        print(f"Updated council_type field: content_type=list, dataset_type={council_type_ct}")
    except DataField.DoesNotExist:
        print("council_type field not found")
    
    # Set up council_nation field
    try:
        council_nation_field = DataField.objects.get(slug="council_nation")
        council_nation_ct = ContentType.objects.get_for_model(CouncilNation)
        council_nation_field.content_type = "list"
        council_nation_field.dataset_type = council_nation_ct
        council_nation_field.save()
        print(f"Updated council_nation field: content_type=list, dataset_type={council_nation_ct}")
    except DataField.DoesNotExist:
        print("council_nation field not found")


def reverse_list_fields(apps, schema_editor):
    """Reverse the list field setup."""
    DataField = apps.get_model("council_finance", "DataField")
    
    # Revert council_type field
    try:
        council_type_field = DataField.objects.get(slug="council_type")
        council_type_field.content_type = "text"
        council_type_field.dataset_type = None
        council_type_field.save()
    except DataField.DoesNotExist:
        pass
    
    # Revert council_nation field
    try:
        council_nation_field = DataField.objects.get(slug="council_nation")
        council_nation_field.content_type = "text"
        council_nation_field.dataset_type = None
        council_nation_field.save()
    except DataField.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0025_council_website_protected"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # First ensure the content_type field supports "list" option
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
        # Then run the data migration to set up the list fields
        migrations.RunPython(setup_list_fields, reverse_list_fields),
    ]
