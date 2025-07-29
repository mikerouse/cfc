"""
Management command to set up the council logo field.
"""

from django.core.management.base import BaseCommand
from council_finance.models import DataField


class Command(BaseCommand):
    help = 'Set up the council logo field for image uploads'

    def handle(self, *args, **options):
        self.stdout.write('Setting up council logo field...')
        
        # Create or update the council logo field
        logo_field, created = DataField.objects.get_or_create(
            slug='council_logo',
            defaults={
                'name': 'Council Logo',
                'category': 'characteristic',
                'content_type': 'image',
                'explanation': 'The official logo or coat of arms for the council',
                'required': False,
                # Default image constraints
                'image_max_width': 500,
                'image_max_height': 500,
                'image_max_file_size': 1024,  # 1MB in KB
                'image_default_alt_text': 'Council logo',
                'image_copyright_text': '',
                'image_ai_generated_flag': False,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created council logo field: {logo_field.slug}')
            )
        else:
            # Update content type if it wasn't already set correctly
            if logo_field.content_type != 'image':
                logo_field.content_type = 'image'
                logo_field.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated council logo field content type to image: {logo_field.slug}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Council logo field already exists: {logo_field.slug}')
                )
        
        self.stdout.write('Council logo field setup complete!')