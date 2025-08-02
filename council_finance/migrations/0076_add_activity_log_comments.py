# Generated migration for ActivityLogComment model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('council_finance', '0075_add_text_value_to_financial_figure'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLogComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(help_text='The comment content')),
                ('is_approved', models.BooleanField(default=True, help_text='Whether this comment is approved for display')),
                ('is_flagged', models.BooleanField(default=False, help_text='Whether this comment has been flagged for review')),
                ('like_count', models.PositiveIntegerField(default=0, help_text='Number of likes this comment has received')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this comment was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this comment was last updated')),
                ('activity_log', models.ForeignKey(help_text='The activity log entry this comment relates to', on_delete=django.db.models.deletion.CASCADE, related_name='following_comments', to='council_finance.activitylog')),
                ('parent', models.ForeignKey(blank=True, help_text='Parent comment if this is a reply', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='council_finance.activitylogcomment')),
                ('user', models.ForeignKey(help_text='User who made this comment', on_delete=django.db.models.deletion.CASCADE, related_name='activity_log_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='activitylogcomment',
            index=models.Index(fields=['activity_log', 'is_approved', 'created_at'], name='council_fin_activit_4c8b9c_idx'),
        ),
        migrations.AddIndex(
            model_name='activitylogcomment',
            index=models.Index(fields=['user', '-created_at'], name='council_fin_user_id_b8c726_idx'),
        ),
        migrations.AddIndex(
            model_name='activitylogcomment',
            index=models.Index(fields=['parent'], name='council_fin_parent__6c0421_idx'),
        ),
        migrations.AddIndex(
            model_name='activitylogcomment',
            index=models.Index(fields=['is_flagged'], name='council_fin_is_flag_e31c5b_idx'),
        ),
    ]