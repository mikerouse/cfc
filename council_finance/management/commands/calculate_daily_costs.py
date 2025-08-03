"""
Django management command to calculate and store daily AI cost summaries.

This command processes AI usage logs and creates daily summary records
for cost tracking, budgeting, and analytics reporting.

Usage:
    python manage.py calculate_daily_costs                    # Yesterday's data
    python manage.py calculate_daily_costs --date=2025-01-15  # Specific date
    python manage.py calculate_daily_costs --days=7           # Last 7 days
    python manage.py calculate_daily_costs --all              # All missing dates
"""

import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q

from council_finance.models import AIUsageLog, DailyCostSummary, PerformanceAlert

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate and store daily AI cost summaries for analytics and budgeting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to process (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to process (backwards from today/specified date)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all dates that have usage logs but no daily summary'
        )
        parser.add_argument(
            '--budget-alert',
            type=float,
            help='Daily budget threshold for creating alerts (in GBP)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculate summaries even if they already exist'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        self.verbosity = options['verbosity']
        budget_threshold = options.get('budget_alert')
        force = options['force']
        
        if options['all']:
            self.process_all_missing_dates(force, budget_threshold)
        else:
            # Determine date range
            if options['date']:
                try:
                    end_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                except ValueError:
                    raise CommandError("Invalid date format. Use YYYY-MM-DD")
            else:
                end_date = timezone.now().date() - timedelta(days=1)  # Yesterday
            
            days = options['days']
            start_date = end_date - timedelta(days=days - 1)
            
            self.process_date_range(start_date, end_date, force, budget_threshold)

    def process_all_missing_dates(self, force=False, budget_threshold=None):
        """Process all dates that have usage logs but no daily summary."""
        self.stdout.write("🔍 Finding dates with missing daily summaries...")
        
        # Get all dates that have usage logs
        usage_dates = AIUsageLog.objects.extra(
            select={'date': 'date(created_at)'}
        ).values('date').distinct().order_by('date')
        
        # Get dates that already have summaries
        if not force:
            existing_dates = set(
                DailyCostSummary.objects.values_list('date', flat=True)
            )
        else:
            existing_dates = set()
        
        # Find missing dates
        missing_dates = []
        for record in usage_dates:
            date = record['date']
            if date not in existing_dates:
                missing_dates.append(date)
        
        if not missing_dates:
            self.stdout.write("✅ No missing daily summaries found")
            return
        
        self.stdout.write(f"📊 Processing {len(missing_dates)} missing dates...")
        
        for date in missing_dates:
            self.calculate_daily_summary(date, force, budget_threshold)

    def process_date_range(self, start_date, end_date, force=False, budget_threshold=None):
        """Process a specific date range."""
        self.stdout.write(f"📊 Processing daily summaries from {start_date} to {end_date}...")
        
        current_date = start_date
        while current_date <= end_date:
            self.calculate_daily_summary(current_date, force, budget_threshold)
            current_date += timedelta(days=1)

    def calculate_daily_summary(self, date, force=False, budget_threshold=None):
        """Calculate daily summary for a specific date."""
        try:
            # Check if summary already exists
            if not force and DailyCostSummary.objects.filter(date=date).exists():
                if self.verbosity >= 2:
                    self.stdout.write(f"  ⏭️ Skipping {date} (already exists)")
                return
            
            # Calculate summary for the date
            summary = DailyCostSummary.calculate_for_date(date)
            
            if summary:
                if self.verbosity >= 1:
                    self.stdout.write(
                        f"  ✅ {date}: {summary.total_requests} requests, "
                        f"£{summary.total_estimated_cost:.4f}, "
                        f"{summary.total_factoids_generated} factoids"
                    )
                
                # Check budget threshold
                if budget_threshold and summary.total_estimated_cost > budget_threshold:
                    self.create_budget_alert(summary, budget_threshold)
                
                # Check for performance issues
                self.check_performance_metrics(summary)
                
            else:
                if self.verbosity >= 2:
                    self.stdout.write(f"  ⏭️ No usage data for {date}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ Error processing {date}: {e}")
            )
            logger.error(f"Daily summary calculation failed for {date}: {e}")

    def create_budget_alert(self, summary, threshold):
        """Create a budget threshold alert."""
        try:
            # Check if we already have a recent budget alert to avoid spam
            recent_budget_alerts = PerformanceAlert.objects.filter(
                alert_type='budget_threshold',
                created_at__gte=timezone.now() - timedelta(days=1),
                is_active=True
            ).count()
            
            if recent_budget_alerts == 0:  # Only create if no recent alerts
                PerformanceAlert.objects.create(
                    alert_type='budget_threshold',
                    severity='high',
                    title=f'Daily Budget Threshold Exceeded',
                    description=f'Daily cost (£{summary.total_estimated_cost:.4f}) exceeded threshold (£{threshold:.4f}) on {summary.date}',
                    recommendation='Review usage patterns and consider implementing stricter rate limiting',
                    metric_value=float(summary.total_estimated_cost),
                    threshold_value=threshold
                )
                
                if self.verbosity >= 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️ Budget alert created for {summary.date} "
                            f"(£{summary.total_estimated_cost:.4f} > £{threshold:.4f})"
                        )
                    )
                
        except Exception as e:
            logger.error(f"Failed to create budget alert: {e}")

    def check_performance_metrics(self, summary):
        """Check performance metrics and create alerts if needed."""
        try:
            # High failure rate check
            if summary.total_requests > 0:
                failure_rate = (summary.failed_requests / summary.total_requests) * 100
                
                if failure_rate > 20:  # 20% failure rate threshold
                    PerformanceAlert.objects.create(
                        alert_type='high_failure_rate',
                        severity='high',
                        title=f'High Failure Rate Detected',
                        description=f'Failure rate was {failure_rate:.1f}% on {summary.date} ({summary.failed_requests}/{summary.total_requests} requests)',
                        recommendation='Check OpenAI API status and error patterns. Consider implementing circuit breaker.',
                        metric_value=failure_rate,
                        threshold_value=20.0
                    )
                    
                    if self.verbosity >= 1:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️ High failure rate alert created for {summary.date} ({failure_rate:.1f}%)"
                            )
                        )
            
            # Slow response time check
            if summary.avg_processing_time and summary.avg_processing_time > 15:  # 15 second threshold
                PerformanceAlert.objects.create(
                    alert_type='slow_response',
                    severity='medium',
                    title=f'Slow Average Response Time',
                    description=f'Average response time was {summary.avg_processing_time:.1f}s on {summary.date}',
                    recommendation='Check OpenAI API performance and consider cache warming for popular councils',
                    metric_value=summary.avg_processing_time,
                    threshold_value=15.0
                )
                
                if self.verbosity >= 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️ Slow response alert created for {summary.date} ({summary.avg_processing_time:.1f}s avg)"
                        )
                    )
            
            # Low cache efficiency check
            if summary.total_requests > 10:  # Only check if we have sufficient data
                cache_hit_rate = (summary.cache_hits / summary.total_requests) * 100
                
                if cache_hit_rate < 20:  # 20% cache hit rate threshold
                    PerformanceAlert.objects.create(
                        alert_type='cache_inefficiency',
                        severity='low',
                        title=f'Low Cache Hit Rate',
                        description=f'Cache hit rate was only {cache_hit_rate:.1f}% on {summary.date}',
                        recommendation='Implement proactive cache warming for frequently accessed councils',
                        metric_value=cache_hit_rate,
                        threshold_value=20.0
                    )
                    
                    if self.verbosity >= 2:
                        self.stdout.write(
                            f"    ℹ️ Low cache hit rate: {cache_hit_rate:.1f}%"
                        )
                        
        except Exception as e:
            logger.error(f"Failed to check performance metrics for {summary.date}: {e}")

    def handle_keyboard_interrupt(self):
        """Handle Ctrl+C gracefully."""
        self.stdout.write("\n⏹️ Interrupted by user")
        return