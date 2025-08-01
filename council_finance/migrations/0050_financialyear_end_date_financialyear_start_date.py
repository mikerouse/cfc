# Generated by Django 5.2.3 on 2025-07-15 21:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0049_contributionv2_councilcharacteristic_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='financialyear',
            name='end_date',
            field=models.DateField(blank=True, help_text='When this financial year ends (optional)', null=True),
        ),
        migrations.AddField(
            model_name='financialyear',
            name='start_date',
            field=models.DateField(blank=True, help_text='When this financial year starts (optional)', null=True),
        ),
    ]
