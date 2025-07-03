from django.db import migrations, models


def create_default(apps, schema_editor):
    SiteSetting = apps.get_model('council_finance', 'SiteSetting')
    SiteSetting.objects.get_or_create(key='default_financial_year', value='2023/24')


class Migration(migrations.Migration):
    dependencies = [
        ('council_finance', '0015_merge_20250703_1617'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSetting',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.CharField(blank=True, max_length=200)),
            ],
        ),
        migrations.RunPython(create_default, migrations.RunPython.noop),
    ]
