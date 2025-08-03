"""
Initialize sample monitoring data for testing the AI monitoring dashboard.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from council_finance.models import (
    AIUsageTrend, LoadBalancerConfig, CostForecast
)


class Command(BaseCommand):
    help = 'Initialize sample monitoring data for AI dashboard testing'

    def handle(self, *args, **options):
        self.stdout.write('Initializing monitoring data...')
        
        # Create hourly usage trends for past 7 days
        self.create_usage_trends()
        
        # Create load balancer config
        self.create_load_balancer_config()
        
        # Create cost forecasts
        self.create_cost_forecasts()
        
        self.stdout.write(self.style.SUCCESS('Monitoring data initialized successfully!'))
    
    def create_usage_trends(self):
        """Create sample usage trend data."""
        now = timezone.now()
        
        for days_ago in range(7):
            date = now.date() - timedelta(days=days_ago)
            
            for hour in range(24):
                # Simulate realistic traffic patterns
                base_requests = 50
                if 9 <= hour <= 17:  # Business hours
                    base_requests = 150
                elif 18 <= hour <= 22:  # Evening
                    base_requests = 100
                elif hour < 6:  # Night
                    base_requests = 20
                
                # Add some variation
                import random
                requests = base_requests + random.randint(-20, 20)
                
                trend, created = AIUsageTrend.objects.get_or_create(
                    date=date,
                    hour=hour,
                    defaults={
                        'request_count': requests,
                        'unique_councils': max(1, requests // 5),
                        'avg_response_time': 2.5 + random.random(),
                        'success_rate': 95 + random.random() * 5,
                        'total_cost': Decimal(str(requests * 0.002)),
                        'avg_cost_per_request': Decimal('0.002'),
                    }
                )
                
                if created:
                    self.stdout.write(f'Created trend for {date} {hour:02d}:00')
    
    def create_load_balancer_config(self):
        """Create default load balancer configuration."""
        config, created = LoadBalancerConfig.objects.get_or_create(
            name='Production Load Balancer',
            defaults={
                'is_active': True,
                'requests_per_second_threshold': 10,
                'cpu_threshold': 80.0,
                'memory_threshold': 85.0,
                'min_instances': 1,
                'max_instances': 5,
                'scale_up_cooldown': 300,
                'scale_down_cooldown': 600,
                'current_instances': 1,
                'avg_request_time': 2.5,
                'requests_per_second': 3.5,
            }
        )
        
        if created:
            self.stdout.write('Created load balancer configuration')
    
    def create_cost_forecasts(self):
        """Create sample cost forecasts."""
        now = timezone.now()
        
        # Daily forecast
        daily_forecast, created = CostForecast.objects.get_or_create(
            period_type='daily',
            period_start=now.date(),
            defaults={
                'period_end': now.date(),
                'forecasted_cost': Decimal('12.50'),
                'forecasted_requests': 2500,
                'forecast_confidence': 85.0,
                'budget_limit': Decimal('15.00'),
            }
        )
        
        if created:
            self.stdout.write('Created daily cost forecast')
        
        # Weekly forecast
        week_start = now.date() - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_forecast, created = CostForecast.objects.get_or_create(
            period_type='weekly',
            period_start=week_start,
            defaults={
                'period_end': week_end,
                'forecasted_cost': Decimal('87.50'),
                'forecasted_requests': 17500,
                'forecast_confidence': 80.0,
                'budget_limit': Decimal('100.00'),
            }
        )
        
        if created:
            self.stdout.write('Created weekly cost forecast')
        
        # Monthly forecast
        month_start = now.date().replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(day=31)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        
        monthly_forecast, created = CostForecast.objects.get_or_create(
            period_type='monthly',
            period_start=month_start,
            defaults={
                'period_end': month_end,
                'forecasted_cost': Decimal('375.00'),
                'forecasted_requests': 75000,
                'forecast_confidence': 75.0,
                'budget_limit': Decimal('500.00'),
            }
        )
        
        if created:
            self.stdout.write('Created monthly cost forecast')
            
        # Generate optimization tips for all forecasts
        for forecast in [daily_forecast, weekly_forecast, monthly_forecast]:
            forecast.generate_optimization_tips()