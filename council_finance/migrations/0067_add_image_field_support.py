# Generated by Django 5.2.3 on 2025-07-29 00:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('council_finance', '0066_add_new_field_content_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='datafield',
            name='image_ai_generated_flag',
            field=models.BooleanField(default=False, help_text='Flag to indicate if image was AI-generated'),
        ),
        migrations.AddField(
            model_name='datafield',
            name='image_copyright_text',
            field=models.TextField(blank=True, help_text='Copyright notice for image fields'),
        ),
        migrations.AddField(
            model_name='datafield',
            name='image_default_alt_text',
            field=models.CharField(blank=True, help_text='Default ALT text for image fields', max_length=255),
        ),
        migrations.AddField(
            model_name='datafield',
            name='image_max_file_size',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum file size in KB for image fields', null=True),
        ),
        migrations.AddField(
            model_name='datafield',
            name='image_max_height',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum height in pixels for image fields', null=True),
        ),
        migrations.AddField(
            model_name='datafield',
            name='image_max_width',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum width in pixels for image fields', null=True),
        ),
        migrations.AlterField(
            model_name='datafield',
            name='content_type',
            field=models.CharField(choices=[('monetary', 'Monetary'), ('integer', 'Integer'), ('text', 'Text'), ('url', 'URL'), ('postcode', 'Post Code'), ('phone', 'Phone Number'), ('latlong', 'Latitude/Longitude'), ('date', 'Date'), ('time', 'Time'), ('datetime', 'Date & Time'), ('boolean', 'True/False'), ('list', 'List'), ('image', 'Image')], default='text', max_length=20),
        ),
    ]
