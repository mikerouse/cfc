"""
Management command to parse log files into SystemEvent records.

Usage:
    python manage.py parse_logs                    # Parse all logs (dry run)
    python manage.py parse_logs --execute          # Parse and import all logs  
    python manage.py parse_logs --file server.log  # Parse specific file
    python manage.py parse_logs --clear-first      # Clear existing events first
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
from event_viewer.services.log_parsers import LogParsingService
from event_viewer.models import SystemEvent


class Command(BaseCommand):
    help = 'Parse log files and import them into SystemEvent model'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually import the events (default is dry run)',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Parse only a specific log file',
        )
        parser.add_argument(
            '--logs-dir',
            type=str,
            default='logs',
            help='Directory containing log files (default: logs)',
        )
        parser.add_argument(
            '--clear-first',
            action='store_true',
            help='Clear existing SystemEvents with source=log_parser before importing',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        service = LogParsingService()
        
        # Handle dry run vs execute
        dry_run = not options['execute']
        if dry_run:
            self.stdout.write("[DRY RUN] No events will be created")
        else:
            self.stdout.write("[EXECUTE] Events will be imported")
        
        # Clear existing log-parsed events if requested
        if options['clear_first'] and not dry_run:
            deleted_count = SystemEvent.objects.filter(source='log_parser').count()
            SystemEvent.objects.filter(source='log_parser').delete()
            self.stdout.write(f"Cleared {deleted_count} existing log-parsed events")
        
        # Parse single file or all files
        if options['file']:
            log_file_path = os.path.join(options['logs_dir'], options['file'])
            self.stdout.write(f"Parsing single file: {log_file_path}")
            
            result = service.parse_single_log(log_file_path, dry_run=dry_run)
            self.display_file_result(options['file'], result, options['verbose'])
        else:
            self.stdout.write(f"Parsing all log files in: {options['logs_dir']}")
            
            results = service.parse_all_logs(dry_run=dry_run, logs_dir=options['logs_dir'])
            self.display_results(results, options['verbose'])
        
        if dry_run:
            self.stdout.write("\nRun with --execute to actually import the events")
    
    def display_results(self, results, verbose):
        """Display parsing results summary."""
        summary = results['summary']
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("PARSING SUMMARY")
        self.stdout.write("="*60)
        
        self.stdout.write(f"Total files processed: {summary['total_files']}")
        self.stdout.write(f"Successful: {summary['successful_files']}")
        self.stdout.write(f"Failed: {summary['failed_files']}")
        self.stdout.write(f"Events created: {summary['total_events']}")
        self.stdout.write(f"Parse errors: {summary['total_errors']}")
        
        if verbose:
            self.stdout.write("\n" + "-"*40)
            self.stdout.write("FILE DETAILS")
            self.stdout.write("-"*40)
            
            for filename, file_result in results['files'].items():
                self.display_file_result(filename, file_result, verbose)
    
    def display_file_result(self, filename, result, verbose):
        """Display results for a single file."""
        if 'error' in result:
            self.stdout.write(f"[ERROR] {filename}: {result['error']}")
        else:
            status = "[OK]" if result['parsed'] > 0 else "[WARN]"
            self.stdout.write(
                f"{status} {filename}: "
                f"{result['parsed']} events, "
                f"{result['errors']} errors, "
                f"{result['skipped']} skipped"
            )
            
            if verbose and result['parsed'] > 0:
                self.stdout.write(f"   File: {result['file']}")
                if result['dry_run']:
                    self.stdout.write("   (dry run - no events actually created)")
    
    def style_text(self, text, style):
        """Apply styling to text."""
        return getattr(self.style, style.upper())(text)