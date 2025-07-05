from django.db import migrations


def add_council_website(apps, schema_editor):
    DataField = apps.get_model('council_finance', 'DataField')
    field, created = DataField.objects.get_or_create(
        slug='council_website',
        defaults={'name': 'Website address', 'content_type': 'url'}
    )
    if not created:
        return


def rename_website_field(apps, schema_editor):
    DataField = apps.get_model('council_finance', 'DataField')
    try:
        df = DataField.objects.get(slug='website')
    except DataField.DoesNotExist:
        return
    df.slug = 'council_website'
    df.content_type = 'url'
    df.save(update_fields=['slug', 'content_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0024_alter_blockedip_id_alter_rejectionlog_id'),
    ]

    operations = [
        migrations.RunPython(rename_website_field, migrations.RunPython.noop),
        migrations.RunPython(add_council_website, migrations.RunPython.noop),
    ]
