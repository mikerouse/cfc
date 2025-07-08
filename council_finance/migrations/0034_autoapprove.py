from django.db import migrations, models
from django.conf import settings


def create_defaults(apps, schema_editor):
    SiteSetting = apps.get_model('council_finance', 'SiteSetting')
    SiteSetting.objects.get_or_create(
        key='auto_approve_min_verified_ips',
        defaults={'value': '1'}
    )
    SiteSetting.objects.get_or_create(
        key='auto_approve_min_approved',
        defaults={'value': '3'}
    )


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0033_factoid_slug_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='verified_ip_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='approved_submission_count',
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name='VerifiedIP',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('ip_address', models.GenericIPAddressField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='verified_ips', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created'], 'unique_together': {('user', 'ip_address')}},
        ),
        migrations.RunPython(create_defaults, migrations.RunPython.noop),
    ]
