"""
Heroicon Validation Management Command

This command scans all templates for heroicon usage and validates that 
all referenced icons exist to prevent runtime errors.
"""
import os
import re
import glob
from django.core.management.base import BaseCommand
from django.template import Template, Context
from django.conf import settings


class Command(BaseCommand):
    help = 'Validate all heroicon references in templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix invalid icons by replacing with fallbacks',
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write("Scanning templates for heroicon usage...")
        
        # Find all template files
        template_dirs = []
        for app_config in settings.INSTALLED_APPS:
            if '.' not in app_config:  # Local apps only
                app_path = os.path.join(settings.BASE_DIR, app_config, 'templates')
                if os.path.exists(app_path):
                    template_dirs.append(app_path)
        
        # Also check main templates directory
        main_templates = os.path.join(settings.BASE_DIR, 'templates')
        if os.path.exists(main_templates):
            template_dirs.append(main_templates)
        
        errors_found = 0
        files_scanned = 0
        
        for template_dir in template_dirs:
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        errors = self.validate_template(file_path, fix=options['fix'])
                        errors_found += len(errors)
                        files_scanned += 1
        
        if errors_found == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All heroicons valid! Scanned {files_scanned} template files."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Found {errors_found} heroicon errors in {files_scanned} files."
                )
            )
            if not options['fix']:
                self.stdout.write("Run with --fix to automatically replace invalid icons with fallbacks.")
            return

    def validate_template(self, file_path, fix=False):
        """Validate heroicons in a single template file"""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all heroicon usages
            patterns = [
                r'{% heroicon "([^"]+)"[^}]*%}',
                r'{% heroicon_outline "([^"]+)"[^}]*%}',
                r'{% heroicon_solid "([^"]+)"[^}]*%}',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    icon_name = match.group(1)
                    full_match = match.group(0)
                    
                    # Test if the icon is valid
                    if not self.is_valid_heroicon(icon_name, full_match):
                        error = {
                            'file': file_path,
                            'icon': icon_name,
                            'line': content[:match.start()].count('\n') + 1,
                            'match': full_match
                        }
                        errors.append(error)
                        
                        self.stdout.write(
                            self.style.ERROR(
                                f"ERROR: {os.path.relpath(file_path)}:{error['line']} - Invalid icon '{icon_name}'"
                            )
                        )
                        
                        if fix:
                            # Replace with a safe fallback
                            fallback = self.get_icon_fallback(icon_name)
                            new_match = full_match.replace(f'"{icon_name}"', f'"{fallback}"')
                            content = content.replace(full_match, new_match)
                            
                            self.stdout.write(
                                self.style.WARNING(
                                    f"FIXED: Replaced '{icon_name}' with '{fallback}'"
                                )
                            )
            
            # Write back fixed content
            if fix and errors:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.stdout.write(
                    self.style.SUCCESS(f"FIXED: {os.path.relpath(file_path)}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error processing {file_path}: {e}")
            )
        
        return errors

    def is_valid_heroicon(self, icon_name, full_match):
        """Test if a heroicon is valid by attempting to render it"""
        try:
            # Create a minimal template to test the icon
            template_content = f"{{% load heroicons %}}{full_match}"
            template = Template(template_content)
            template.render(Context())
            return True
        except Exception as e:
            # If the original syntax fails, try alternative syntaxes
            try:
                # Try with size="mini" syntax
                test_template = f'{{% load heroicons %}}{{% heroicon "{icon_name}" size="mini" class="w-4 h-4" %}}'
                Template(test_template).render(Context())
                return True
            except Exception:
                try:
                    # Try with outline syntax
                    test_template = f'{{% load heroicons %}}{{% heroicon_outline "{icon_name}" class="w-4 h-4" %}}'
                    Template(test_template).render(Context())
                    return True
                except Exception:
                    return False

    def get_icon_fallback(self, invalid_icon):
        """Get a safe fallback icon for invalid ones"""
        fallbacks = {
            'arrow-path': 'refresh',
            'building-office': 'home',
            'arrow-clockwise': 'refresh',
            'arrow-circular': 'refresh',
            'chat-bubble-oval-left': 'chat',
            'chat-bubble-left': 'chat',
            'chat-bubble': 'chat',
            'arrow-up-tray': 'share',
            'cog-6-tooth': 'cog',
            'eye': 'eye',
            'eye-open': 'eye',
            'document-text': 'document',
            'document': 'document',
            'magnifying-glass-plus': 'search',
            'search': 'search',
            'swatch': 'information-circle',  # No valid color icon found
            'color-swatch': 'information-circle',
            'check': 'check',
            'check-circle': 'check',
            'refresh': 'refresh',
            'hand-thumb-up': 'thumb-up',
            'hand-thumb-down': 'thumb-down',
            'thumb-up-solid': 'thumb-up',
            'thumb-down-solid': 'thumb-down',
            'message': 'chat',
            'messages': 'chat',
            'comment': 'chat',
            'comments': 'chat',
            # Add more mappings as needed
        }
        
        return fallbacks.get(invalid_icon, 'information-circle')  # Default fallback