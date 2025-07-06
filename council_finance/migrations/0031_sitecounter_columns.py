from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0030_sitecounter_explanation"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitecounter",
            name="columns",
            field=models.PositiveIntegerField(default=1, choices=[(1, "1"), (2, "2"), (3, "3")]),
        ),
    ]
