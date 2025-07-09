from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("council_finance", "0037_reconcile_population_cache"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataIssue",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("issue_type", models.CharField(max_length=20)),
                ("value", models.CharField(blank=True, max_length=255)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("council", models.ForeignKey(on_delete=models.deletion.CASCADE, to="council_finance.council")),
                ("field", models.ForeignKey(on_delete=models.deletion.CASCADE, to="council_finance.datafield")),
                (
                    "year",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to="council_finance.financialyear"),
                ),
            ],
            options={
                "unique_together": {("council", "field", "year", "issue_type")},
                "ordering": ["council__name", "field__name"],
            },
        ),
    ]
