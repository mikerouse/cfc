"""
Management command to clear development caches and restart cleanly.
"""
import os
import shutil
import sys
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Clear development caches, compiled Python files, and other cached data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--templates',
            action='store_true',
            help='Also clear template cache',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear all possible caches (templates, static, etc.)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting development cache cleanup...')
        )

        # Clear Python cache files
        self._clear_python_cache()
        
        # Clear template cache if requested
        if options['templates'] or options['all']:
            self._clear_template_cache()
            
        # Clear static file cache if requested  
        if options['all']:
            self._clear_static_cache()
            
        # Clear Django's internal caches
        self._clear_django_caches()

        self.stdout.write(
            self.style.SUCCESS('Development cache cleanup completed successfully!')
        )
        self.stdout.write(
            'Tip: Use "python manage.py runserver" to start fresh'
        )

    def _clear_python_cache(self):
        """Clear Python __pycache__ directories and .pyc files."""
        self.stdout.write('Clearing Python cache files...')
        
        # Find and remove __pycache__ directories
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                cache_dir = os.path.join(root, '__pycache__')
                try:
                    shutil.rmtree(cache_dir)
                    self.stdout.write(f'  Removed: {cache_dir}')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Could not remove {cache_dir}: {e}')
                    )
        
        # Find and remove .pyc files
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.pyc'):
                    pyc_file = os.path.join(root, file)
                    try:
                        os.remove(pyc_file)
                        self.stdout.write(f'  Removed: {pyc_file}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'  Could not remove {pyc_file}: {e}')
                        )

    def _clear_template_cache(self):
        """Clear Django template cache."""
        self.stdout.write('Clearing template cache...')
        
        try:
            from django.core.cache import cache
            from django.template import engines
            
            # Clear the default cache
            cache.clear()
            
            # Clear template engines cache
            for engine in engines.all():
                if hasattr(engine, 'env') and hasattr(engine.env, 'cache'):
                    engine.env.cache.clear()
                    
            self.stdout.write('  Template cache cleared')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  Could not clear template cache: {e}')
            )

    def _clear_static_cache(self):
        """Clear static file cache directories."""
        self.stdout.write('Clearing static file cache...')
        
        # Common static cache directories
        cache_dirs = [
            'static/CACHE',
            'staticfiles/CACHE', 
            'static/admin/css/.sass-cache',
            'static/admin/js/.cache',
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    self.stdout.write(f'  Removed: {cache_dir}')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Could not remove {cache_dir}: {e}')
                    )

    def _clear_django_caches(self):
        """Clear Django's internal caches."""
        self.stdout.write('Clearing Django internal caches...')
        
        try:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write('  Django cache cleared')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  Could not clear Django cache: {e}')
            )
            
        try:
            # Clear URL resolver cache
            from django.urls import get_resolver
            from django.urls.resolvers import _get_cached_resolver
            
            # This clears the URL resolver cache
            _get_cached_resolver.cache_clear()
            self.stdout.write('  URL resolver cache cleared')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  Could not clear URL cache: {e}')
            )