"""
AI Tools Hub View

Provides unified navigation and overview for all AI-powered tools
in the council finance system.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from decimal import Decimal

from council_finance.models import (
    AIUsageLog, Council, FactoidInstance,
    DailyCostSummary
)


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def ai_tools_hub(request):
    """Main hub page for AI tools navigation."""
    
    # Calculate quick stats
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Total factoids generated
    total_factoids = FactoidInstance.objects.count()
    
    # Councils analyzed (councils with factoids)
    councils_analyzed = FactoidInstance.objects.values('council').distinct().count()
    
    # Success rate (last 7 days)
    week_ago = now - timedelta(days=7)
    recent_logs = AIUsageLog.objects.filter(created_at__gte=week_ago)
    total_requests = recent_logs.count()
    successful_requests = recent_logs.filter(success=True).count()
    
    if total_requests > 0:
        success_rate = (successful_requests / total_requests) * 100
    else:
        success_rate = 100.0
    
    # Monthly cost
    monthly_costs = DailyCostSummary.objects.filter(
        date__gte=month_start.date()
    ).aggregate(total=Sum('total_estimated_cost'))
    
    monthly_cost = monthly_costs['total'] or Decimal('0')
    
    context = {
        'page_title': 'AI Tools Hub',
        'stats': {
            'total_factoids': total_factoids,
            'councils_analyzed': councils_analyzed,
            'success_rate': round(success_rate, 1),
            'monthly_cost': float(monthly_cost),
        }
    }
    
    return render(request, 'council_finance/ai_tools/hub.html', context)