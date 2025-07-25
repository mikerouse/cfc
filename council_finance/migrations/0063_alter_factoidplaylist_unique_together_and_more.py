# Generated by Django 5.2.3 on 2025-07-24 21:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0062_fix_expires_at_field'),
    ]

    operations = [
        # migrations.AlterUniqueTogether(
        #     name='factoidplaylist',
        #     unique_together=None,
        # ),
        migrations.RemoveField(
            model_name='factoidplaylist',
            name='council',
        ),
        migrations.RemoveField(
            model_name='factoidplaylist',
            name='counter',
        ),
        migrations.RemoveField(
            model_name='factoidplaylist',
            name='factoid_templates',
        ),
        migrations.RemoveField(
            model_name='factoidplaylist',
            name='year',
        ),
        migrations.RemoveField(
            model_name='playlistitem',
            name='playlist',
        ),
        migrations.RemoveField(
            model_name='factoidtemplate',
            name='council_types',
        ),
        migrations.RemoveField(
            model_name='factoidtemplate',
            name='counters',
        ),
        migrations.RemoveField(
            model_name='factoidtemplate',
            name='group_counters',
        ),
        migrations.RemoveField(
            model_name='factoidtemplate',
            name='site_counters',
        ),
        migrations.RemoveField(
            model_name='playlistitem',
            name='factoid_template',
        ),
        # migrations.AlterUniqueTogether(
        #     name='playlistitem',
        #     unique_together=None,
        # ),
        migrations.DeleteModel(
            name='Factoid',
        ),
        migrations.DeleteModel(
            name='FactoidPlaylist',
        ),
        migrations.DeleteModel(
            name='FactoidTemplate',
        ),
        migrations.DeleteModel(
            name='PlaylistItem',
        ),
    ]
