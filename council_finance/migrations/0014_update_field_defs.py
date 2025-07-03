from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0013_datafield_list_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datafield",
            name="category",
            field=models.CharField(
                choices=[
                    ("balance_sheet", "Balance Sheet"),
                    ("cash_flow", "Cash Flow"),
                    ("income", "Income"),
                    ("spending", "Spending"),
                    ("general", "General"),
                    ("calculated", "Calculated"),
                ],
                default="general",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="figuresubmission",
            name="field",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="council_finance.datafield",
            ),
        ),
    ]

