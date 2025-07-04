from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def create_default_tiers(apps, schema_editor):
    TrustTier = apps.get_model('council_finance', 'TrustTier')
    tiers = [
        (1, 'New Counter'),
        (2, 'Steady Counter'),
        (3, 'Approved Counter'),
        (4, 'Counter Manager'),
        (5, 'King Counter'),
    ]
    for level, name in tiers:
        TrustTier.objects.get_or_create(level=level, defaults={'name': name})

class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0017_counter_show_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrustTier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={'ordering': ['level']},
        ),
        migrations.AddField(
            model_name='userprofile',
            name='tier',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='council_finance.trusttier'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='political_affiliation',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='works_for_council',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='employer_council',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='council_finance.council'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='official_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='official_email_confirmed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='official_email_token',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.CreateModel(
            name='Contribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('council', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='council_finance.council')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='council_finance.datafield')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='council_finance.financialyear')),
            ],
            options={'ordering': ['-created']},
        ),
        migrations.RunPython(create_default_tiers, migrations.RunPython.noop),
    ]
