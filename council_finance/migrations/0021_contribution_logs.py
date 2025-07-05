from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0020_user_font_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="contribution",
            name="edited",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="points",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="rejection_count",
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name="RejectionLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "contribution",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="council_finance.contribution",
                    ),
                ),
                (
                    "council",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="council_finance.council",
                    ),
                ),
                (
                    "field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="council_finance.datafield",
                    ),
                ),
                (
                    "year",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="council_finance.financialyear",
                    ),
                ),
                ("value", models.CharField(max_length=255)),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("data_incorrect", "The data wasn't correct"),
                            ("no_sources", "We can't find reliable sources"),
                            ("other", "Other"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created"]},
        ),
    ]
