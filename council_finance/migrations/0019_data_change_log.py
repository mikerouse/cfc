from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('council_finance', '0018_trust_tier_and_contributions'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_value', models.CharField(blank=True, max_length=255)),
                ('new_value', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('contribution', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='council_finance.contribution')),
                ('council', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='council_finance.council')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='council_finance.datafield')),
                ('year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='council_finance.financialyear')),
            ],
            options={'ordering': ['-created']},
        ),
    ]
