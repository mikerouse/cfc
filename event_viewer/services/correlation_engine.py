"""
Event Correlation Engine

Identifies relationships between events to provide better context for debugging
and to detect patterns that might indicate larger system issues.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Count, F
from django.contrib.auth import get_user_model
from ..models import SystemEvent

User = get_user_model()


class EventCorrelationEngine:
    """
    Analyzes events to find correlations and patterns that provide
    better context for system monitoring and debugging.
    """
    
    def __init__(self):
        self.correlation_window_minutes = 15  # Time window for correlating events
        self.max_related_events = 20  # Maximum number of related events to return
    
    def find_related_events(self, event):
        """
        Find events related to the given event based on various correlation factors.
        
        Returns a dictionary with different types of related events.
        """
        related = {
            'temporal': self._find_temporal_correlations(event),
            'user_related': self._find_user_correlations(event),
            'similar_errors': self._find_similar_errors(event),
            'cascading': self._find_cascading_events(event),
            'source_related': self._find_source_correlations(event),
        }
        
        # Remove empty categories and limit results
        return {k: v[:self.max_related_events] for k, v in related.items() if v}
    
    def _find_temporal_correlations(self, event):
        """Find events that occurred around the same time."""
        window_start = event.timestamp - timedelta(minutes=self.correlation_window_minutes)
        window_end = event.timestamp + timedelta(minutes=self.correlation_window_minutes)
        
        return list(SystemEvent.objects.filter(
            timestamp__range=(window_start, window_end)
        ).exclude(
            id=event.id
        ).order_by('timestamp')[:10])
    
    def _find_user_correlations(self, event):
        """Find events related to the same user."""
        if not event.user:
            return []
        
        # Look for events from the same user within the last hour
        one_hour_ago = event.timestamp - timedelta(hours=1)
        
        return list(SystemEvent.objects.filter(
            user=event.user,
            timestamp__gte=one_hour_ago
        ).exclude(
            id=event.id
        ).order_by('-timestamp')[:10])
    
    def _find_similar_errors(self, event):
        """Find events with similar fingerprints or error messages."""
        similar_events = []
        
        # Find events with the same fingerprint (but different occurrence)
        if event.fingerprint:
            similar_events.extend(SystemEvent.objects.filter(
                fingerprint=event.fingerprint
            ).exclude(
                id=event.id
            ).order_by('-timestamp')[:5])
        
        # Find events with similar titles or messages
        if event.title:
            # Extract key words from the title for similarity matching
            title_words = event.title.lower().split()
            if len(title_words) >= 2:
                key_words = [word for word in title_words if len(word) > 3][:3]
                if key_words:
                    q_objects = Q()
                    for word in key_words:
                        q_objects |= Q(title__icontains=word) | Q(message__icontains=word)
                    
                    similar_events.extend(SystemEvent.objects.filter(
                        q_objects,
                        level=event.level,
                        category=event.category
                    ).exclude(
                        id=event.id
                    ).exclude(
                        id__in=[e.id for e in similar_events]  # Avoid duplicates
                    ).order_by('-timestamp')[:5])
        
        return similar_events[:10]
    
    def _find_cascading_events(self, event):
        """Find events that might be caused by this event or vice versa."""
        cascading = []
        
        # Look for events shortly after this one that might be consequences
        if event.level in ['error', 'critical']:
            five_minutes_later = event.timestamp + timedelta(minutes=5)
            
            cascading.extend(SystemEvent.objects.filter(
                timestamp__range=(event.timestamp, five_minutes_later),
                level__in=['error', 'warning']
            ).exclude(
                id=event.id
            ).order_by('timestamp')[:5])
        
        # Look for events shortly before that might be causes
        five_minutes_before = event.timestamp - timedelta(minutes=5)
        
        cascading.extend(SystemEvent.objects.filter(
            timestamp__range=(five_minutes_before, event.timestamp),
            level__in=['error', 'critical']
        ).exclude(
            id=event.id
        ).exclude(
            id__in=[e.id for e in cascading]  # Avoid duplicates
        ).order_by('-timestamp')[:5])
        
        return cascading
    
    def _find_source_correlations(self, event):
        """Find events from the same source around the same time."""
        one_hour_ago = event.timestamp - timedelta(hours=1)
        one_hour_later = event.timestamp + timedelta(hours=1)
        
        return list(SystemEvent.objects.filter(
            source=event.source,
            timestamp__range=(one_hour_ago, one_hour_later)
        ).exclude(
            id=event.id
        ).order_by('-timestamp')[:8])
    
    def detect_error_patterns(self, hours_back=24):
        """
        Detect patterns in errors that might indicate systemic issues.
        
        Returns a list of detected patterns with descriptions and affected events.
        """
        cutoff_time = timezone.now() - timedelta(hours=hours_back)
        
        patterns = []
        
        # Pattern 1: High frequency of similar errors
        patterns.extend(self._detect_high_frequency_errors(cutoff_time))
        
        # Pattern 2: Cascading failures
        patterns.extend(self._detect_cascading_failures(cutoff_time))
        
        # Pattern 3: User-specific error spikes
        patterns.extend(self._detect_user_error_spikes(cutoff_time))
        
        # Pattern 4: Source-specific issues
        patterns.extend(self._detect_source_issues(cutoff_time))
        
        return patterns
    
    def _detect_high_frequency_errors(self, cutoff_time):
        """Detect errors that are occurring at unusually high frequency."""
        patterns = []
        
        # Group by fingerprint and count occurrences
        frequent_errors = SystemEvent.objects.filter(
            timestamp__gte=cutoff_time,
            level__in=['error', 'critical']
        ).values(
            'fingerprint', 'title'
        ).annotate(
            count=Count('id')
        ).filter(
            count__gte=5  # 5 or more similar errors
        ).order_by('-count')
        
        for error_group in frequent_errors:
            events = SystemEvent.objects.filter(
                fingerprint=error_group['fingerprint'],
                timestamp__gte=cutoff_time
            ).order_by('-timestamp')[:10]
            
            patterns.append({
                'type': 'high_frequency_error',
                'title': f"High frequency error: {error_group['title']}",
                'description': f"Error occurred {error_group['count']} times in the last 24 hours",
                'severity': 'high' if error_group['count'] >= 10 else 'medium',
                'events': list(events),
                'count': error_group['count']
            })
        
        return patterns
    
    def _detect_cascading_failures(self, cutoff_time):
        """Detect sequences of errors that might indicate cascading failures."""
        patterns = []
        
        # Find critical errors followed by multiple other errors
        critical_events = SystemEvent.objects.filter(
            timestamp__gte=cutoff_time,
            level='critical'
        ).order_by('-timestamp')
        
        for critical_event in critical_events:
            # Look for errors in the 10 minutes following this critical error
            following_errors = SystemEvent.objects.filter(
                timestamp__range=(
                    critical_event.timestamp,
                    critical_event.timestamp + timedelta(minutes=10)
                ),
                level__in=['error', 'warning']
            ).exclude(id=critical_event.id)
            
            if following_errors.count() >= 3:  # 3 or more following errors
                patterns.append({
                    'type': 'cascading_failure',
                    'title': f"Cascading failure from: {critical_event.title}",
                    'description': f"Critical error led to {following_errors.count()} subsequent errors",
                    'severity': 'high',
                    'trigger_event': critical_event,
                    'following_events': list(following_errors[:10]),
                    'count': following_errors.count()
                })
        
        return patterns
    
    def _detect_user_error_spikes(self, cutoff_time):
        """Detect users experiencing unusually high error rates."""
        patterns = []
        
        user_error_counts = SystemEvent.objects.filter(
            timestamp__gte=cutoff_time,
            level__in=['error', 'critical'],
            user__isnull=False
        ).values(
            'user__username', 'user__id'
        ).annotate(
            error_count=Count('id')
        ).filter(
            error_count__gte=5  # 5 or more errors for one user
        ).order_by('-error_count')
        
        for user_errors in user_error_counts:
            user_events = SystemEvent.objects.filter(
                user__id=user_errors['user__id'],
                timestamp__gte=cutoff_time,
                level__in=['error', 'critical']
            ).order_by('-timestamp')[:10]
            
            patterns.append({
                'type': 'user_error_spike',
                'title': f"High error rate for user: {user_errors['user__username']}",
                'description': f"User experienced {user_errors['error_count']} errors in the last 24 hours",
                'severity': 'medium' if user_errors['error_count'] < 10 else 'high',
                'events': list(user_events),
                'user_id': user_errors['user__id'],
                'username': user_errors['user__username'],
                'count': user_errors['error_count']
            })
        
        return patterns
    
    def _detect_source_issues(self, cutoff_time):
        """Detect issues with specific event sources."""
        patterns = []
        
        source_error_counts = SystemEvent.objects.filter(
            timestamp__gte=cutoff_time,
            level__in=['error', 'critical']
        ).values(
            'source'
        ).annotate(
            error_count=Count('id')
        ).filter(
            error_count__gte=5
        ).order_by('-error_count')
        
        for source_errors in source_error_counts:
            source_events = SystemEvent.objects.filter(
                source=source_errors['source'],
                timestamp__gte=cutoff_time,
                level__in=['error', 'critical']
            ).order_by('-timestamp')[:10]
            
            patterns.append({
                'type': 'source_issue',
                'title': f"Issues with {source_errors['source']} system",
                'description': f"Source generated {source_errors['error_count']} errors in the last 24 hours",
                'severity': 'medium' if source_errors['error_count'] < 15 else 'high',
                'events': list(source_events),
                'source': source_errors['source'],
                'count': source_errors['error_count']
            })
        
        return patterns


# Global correlation engine instance
correlation_engine = EventCorrelationEngine()