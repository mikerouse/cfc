# Generated by Django 5.2.4 on 2025-07-04 23:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0019_data_change_log"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="preferred_font",
            field=models.CharField(blank=True, default="Cairo", max_length=100),
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
        migrations.AlterField(
            model_name="datafield",
            name="id",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]
