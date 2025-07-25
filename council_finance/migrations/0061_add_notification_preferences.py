# Generated by Django 5.2.3 on 2025-07-22 18:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0060_enhance_pending_profile_change'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='contribution_notifications',
            field=models.BooleanField(default=True, help_text='Get notified when your contributions are reviewed'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='council_update_notifications',
            field=models.BooleanField(default=False, help_text='Receive notifications about councils you follow'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email_notifications',
            field=models.BooleanField(default=True, help_text='Receive email notifications for important updates'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='weekly_digest',
            field=models.BooleanField(default=False, help_text='Receive a weekly summary of activity and updates'),
        ),
        migrations.AlterField(
            model_name='pendingprofilechange',
            name='field',
            field=models.CharField(help_text='Field being changed', max_length=50),
        ),
        migrations.AlterField(
            model_name='pendingprofilechange',
            name='new_value',
            field=models.TextField(help_text='New value to be applied'),
        ),
    ]
