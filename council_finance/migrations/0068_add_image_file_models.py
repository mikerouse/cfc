# Generated by Django 5.2.3 on 2025-07-29 00:25

import council_finance.models.image_file
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0067_add_image_field_support'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ImageFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=council_finance.models.image_file.image_upload_path, validators=[council_finance.models.image_file.validate_image_file])),
                ('original_filename', models.CharField(max_length=255)),
                ('file_size', models.PositiveIntegerField()),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('alt_text', models.CharField(blank=True, help_text='Alternative text for accessibility', max_length=255)),
                ('copyright_text', models.TextField(blank=True, help_text='Copyright notice or attribution')),
                ('is_ai_generated', models.BooleanField(default=False, help_text='Was this image generated by AI?')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this image is currently in use')),
                ('is_approved', models.BooleanField(default=False, help_text='Whether this image has been approved for use')),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_images', to=settings.AUTH_USER_MODEL)),
                ('council', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='image_files', to='council_finance.council')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='council_finance.datafield')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='ImageFileHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('uploaded', 'Uploaded'), ('approved', 'Approved'), ('replaced', 'Replaced'), ('deactivated', 'Deactivated'), ('metadata_updated', 'Metadata Updated')], max_length=20)),
                ('details', models.TextField(blank=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('image_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='council_finance.imagefile')),
            ],
            options={
                'ordering': ['-changed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='imagefile',
            index=models.Index(fields=['council', 'field', 'is_active'], name='council_fin_council_b4b922_idx'),
        ),
        migrations.AddIndex(
            model_name='imagefile',
            index=models.Index(fields=['is_approved', 'uploaded_at'], name='council_fin_is_appr_f6c59f_idx'),
        ),
        migrations.AddIndex(
            model_name='imagefilehistory',
            index=models.Index(fields=['image_file', 'changed_at'], name='council_fin_image_f_78e9bf_idx'),
        ),
    ]
