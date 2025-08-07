"""
Check Auth0 configuration
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Check Auth0 configuration and environment variables'

    def handle(self, *args, **options):
        self.stdout.write("Auth0 Configuration Check")
        self.stdout.write("=" * 50)
        
        # Check environment variables
        env_vars = {
            'AUTH0_DOMAIN': os.getenv('AUTH0_DOMAIN'),
            'AUTH0_CLIENT_ID': os.getenv('AUTH0_CLIENT_ID'),
            'AUTH0_CLIENT_SECRET': os.getenv('AUTH0_CLIENT_SECRET'),
            'AUTH0_CALLBACK_URL': os.getenv('AUTH0_CALLBACK_URL'),
        }
        
        self.stdout.write("\nEnvironment Variables:")
        for key, value in env_vars.items():
            if value:
                if 'SECRET' in key:
                    display_value = value[:10] + '...' if len(value) > 10 else value
                else:
                    display_value = value
                self.stdout.write(f"  {key}: {display_value}")
            else:
                self.stdout.write(self.style.ERROR(f"  {key}: NOT SET"))
        
        # Check Django settings
        self.stdout.write("\nDjango Settings:")
        django_settings = {
            'SOCIAL_AUTH_AUTH0_DOMAIN': getattr(settings, 'SOCIAL_AUTH_AUTH0_DOMAIN', None),
            'SOCIAL_AUTH_AUTH0_KEY': getattr(settings, 'SOCIAL_AUTH_AUTH0_KEY', None),
            'SOCIAL_AUTH_AUTH0_SECRET': getattr(settings, 'SOCIAL_AUTH_AUTH0_SECRET', None),
        }
        
        for key, value in django_settings.items():
            if value:
                if 'SECRET' in key:
                    display_value = value[:10] + '...' if len(value) > 10 else value
                else:
                    display_value = value
                self.stdout.write(f"  {key}: {display_value}")
            else:
                self.stdout.write(self.style.ERROR(f"  {key}: NOT SET"))
        
        # Check authentication backends
        self.stdout.write("\nAuthentication Backends:")
        for backend in settings.AUTHENTICATION_BACKENDS:
            self.stdout.write(f"  - {backend}")
        
        # Recommendations
        self.stdout.write("\nRecommendations:")
        if not env_vars['AUTH0_DOMAIN']:
            self.stdout.write(self.style.WARNING(
                "- Set AUTH0_DOMAIN environment variable on your production server"
            ))
        if not env_vars['AUTH0_CLIENT_ID']:
            self.stdout.write(self.style.WARNING(
                "- Set AUTH0_CLIENT_ID environment variable on your production server"
            ))
        if not env_vars['AUTH0_CLIENT_SECRET']:
            self.stdout.write(self.style.WARNING(
                "- Set AUTH0_CLIENT_SECRET environment variable on your production server"
            ))
        
        if env_vars['AUTH0_CALLBACK_URL'] and 'localhost' in env_vars['AUTH0_CALLBACK_URL']:
            self.stdout.write(self.style.WARNING(
                "- Update AUTH0_CALLBACK_URL for production (currently set to localhost)"
            ))
        
        self.stdout.write("\nAuth0 Dashboard Settings:")
        self.stdout.write("Make sure these URLs are added to your Auth0 application:")
        self.stdout.write(f"  - Callback URL: https://beta.councillor.pro/auth/complete/auth0/")
        self.stdout.write(f"  - Logout URL: https://beta.councillor.pro/")
        self.stdout.write(f"  - Web Origins: https://beta.councillor.pro")