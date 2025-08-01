# Generated by Django 5.2.3 on 2025-07-03 14:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0012_datafield_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datafield',
            name='category',
            field=models.CharField(choices=[('balance_sheet', 'Balance Sheet'), ('cash_flow', 'Cash Flow'), ('income', 'Income'), ('spending', 'Spending'), ('general', 'General'), ('calculated', 'Calculated')], default='general', max_length=20),
        ),
        migrations.AlterField(
            model_name='datafield',
            name='content_type',
            field=models.CharField(choices=[('monetary', 'Monetary'), ('integer', 'Integer'), ('text', 'Text'), ('url', 'URL')], default='text', max_length=20),
        ),
        migrations.AlterField(
            model_name='datafield',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='figuresubmission',
            name='field',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='council_finance.datafield'),
        ),
    ]
