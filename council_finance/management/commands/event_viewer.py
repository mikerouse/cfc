"""
Command-line Event Viewer tool for debugging and monitoring

Usage Examples:
    # Standard mode
    python manage.py event_viewer --recent 15m
    python manage.py event_viewer --source pdf_processor --level error
    python manage.py event_viewer --category ai_processing --count 20
    
    # Exclude INFO level events (show only warnings/errors)
    python manage.py event_viewer --exclude-level info
    
    # Real-time monitoring for errors and warnings only
    python manage.py event_viewer --monitor --exclude-level info --exclude-level debug
    
    # Monitor specific source with details
    python manage.py event_viewer --monitor --source pdf_processor --details
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import models
from datetime import timedelta
import re

try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False


class Command(BaseCommand):
    help = 'Command-line Event Viewer for debugging and monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recent',
            type=str,
            help='Show events from recent time period (e.g. 15m, 2h, 1d)',
            default='1h'
        )
        
        parser.add_argument(
            '--source',
            type=str,
            help='Filter by event source (pdf_processor, council_edit_api, ai_integration, etc.)',
        )
        
        parser.add_argument(
            '--level',
            type=str,
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Filter by event level'
        )
        
        parser.add_argument(
            '--exclude-level',
            type=str,
            action='append',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Exclude event levels (can be used multiple times: --exclude-level info --exclude-level debug)'
        )
        
        parser.add_argument(
            '--category',
            type=str,
            help='Filter by event category (data_processing, ai_processing, etc.)',
        )
        
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of events to display (default: 20)'
        )
        
        parser.add_argument(
            '--details',
            action='store_true',
            help='Show full event details'
        )
        
        parser.add_argument(
            '--search',
            type=str,
            help='Search in event title and message'
        )
        
        parser.add_argument(
            '--monitor',
            action='store_true',
            help='Real-time monitoring mode - continuously show new events (Ctrl+C to exit)'
        )
        
        parser.add_argument(
            '--monitor-interval',
            type=int,
            default=2,
            help='Monitoring refresh interval in seconds (default: 2)'
        )

    def handle(self, *args, **options):
        if not EVENT_VIEWER_AVAILABLE:
            self.stdout.write(
                self.style.ERROR('Event Viewer not available. Install event_viewer app.')
            )
            return

        # Check for monitoring mode
        if options['monitor']:
            self.run_monitor_mode(options)
            return

        # Standard mode - single query
        self.run_standard_mode(options)

    def run_standard_mode(self, options):
        """Run single query mode"""
        # Parse time period
        time_delta = self.parse_time_period(options['recent'])
        since_time = timezone.now() - time_delta

        # Build and execute query
        queryset = self.build_query(since_time, options)
        queryset = queryset.order_by('-timestamp')[:options['count']]
        events = list(queryset)
        
        if not events:
            self.stdout.write(
                self.style.WARNING('No events found matching criteria')
            )
            return

        # Display header and results
        self.display_header(len(events), options)
        for event in events:
            self.display_event(event, show_details=options['details'])
        self.display_footer(len(events), since_time)

    def run_monitor_mode(self, options):
        """Run real-time monitoring mode"""
        import time
        
        self.stdout.write(
            self.style.SUCCESS('\n[EVENT VIEWER - MONITOR MODE]')
        )
        self.stdout.write('Monitoring for new events... (Ctrl+C to exit)')
        
        # Show active filters
        filters = []
        if options['source']:
            filters.append(f"source={options['source']}")
        if options['level']:
            filters.append(f"level={options['level']}")
        if options['exclude_level']:
            filters.append(f"exclude={','.join(options['exclude_level'])}")
        if options['category']:
            filters.append(f"category={options['category']}")
        if options['search']:
            filters.append(f"search='{options['search']}'")
            
        if filters:
            self.stdout.write(f'Filters: {" | ".join(filters)}')
        
        self.stdout.write('=' * 80)
        
        # Track last seen event to avoid duplicates
        last_seen_id = self.get_latest_event_id()
        
        try:
            while True:
                # Check for new events since last check
                new_events = self.get_new_events_since(last_seen_id, options)
                
                for event in new_events:
                    self.display_event(event, show_details=options['details'])
                    last_seen_id = max(last_seen_id, event.id)
                
                if new_events:
                    self.stdout.write('─' * 40)  # Separator between batches
                
                time.sleep(options['monitor_interval'])
                
        except KeyboardInterrupt:
            self.stdout.write('\n\nMonitoring stopped by user')
            return

    def build_query(self, since_time, options):
        """Build filtered queryset based on options"""
        queryset = SystemEvent.objects.filter(timestamp__gte=since_time)
        
        if options['source']:
            queryset = queryset.filter(source=options['source'])
            
        if options['level']:
            queryset = queryset.filter(level=options['level'])
            
        # Handle level exclusions
        if options['exclude_level']:
            queryset = queryset.exclude(level__in=options['exclude_level'])
            
        if options['category']:
            queryset = queryset.filter(category=options['category'])
            
        if options['search']:
            search_term = options['search']
            queryset = queryset.filter(
                models.Q(title__icontains=search_term) |
                models.Q(message__icontains=search_term)
            )
        
        return queryset

    def get_latest_event_id(self):
        """Get the ID of the most recent event"""
        latest = SystemEvent.objects.order_by('-id').first()
        return latest.id if latest else 0

    def get_new_events_since(self, last_id, options):
        """Get new events since the given ID"""
        queryset = SystemEvent.objects.filter(id__gt=last_id)
        
        # Apply same filters as standard mode, but no time constraint
        if options['source']:
            queryset = queryset.filter(source=options['source'])
            
        if options['level']:
            queryset = queryset.filter(level=options['level'])
            
        # Handle level exclusions
        if options['exclude_level']:
            queryset = queryset.exclude(level__in=options['exclude_level'])
            
        if options['category']:
            queryset = queryset.filter(category=options['category'])
            
        if options['search']:
            search_term = options['search']
            queryset = queryset.filter(
                models.Q(title__icontains=search_term) |
                models.Q(message__icontains=search_term)
            )
        
        return list(queryset.order_by('timestamp'))  # Ascending for chronological display

    def display_header(self, event_count, options):
        """Display header information"""
        self.stdout.write(
            self.style.SUCCESS(f'\n[EVENT VIEWER] Found {event_count} events')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Time range: {options["recent"]} ago to now')
        )
        
        if options['source']:
            self.stdout.write(f'Source: {options["source"]}')
        if options['level']:
            self.stdout.write(f'Level: {options["level"].upper()}')
        if options['exclude_level']:
            self.stdout.write(f'Excluding levels: {", ".join(options["exclude_level"]).upper()}')
        if options['category']:
            self.stdout.write(f'Category: {options["category"]}')
            
        self.stdout.write('=' * 80)

    def display_footer(self, shown_count, since_time):
        """Display footer information"""
        total_count = SystemEvent.objects.filter(timestamp__gte=since_time).count()
        self.stdout.write('=' * 80)
        self.stdout.write(f'Showing {shown_count} of {total_count} total events')

    def display_event(self, event, show_details=False):
        """Display a single event with formatting"""
        
        # Time formatting
        time_str = event.timestamp.strftime('%H:%M:%S')
        
        # Level color coding
        level_colors = {
            'debug': self.style.HTTP_INFO,
            'info': self.style.SUCCESS,  
            'warning': self.style.WARNING,
            'error': self.style.ERROR,
            'critical': self.style.ERROR
        }
        
        level_color = level_colors.get(event.level, self.style.SUCCESS)
        
        # Level symbols
        level_symbols = {
            'debug': '[DEBUG]',
            'info': '[INFO]',
            'warning': '[WARN]',
            'error': '[ERROR]',
            'critical': '[CRIT]'
        }
        
        symbol = level_symbols.get(event.level, '[INFO]')
        
        # Main event line
        self.stdout.write(
            f'{time_str} {symbol} [{level_color(event.level.upper())}] {event.source}: {event.title}'
        )
        
        # Message (wrapped if long)
        if event.message:
            message = event.message
            if len(message) > 100 and not show_details:
                message = message[:97] + '...'
            self.stdout.write(f'    Message: {message}')
        
        # Details if requested
        if show_details and event.details:
            self.stdout.write('    Details:')
            for key, value in event.details.items():
                if isinstance(value, str) and len(value) > 200:
                    value = value[:197] + '...'
                self.stdout.write(f'      {key}: {value}')
        
        # Tags if available
        if event.tags:
            tags_str = ', '.join(event.tags)
            self.stdout.write(f'    Tags: {tags_str}')
            
        self.stdout.write('')  # Blank line

    def parse_time_period(self, period_str):
        """Parse time period string like '15m', '2h', '1d' into timedelta"""
        match = re.match(r'^(\d+)([mhd])$', period_str.lower())
        if not match:
            raise CommandError(f'Invalid time period format: {period_str}. Use format like: 15m, 2h, 1d')
        
        amount, unit = match.groups()
        amount = int(amount)
        
        if unit == 'm':
            return timedelta(minutes=amount)
        elif unit == 'h':
            return timedelta(hours=amount)
        elif unit == 'd':
            return timedelta(days=amount)
        else:
            raise CommandError(f'Invalid time unit: {unit}. Use m (minutes), h (hours), or d (days)')