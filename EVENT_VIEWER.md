# EVENT VIEWER SYSTEM DOCUMENTATION

**CRITICAL**: This system provides comprehensive error monitoring and debugging capabilities for superadmin users. Always reference this document when working on system monitoring, error tracking, or log analysis features.

## System Overview

The Event Viewer is a custom Django-based monitoring solution that captures, analyzes, and presents system events for troubleshooting and debugging. It **complements** (does not replace) the existing ActivityLog system.

### Key Design Principles
- **No Disruption**: Preserves all existing error handling and email alerts
- **Complementary**: Works alongside ActivityLog for comprehensive coverage
- **GOV.UK Design**: Flat, accessible interface following government design standards
- **Superuser Only**: Secure access control for administrative monitoring

## Architecture

### Core Models

#### SystemEvent Model (`event_viewer/models.py`)
```python
class SystemEvent(models.Model):
    # Core event data
    source = models.CharField(max_length=50, choices=EVENT_SOURCES)
    level = models.CharField(max_length=20, choices=EVENT_LEVELS)
    category = models.CharField(max_length=50, choices=EVENT_CATEGORIES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Context and metadata
    user = models.ForeignKey(User, null=True, blank=True)
    request_path = models.CharField(max_length=500, null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Technical details
    stack_trace = models.TextField(null=True, blank=True)
    details = models.JSONField(default=dict)
    tags = models.JSONField(default=list)
    
    # Deduplication and tracking
    fingerprint = models.CharField(max_length=64, db_index=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
```

#### EventSummary Model
Daily aggregation model for analytics and trend analysis.

### Event Sources & Categories

#### Sources
- `django_error`: Django error handler captures
- `middleware`: Error middleware captures  
- `log_parser`: Parsed from existing log files
- `ai_system`: AI factoid system events
- `test_runner`: Test failure detection
- `security`: God mode and authentication events
- `api`: API response monitoring

#### Categories
- `exception`: Runtime errors and exceptions
- `security`: Authentication and access events
- `integration`: API and external service issues
- `test_failure`: Automated test failures
- `configuration`: System configuration issues
- `performance`: Performance-related events

## Log Parsing System

### Overview
The log parsing system automatically imports events from existing log files using specialized parsers.

### Available Parsers (`event_viewer/services/log_parsers.py`)

#### 1. GodModeLogParser
- **File**: `logs/god_mode.log`
- **Purpose**: Security access tracking
- **Pattern**: `2025-07-05 19:49:43,210 INFO mikerouse accessed God Mode via GET`
- **Events**: Admin access monitoring

#### 2. SyntaxErrorLogParser  
- **File**: `syntax_errors.log`
- **Purpose**: Test failure detection
- **Features**: Multi-line parsing, timestamp extraction
- **Events**: Comprehensive test failures

#### 3. ResponseLogParser
- **File**: `response.log`
- **Purpose**: API response monitoring
- **Filtering**: HTML content protection, success filtering
- **Events**: API errors and warnings only

#### 4. ServerLogParser
- **Files**: `server.log`, `server2.log`
- **Purpose**: Django error logging
- **Filtering**: Error/warning/critical only (skips info)
- **Events**: Server-side errors

#### 5. FactoidDebugLogParser
- **File**: `factoid_debug.log`
- **Purpose**: AI system debugging
- **Events**: Factoid system debugging entries

### Data Quality Protection

#### HTML Content Filtering
The ResponseLogParser includes comprehensive filtering to prevent HTML content and curl output from creating junk events:

```python
# Filters out these patterns
html_markers = [
    '<!DOCTYPE', '<html', '<head', '<body', '<script', '<style',
    'Content-Type: text/html', '% Total', '% Received', 'Dload', 'Upload',
    'Content-Length:', 'X-Frame-Options:', 'Set-Cookie:', 'Date:', 'Server:'
]
```

#### Fingerprinting & Deduplication
- Uses SHA-256 fingerprints to group similar events
- Increments `occurrence_count` instead of creating duplicates
- Updates `last_seen` timestamp for recurring events

### Management Commands

#### parse_logs Command
```bash
# Dry run (default) - shows what would be imported
python manage.py parse_logs

# Execute import
python manage.py parse_logs --execute

# Parse specific file
python manage.py parse_logs --file god_mode.log --execute

# Parse different directory
python manage.py parse_logs --logs-dir /path/to/logs --execute

# Clear existing events first
python manage.py parse_logs --clear-first --execute

# Verbose output with details
python manage.py parse_logs --verbose
```

## User Interface

### Access Control
- **URL**: `/system-events/`
- **Permission**: Superuser only (`@user_passes_test(lambda u: u.is_superuser)`)
- **Design**: GOV.UK-inspired flat design, no unnecessary icons

### Pages

#### 1. Dashboard (`/system-events/`)
- Recent events overview
- Event level distribution (error, warning, info)
- Top event sources
- System health indicators

#### 2. Event List (`/system-events/events/`)
- Filterable table of all events
- Search functionality
- Pagination
- Level-based color coding

#### 3. Event Detail (`/system-events/events/<id>/`)
- Complete event information
- Stack traces and technical details
- Context data and user information
- Related events

#### 4. Analytics (`/system-events/analytics/`)
- Daily event summaries
- Trend analysis
- Event source breakdowns
- Performance metrics

### Export Functionality
- CSV export from event list
- Filtered exports based on search criteria
- Includes all event metadata

## Integration Points

### Email Integration with Existing System
The Event Viewer automatically integrates with your existing email configuration by using the `ERROR_ALERTS_EMAIL_ADDRESS` from your `.env` file:

```bash
# In .env file
ERROR_ALERTS_EMAIL_ADDRESS=admin@yourcouncil.gov.uk
```

This ensures consistency with existing error alerting and requires no additional email configuration. The Event Viewer will automatically use this address for:
- Threshold violation alerts
- Pattern detection notifications  
- Daily/weekly health reports
- Anomaly detection alerts

### Middleware Integration (`council_finance/middleware/error_alerting.py`)
Enhanced existing error middleware to create SystemEvent records without disrupting email alerts:

```python
def process_exception(self, request, exception):
    # Existing email alert logic (preserved)
    self._send_error_email(request, exception)
    
    # New: Create SystemEvent record
    self._create_system_event(request, exception)
    
    return None  # Don't interfere with Django's error handling
```

### Database Indexes
Optimized for performance with strategic indexes:
- `timestamp` field for chronological queries
- `source` field for filtering by event source
- `level` field for severity filtering
- `fingerprint` field for deduplication

## Performance Considerations

### Processing Times
- **God Mode Log**: 751 events in 85.7 seconds
- **Response Log**: HTML filtering prevents thousands of junk events
- **Batch Processing**: Efficient bulk operations with progress tracking

### Storage Management
- Events include full context but limit message length (500-2000 chars)
- JSON fields for flexible metadata storage
- Fingerprinting reduces duplicate storage

### Query Optimization
- Proper database indexing for common queries
- Pagination for large result sets
- Efficient filtering and search operations

## Configuration

### Basic Setup (Uses Existing Email Configuration)
The Event Viewer works out-of-the-box with your existing `.env` configuration:

```bash
# In .env file (already configured for your project)
ERROR_ALERTS_EMAIL_ADDRESS=admin@yourcouncil.gov.uk
```

### Advanced Configuration (Optional)
For custom alert thresholds and settings, add to your Django `settings.py`:

```python
# Optional: Customize Event Viewer settings
EVENT_VIEWER_SETTINGS = {
    # Email configuration (defaults to ERROR_ALERTS_EMAIL_ADDRESS from .env)
    'ENABLE_EMAIL_ALERTS': True,
    
    # Custom alert thresholds (adjust for your environment)
    'ALERT_THRESHOLDS': {
        'critical_errors_per_hour': 3,    # Lower threshold for faster alerts
        'total_errors_per_hour': 15,      # Adjust based on normal error volume
        'api_errors_per_hour': 8,         # API-specific monitoring
        'security_events_per_hour': 1,    # Security events are high priority
        'test_failures_per_day': 1,       # Test failures should be rare
    },
    
    # Data retention (adjust based on storage needs)
    'RETENTION_POLICIES': {
        'default_retention_days': 90,
        'critical_events_retention_days': 365,
    },
    
    # Analytics configuration
    'ANALYTICS': {
        'enable_health_scoring': True,
        'daily_summary_time': '06:00',    # When to generate daily summaries
    }
}
```

### Setting Up Automated Monitoring
Add to your cron jobs for automated monitoring:

```bash
# Check alert thresholds every 15 minutes
*/15 * * * * /path/to/python manage.py check_alerts

# Send daily health report at 6 AM
0 6 * * * /path/to/python manage.py check_alerts --health-report

# Create missing daily summaries (run once daily)
0 1 * * * /path/to/python manage.py check_alerts --create-summaries
```

## Common Issues & Solutions

### Issue: "TemplateDoesNotExist at /system-events/"
**Solution**: Ensure all templates exist in `event_viewer/templates/event_viewer/`:
- `dashboard.html`
- `event_list.html` 
- `event_detail.html`
- `analytics.html`

### Issue: "No events showing despite log files"
**Solution**: 
1. Check superuser access
2. Run log parsing: `python manage.py parse_logs --execute`
3. Verify log file formats match parser expectations

### Issue: "HTML junk events from response.log"
**Solution**: 
- Clear corrupted events: `SystemEvent.objects.filter(source='api').delete()`
- ResponseLogParser now includes HTML filtering
- Ensure response.log contains actual log entries, not curl output

### Issue: "Unicode errors in command output"
**Solution**: 
- parse_logs command now uses ASCII-safe output
- No emoji characters in command line output
- Windows-compatible encoding

## Development Guidelines

### Adding New Event Sources
1. Define new source in `EVENT_SOURCES` choices
2. Update middleware or create new capture points
3. Add appropriate categorization
4. Test with various error conditions

### Creating New Log Parsers
1. Extend `BaseLogParser` class
2. Implement `parse_line()` method
3. Add to `LogParsingService.parsers` dictionary
4. Include appropriate filtering and validation

### Extending Analytics
1. Add new summary fields to `EventSummary` model
2. Update analytics view and template
3. Consider performance impact of new calculations

## Testing & Validation

### Manual Testing Checklist
- [ ] Dashboard loads and shows recent events
- [ ] Event list is filterable and paginated
- [ ] Event detail shows complete information
- [ ] Log parsing imports correct number of events
- [ ] HTML content is filtered from response logs
- [ ] Superuser access control works
- [ ] Export functionality produces valid CSV

### Automated Testing
Consider adding tests for:
- Log parser accuracy
- Event deduplication
- Template rendering
- Access control
- API endpoints

## Future Enhancements

### Phase 3: Analytics & Alerting (Next)
- Threshold-based email alerts
- Trend detection and anomaly identification
- Advanced correlation between events
- Weekly health reports

### Phase 4: Real-time Monitoring
- WebSocket-based live updates
- File watchers for automatic log processing
- Real-time dashboard notifications

### Phase 5: Integration & Extensibility
- Slack/Teams webhook integration
- REST API for external monitoring
- Plugin architecture for custom parsers

## Troubleshooting

### Performance Issues
- Check database indexes: `python manage.py dbshell` then `\d+ event_viewer_systemevent`
- Monitor query performance in Django debug toolbar
- Consider event retention policies for large datasets

### Missing Events
- Verify middleware is properly configured
- Check log file permissions and locations
- Ensure parsers match actual log file formats
- Test with verbose parsing: `python manage.py parse_logs --verbose`

### Access Issues
- Confirm user has superuser status
- Check URL configuration includes event_viewer.urls
- Verify Django admin is not conflicting with /admin/ paths

---

**CRITICAL NOTES:**
- Always use `--execute` flag to actually import events (default is dry-run)
- Clear junk events before re-parsing: `python manage.py parse_logs --clear-first`
- Monitor database growth - consider retention policies for production
- This system complements ActivityLog - never replace existing logging