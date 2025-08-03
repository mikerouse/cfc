"""
Django management command to build optimized sitewide data summaries.

This command processes financial data from all councils and creates
efficient aggregated summaries for site-wide factoid generation.

Usage:
    python manage.py build_sitewide_summaries                    # Today's summaries
    python manage.py build_sitewide_summaries --date=2025-01-15  # Specific date
    python manage.py build_sitewide_summaries --rebuild          # Rebuild existing
    python manage.py build_sitewide_summaries --all-years        # All years with data
"""

import logging
import statistics
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg, Min, Max, StdDev
from django.db import transaction

from council_finance.models import (
    Council, DataField, FinancialYear, FinancialFigure,
    SitewideDataSummary, SitewideDataChangeLog
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build optimized sitewide data summaries for efficient factoid generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to process (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild summaries even if they already exist'
        )
        parser.add_argument(
            '--all-years',
            action='store_true',
            help='Process all years with financial data'
        )
        parser.add_argument(
            '--fields',
            type=str,
            help='Comma-separated list of field slugs to process (default: comparison fields)'
        )
        parser.add_argument(
            '--min-councils',
            type=int,
            default=5,
            help='Minimum number of councils required to create a summary'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        self.verbosity = options['verbosity']
        self.rebuild = options['rebuild']
        
        # Determine target date
        if options['date']:
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError("Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = timezone.now().date()
        
        # Determine fields to process
        if options['fields']:
            field_slugs = [slug.strip() for slug in options['fields'].split(',')]
        else:
            # Default comparison fields for site-wide analysis
            field_slugs = [
                'interest-paid',
                'total-debt',
                'current-liabilities',
                'long-term-liabilities',
                'business-rates-income',
                'council-tax-income',
                'reserves-and-balances',
                'employee-costs',
                'housing-benefit-payments'
            ]
        
        if options['all_years']:
            self.process_all_years(field_slugs, target_date, options['min_councils'])
        else:
            self.process_single_date(target_date, field_slugs, options['min_councils'])

    def process_all_years(self, field_slugs, target_date, min_councils):
        """Process all years with financial data."""
        self.stdout.write("Finding years with financial data...")
        
        # Get all years that have financial data
        years_with_data = FinancialYear.objects.filter(
            financialfigure__isnull=False
        ).distinct().order_by('-start_date')
        
        if not years_with_data.exists():
            self.stdout.write("No financial years with data found")
            return
        
        self.stdout.write(f"Processing {years_with_data.count()} years...")
        
        total_summaries = 0
        for year in years_with_data:
            year_summaries = self.process_year(target_date, year, field_slugs, min_councils)
            total_summaries += year_summaries
            
            if self.verbosity >= 1:
                self.stdout.write(f"  {year.label}: {year_summaries} summaries")
        
        self.stdout.write(
            self.style.SUCCESS(f"Processed {total_summaries} summaries across all years")
        )

    def process_single_date(self, target_date, field_slugs, min_councils):
        """Process summaries for a single date."""
        self.stdout.write(f"Building sitewide summaries for {target_date}...")
        
        # Get the latest year with substantial data
        latest_year = self.get_latest_year_with_data(min_councils)
        
        if not latest_year:
            self.stdout.write("No year with sufficient data found")
            return
        
        summaries_created = self.process_year(target_date, latest_year, field_slugs, min_councils)
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {summaries_created} summaries for {target_date}")
        )

    def process_year(self, target_date, year, field_slugs, min_councils):
        """Process summaries for a specific year."""
        summaries_created = 0
        
        for field_slug in field_slugs:
            try:
                # Get the field
                try:
                    field = DataField.objects.get(slug=field_slug)
                except DataField.DoesNotExist:
                    if self.verbosity >= 2:
                        self.stdout.write(f"  Field {field_slug} not found")
                    continue
                
                # Check if summary already exists
                if not self.rebuild:
                    existing = SitewideDataSummary.objects.filter(
                        date_calculated=target_date,
                        year=year,
                        field=field
                    ).exists()
                    
                    if existing:
                        if self.verbosity >= 2:
                            self.stdout.write(f"  Summary exists: {field.name} - {year.label}")
                        continue
                
                # Build summary for this field and year
                summary = self.build_field_summary(target_date, year, field, min_councils)
                
                if summary:
                    summaries_created += 1
                    if self.verbosity >= 2:
                        self.stdout.write(
                            f"  {field.name} - {year.label}: "
                            f"{summary.total_councils} councils, "
                            f"avg £{summary.average_value:.0f}M"
                        )
                else:
                    if self.verbosity >= 2:
                        self.stdout.write(
                            f"  Insufficient data: {field.name} - {year.label}"
                        )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Error processing {field_slug}: {e}")
                )
                logger.error(f"Summary building failed for {field_slug} in {year.label}: {e}")
        
        return summaries_created

    def build_field_summary(self, target_date, year, field, min_councils):
        """Build summary for a specific field and year."""
        try:
            # Get all financial figures for this field and year
            figures = FinancialFigure.objects.filter(
                field=field,
                year=year
            ).select_related(
                'council',
                'council__council_type',
                'council__council_nation'
            ).exclude(
                value__isnull=True
            )
            
            if figures.count() < min_councils:
                return None
            
            # Extract data for analysis
            council_data = []
            values = []
            
            for figure in figures:
                try:
                    value = float(figure.value)
                    council_data.append({
                        'council_name': figure.council.name,
                        'council_slug': figure.council.slug,
                        'council_type': figure.council.council_type.name if figure.council.council_type else 'Unknown',
                        'council_nation': figure.council.council_nation.name if figure.council.council_nation else 'Unknown',
                        'value': value
                    })
                    values.append(value)
                except (ValueError, TypeError):
                    continue
            
            if len(values) < min_councils:
                return None
            
            # Calculate statistics
            values.sort()
            avg_value = statistics.mean(values)
            median_value = statistics.median(values)
            min_value = min(values)
            max_value = max(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
            
            # Sort council data by value for top/bottom identification
            council_data.sort(key=lambda x: x['value'], reverse=True)
            
            # Get top and bottom performers
            top_5 = council_data[:5]
            bottom_5 = council_data[-5:] if len(council_data) >= 5 else council_data
            
            # Calculate type and nation averages
            type_averages = {}
            nation_averages = {}
            
            # Group by type
            type_groups = {}
            nation_groups = {}
            
            for item in council_data:
                council_type = item['council_type']
                nation = item['council_nation']
                
                if council_type not in type_groups:
                    type_groups[council_type] = []
                type_groups[council_type].append(item['value'])
                
                if nation not in nation_groups:
                    nation_groups[nation] = []
                nation_groups[nation].append(item['value'])
            
            # Calculate averages
            for type_name, type_values in type_groups.items():
                if len(type_values) >= 2:  # Only include if we have multiple councils
                    type_averages[type_name] = round(statistics.mean(type_values), 2)
            
            for nation_name, nation_values in nation_groups.items():
                if len(nation_values) >= 2:
                    nation_averages[nation_name] = round(statistics.mean(nation_values), 2)
            
            # Calculate data quality metrics
            total_councils = Council.objects.count()
            data_completeness = (len(council_data) / total_councils) * 100 if total_councils > 0 else 0
            
            # Detect outliers (values more than 2 standard deviations from mean)
            outlier_threshold = 2 * std_dev
            outlier_count = sum(1 for value in values if abs(value - avg_value) > outlier_threshold)
            
            # Calculate data hash for change detection
            data_hash = SitewideDataSummary.calculate_hash(council_data)
            
            # Create or update summary
            with transaction.atomic():
                summary, created = SitewideDataSummary.objects.update_or_create(
                    date_calculated=target_date,
                    year=year,
                    field=field,
                    defaults={
                        'total_councils': len(council_data),
                        'average_value': round(avg_value, 2),
                        'median_value': round(median_value, 2),
                        'min_value': round(min_value, 2),
                        'max_value': round(max_value, 2),
                        'std_deviation': round(std_dev, 2),
                        'top_5_councils': top_5,
                        'bottom_5_councils': bottom_5,
                        'type_averages': type_averages,
                        'nation_averages': nation_averages,
                        'data_completeness': round(data_completeness, 1),
                        'outlier_count': outlier_count,
                        'data_hash': data_hash
                    }
                )
                
                # Log the change if this is new or updated
                if created or (hasattr(summary, '_old_hash') and summary._old_hash != data_hash):
                    SitewideDataChangeLog.objects.create(
                        change_type='data_update',
                        affected_year=year,
                        affected_field=field,
                        old_hash=getattr(summary, '_old_hash', ''),
                        new_hash=data_hash,
                        change_magnitude=0.0  # Could calculate percentage change in future
                    )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to build summary for {field.slug} in {year.label}: {e}")
            raise

    def get_latest_year_with_data(self, min_councils):
        """Get the most recent year with sufficient data coverage."""
        # Find years with substantial council participation
        years_with_counts = FinancialFigure.objects.values('year').annotate(
            council_count=Count('council', distinct=True)
        ).filter(
            council_count__gte=min_councils
        ).order_by('-year__start_date')
        
        if not years_with_counts:
            return None
        
        year_id = years_with_counts[0]['year']
        return FinancialYear.objects.get(id=year_id)