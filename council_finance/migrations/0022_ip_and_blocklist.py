from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0021_contribution_logs"),
    ]

    operations = [
        migrations.AddField(
            model_name="contribution",
            name="ip_address",
            field=models.GenericIPAddressField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="rejectionlog",
            name="ip_address",
            field=models.GenericIPAddressField(null=True, blank=True),
        ),
        migrations.CreateModel(
            name="BlockedIP",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("ip_address", models.GenericIPAddressField(unique=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created"]},
        ),
    ]
