#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

print("Testing AI Tools...")

try:
    from council_finance.models import AIUsageTrend, LoadBalancerConfig
    from council_finance.services.realtime_monitoring import RealtimeMonitoringService
    from django.utils import timezone
    from decimal import Decimal
    
    print("Models imported successfully")
    
    # Create test data
    trend, created = AIUsageTrend.objects.get_or_create(
        date=timezone.now().date(),
        hour=timezone.now().hour,
        defaults={
            'request_count': 50,
            'unique_councils': 10,
            'avg_response_time': 2.5,
            'success_rate': 98.5,
            'total_cost': Decimal('0.10'),
        }
    )
    
    config, created = LoadBalancerConfig.objects.get_or_create(
        name='Test Config',
        defaults={'is_active': True, 'current_instances': 1}
    )
    
    service = RealtimeMonitoringService()
    metrics = service.get_live_metrics()
    
    print(f"SUCCESS: System health: {metrics['system_health']}%")
    print("AI Tools Phase 4 implementation is working!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()