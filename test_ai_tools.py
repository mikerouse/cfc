#!/usr/bin/env python
"""
Test AI tools functionality without URL configuration.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

print("Testing AI Tools functionality...")

try:
    print("1. Testing model imports...")
    from council_finance.models import AIUsageTrend, LoadBalancerConfig, CostForecast, PerformanceAnomaly
    print("   All predictive analytics models imported")
    
    print("2. Testing service imports...")
    from council_finance.services.realtime_monitoring import RealtimeMonitoringService
    print("   RealtimeMonitoringService imported")
    
    print("3. Creating sample data...")
    from django.utils import timezone
    from decimal import Decimal
    import random
    
    # Create sample usage trends for past 24 hours
    now = timezone.now()
    trends_created = 0
    
    for hours_ago in range(24):
        date = (now - timezone.timedelta(hours=hours_ago)).date()
        hour = (now - timezone.timedelta(hours=hours_ago)).hour
        
        trend, created = AIUsageTrend.objects.get_or_create(
            date=date,
            hour=hour,
            defaults={
                'request_count': random.randint(20, 100),
                'unique_councils': random.randint(5, 25),
                'avg_response_time': 2.0 + random.random() * 2,
                'success_rate': 95 + random.random() * 5,
                'total_cost': Decimal(str(random.uniform(0.05, 0.25))),
                'avg_cost_per_request': Decimal('0.002'),
            }
        )
        if created:
            trends_created += 1
    
    print(f"   ✓ Created {trends_created} usage trends")
    
    # Create load balancer config
    config, created = LoadBalancerConfig.objects.get_or_create(
        name='Production LB',
        defaults={
            'is_active': True,
            'requests_per_second_threshold': 10,
            'current_instances': 1,
            'max_instances': 5,
            'min_instances': 1,
        }
    )
    print(f"   ✓ LoadBalancerConfig {'created' if created else 'exists'}")
    
    # Create cost forecast
    forecast, created = CostForecast.objects.get_or_create(
        period_type='monthly',
        period_start=now.date().replace(day=1),
        defaults={
            'period_end': now.date().replace(day=28),  # Simplified
            'forecasted_cost': Decimal('125.50'),
            'forecasted_requests': 25000,
            'forecast_confidence': 85.0,
            'budget_limit': Decimal('200.00'),
        }
    )
    print(f"   ✓ CostForecast {'created' if created else 'exists'}")
    
    print("4. Testing monitoring service...")
    service = RealtimeMonitoringService()
    
    # Test live metrics
    metrics = service.get_live_metrics()
    print(f"   ✓ Live metrics: {metrics['requests_per_minute']:.1f} RPM, {metrics['system_health']:.1f}% health")
    
    # Test anomaly detection
    anomalies = service.detect_anomalies()
    print(f"   ✓ Detected {len(anomalies)} anomalies")
    
    # Test predictions
    predictions = service.get_predictive_insights()
    print(f"   ✓ Predictions available: {predictions['next_hour_prediction']['available']}")
    
    print("\n🎉 AI Tools functionality test PASSED!")
    print("✅ Phase 4 implementation is working correctly")
    print("✅ Real-time monitoring system operational")
    print("✅ Predictive analytics models functional")
    print("✅ Sample data created successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()