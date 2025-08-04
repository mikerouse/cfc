"""
Log File Parsers for Event Viewer

Parses existing log files and imports them into SystemEvent model.
Each parser handles a specific log format and type.
"""

import re
import os
from datetime import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from ..models import SystemEvent

User = get_user_model()


class BaseLogParser:
    """Base class for log parsers."""
    
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.source = 'log_parser'
        self.parsed_count = 0
        self.error_count = 0
        
    def parse_file(self, dry_run=False):
        """Parse the entire log file."""
        if not os.path.exists(self.log_file_path):
            return {'error': f'Log file not found: {self.log_file_path}'}
        
        results = {
            'file': self.log_file_path,
            'parsed': 0,
            'errors': 0,
            'skipped': 0,
            'dry_run': dry_run
        }
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                for line_num, line in enumerate(file, 1):
                    try:
                        event_data = self.parse_line(line.strip(), line_num)
                        if event_data:
                            if not dry_run:
                                self.create_system_event(event_data)
                            results['parsed'] += 1
                        else:
                            results['skipped'] += 1
                    except Exception as e:
                        results['errors'] += 1
                        if results['errors'] <= 5:  # Only log first 5 errors
                            print(f"Error parsing line {line_num}: {e}")
                        
        except Exception as e:
            results['error'] = f'Failed to read file: {e}'
        
        return results
    
    def parse_line(self, line, line_num):
        """Parse a single log line. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement parse_line")
    
    def create_system_event(self, event_data):
        """Create a SystemEvent from parsed data."""
        # Check if event already exists to avoid duplicates
        existing = SystemEvent.objects.filter(
            fingerprint=event_data.get('fingerprint', ''),
            timestamp=event_data['timestamp']
        ).first()
        
        if existing:
            # Update occurrence count
            existing.occurrence_count += 1
            existing.last_seen = timezone.now()
            existing.save()
            return existing
        
        return SystemEvent.objects.create(**event_data)


class GodModeLogParser(BaseLogParser):
    """Parser for god_mode.log files."""
    
    def __init__(self, log_file_path):
        super().__init__(log_file_path)
        self.source = 'log_parser'
        
        # Pattern: 2025-07-05 19:49:43,210 INFO mikerouse accessed God Mode via GET
        self.pattern = re.compile(
            r'(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) '
            r'(?P<level>\w+) '
            r'(?P<username>\w+) '
            r'(?P<message>.*)'
        )
    
    def parse_line(self, line, line_num):
        if not line.strip():
            return None
            
        match = self.pattern.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Parse timestamp
        try:
            dt = datetime.strptime(data['datetime'], '%Y-%m-%d %H:%M:%S,%f')
            timestamp = timezone.make_aware(dt)
        except ValueError:
            return None
        
        # Get user
        user = None
        try:
            user = User.objects.get(username=data['username'])
        except User.DoesNotExist:
            pass
        
        return {
            'source': self.source,
            'level': 'info',
            'category': 'security',
            'title': f"God Mode Access: {data['username']}",
            'message': data['message'],
            'timestamp': timestamp,
            'user': user,
            'details': {
                'log_file': 'god_mode.log',
                'original_level': data['level'],
                'line_number': line_num,
            },
            'tags': ['god_mode', 'admin_access', 'security'],
            'fingerprint': f"god_mode-{data['username']}-access",
        }


class SyntaxErrorLogParser(BaseLogParser):
    """Parser for syntax_errors.log files."""
    
    def __init__(self, log_file_path):
        super().__init__(log_file_path)
        self.source = 'test_runner'
        self.current_section = None
        self.buffer = []
        
    def parse_file(self, dry_run=False):
        """Override to handle multi-line parsing."""
        if not os.path.exists(self.log_file_path):
            return {'error': f'Log file not found: {self.log_file_path}'}
        
        results = {
            'file': self.log_file_path,
            'parsed': 0,
            'errors': 0,
            'skipped': 0,
            'dry_run': dry_run
        }
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                
                # Extract timestamp from header
                timestamp_match = re.search(r'Generated: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
                if timestamp_match:
                    try:
                        dt = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                        timestamp = timezone.make_aware(dt)
                    except ValueError:
                        timestamp = timezone.now()
                else:
                    timestamp = timezone.now()
                
                # Check if this is a test failure
                if 'TEST FAILURES' in content or 'TESTS FAILED' in content:
                    level = 'error'
                    category = 'test_failure'
                    title = 'Comprehensive Test Failures Detected'
                    
                    # Extract test output section
                    test_output = ''
                    if 'TEST OUTPUT:' in content:
                        test_output = content.split('TEST OUTPUT:')[1][:2000]  # Limit size
                    
                    event_data = {
                        'source': self.source,
                        'level': level,
                        'category': category,
                        'title': title,
                        'message': test_output or content[:1000],
                        'timestamp': timestamp,
                        'details': {
                            'log_file': 'syntax_errors.log',
                            'test_type': 'comprehensive',
                        },
                        'tags': ['test_failure', 'syntax_error', 'validation'],
                        'fingerprint': f"test_failure-comprehensive-{timestamp.date()}",
                    }
                    
                    if not dry_run:
                        self.create_system_event(event_data)
                    results['parsed'] = 1
                else:
                    results['skipped'] = 1
                
        except Exception as e:
            results['error'] = f'Failed to read file: {e}'
        
        return results
    
    def parse_line(self, line, line_num):
        # Not used in this parser - we override parse_file instead
        return None


class FactoidDebugLogParser(BaseLogParser):
    """Parser for factoid_debug.log files."""
    
    def __init__(self, log_file_path):
        super().__init__(log_file_path)
        self.source = 'ai_system'
    
    def parse_line(self, line, line_num):
        if not line.strip():
            return None
        
        # Simple factoid debug entries
        timestamp = timezone.now()  # Use current time since no timestamp in file
        
        return {
            'source': self.source,
            'level': 'debug',
            'category': 'integration',
            'title': 'Factoid Debug Entry',
            'message': line,
            'timestamp': timestamp,
            'details': {
                'log_file': 'factoid_debug.log',
                'line_number': line_num,
            },
            'tags': ['factoid', 'ai_system', 'debug'],
            'fingerprint': f"factoid_debug-{line_num}",
        }


class ServerLogParser(BaseLogParser):
    """Parser for server.log and server2.log files."""
    
    def __init__(self, log_file_path):
        super().__init__(log_file_path)
        self.source = 'django_error'
        
        # Common Django error patterns
        self.error_patterns = [
            (re.compile(r'ERROR.*'), 'error'),
            (re.compile(r'WARNING.*'), 'warning'),
            (re.compile(r'CRITICAL.*'), 'critical'),
            (re.compile(r'INFO.*'), 'info'),
        ]
    
    def parse_line(self, line, line_num):
        if not line.strip():
            return None
        
        # Determine level
        level = 'info'
        for pattern, log_level in self.error_patterns:
            if pattern.search(line):
                level = log_level
                break
        
        # Skip info level entries to reduce noise
        if level == 'info':
            return None
        
        timestamp = timezone.now()  # Default to now since format varies
        
        return {
            'source': self.source,
            'level': level,
            'category': 'exception' if level in ['error', 'critical'] else 'configuration',
            'title': f'Server Log: {level.upper()}',
            'message': line[:500],  # Limit message length
            'timestamp': timestamp,
            'details': {
                'log_file': os.path.basename(self.log_file_path),
                'line_number': line_num,
            },
            'tags': ['server_log', 'django'],
            'fingerprint': f"server_log-{level}-{line_num % 100}",  # Group similar entries
        }


class ResponseLogParser(BaseLogParser):
    """Parser for response.log files."""
    
    def __init__(self, log_file_path):
        super().__init__(log_file_path)
        self.source = 'api'
    
    def parse_line(self, line, line_num):
        if not line.strip():
            return None
        
        # Filter out HTML content and curl progress output
        if any(marker in line for marker in [
            '<!DOCTYPE', '<html', '<head', '<body', '<script', '<style',
            'Content-Type: text/html', '% Total', '% Received', 'Dload', 'Upload',
            'Content-Length:', 'X-Frame-Options:', 'Set-Cookie:', 'Date:', 'Server:'
        ]):
            return None
        
        # Only process lines that look like HTTP responses or proper log entries
        if not any(marker in line for marker in [
            'HTTP/', 'GET ', 'POST ', 'PUT ', 'DELETE ', 'PATCH ',
            '[INFO]', '[DEBUG]', '[WARNING]', '[ERROR]', '[CRITICAL]'
        ]):
            return None
        
        # Skip successful responses to reduce noise
        if '200' in line or '201' in line or '204' in line:
            return None
        
        # Focus on errors and warnings
        level = 'warning'
        if any(code in line for code in ['400', '401', '403', '404', '500', '502', '503']):
            level = 'error'
        
        timestamp = timezone.now()
        
        return {
            'source': self.source,
            'level': level,
            'category': 'integration',
            'title': 'API Response Issue',
            'message': line[:300],
            'timestamp': timestamp,
            'details': {
                'log_file': 'response.log',
                'line_number': line_num,
            },
            'tags': ['api', 'response', 'http'],
            'fingerprint': f"response_log-{level}",
        }


class LogParsingService:
    """Main service for parsing all log files."""
    
    def __init__(self):
        self.parsers = {
            'god_mode.log': GodModeLogParser,
            'syntax_errors.log': SyntaxErrorLogParser,
            'factoid_debug.log': FactoidDebugLogParser,
            'server.log': ServerLogParser,
            'server2.log': ServerLogParser,
            'response.log': ResponseLogParser,
        }
        self.stats = {
            'start_time': None,
            'end_time': None,
            'duration': None,
        }
    
    def parse_all_logs(self, dry_run=False, logs_dir='logs'):
        """Parse all available log files."""
        import time
        self.stats['start_time'] = time.time()
        
        results = {
            'summary': {
                'total_files': 0,
                'successful_files': 0,
                'failed_files': 0,
                'total_events': 0,
                'total_errors': 0,
                'total_skipped': 0,
            },
            'files': {}
        }
        
        # Find all log files
        if os.path.exists(logs_dir):
            for filename in os.listdir(logs_dir):
                if filename.endswith('.log') and filename in self.parsers:
                    log_path = os.path.join(logs_dir, filename)
                    parser_class = self.parsers[filename]
                    parser = parser_class(log_path)
                    
                    print(f"Parsing {filename}...")
                    file_result = parser.parse_file(dry_run=dry_run)
                    
                    results['files'][filename] = file_result
                    results['summary']['total_files'] += 1
                    
                    if 'error' in file_result:
                        results['summary']['failed_files'] += 1
                    else:
                        results['summary']['successful_files'] += 1
                        results['summary']['total_events'] += file_result.get('parsed', 0)
                        results['summary']['total_errors'] += file_result.get('errors', 0)
                        results['summary']['total_skipped'] += file_result.get('skipped', 0)
        
        # Calculate duration
        import time
        self.stats['end_time'] = time.time()
        self.stats['duration'] = round(self.stats['end_time'] - self.stats['start_time'], 2)
        results['stats'] = self.stats.copy()
        
        return results
    
    def parse_single_log(self, log_file_path, dry_run=False):
        """Parse a single log file."""
        filename = os.path.basename(log_file_path)
        
        if filename not in self.parsers:
            return {
                'error': f'No parser available for {filename}. Available parsers: {list(self.parsers.keys())}'
            }
        
        parser_class = self.parsers[filename]
        parser = parser_class(log_file_path)
        
        return parser.parse_file(dry_run=dry_run)