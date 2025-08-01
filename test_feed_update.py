#!/usr/bin/env python
"""
Test script to verify the feed update system is working properly.
Creates/updates financial data and checks if feed updates are generated.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append('.')
django.setup()

from council_finance.models import Council, FinancialFigure, DataField, FinancialYear, FeedUpdate
from django.contrib.auth import get_user_model

def test_feed_updates():
    print("=== Testing Feed Update System ===")
    
    # Get Aberdeen council 
    council = Council.objects.filter(name__icontains='Aberdeen').first()
    if not council:
        print('❌ No Aberdeen council found')
        return False

    print(f'✅ Found council: {council.name}')

    # Get or create a reserves field
    field, created = DataField.objects.get_or_create(
        slug='usable-reserves',
        defaults={
            'name': 'Usable Reserves',
            'category': 'financial',
            'description': 'Total usable reserves available to the council'
        }
    )
    print(f'✅ Using field: {field.name} (created: {created})')

    # Get latest financial year
    year = FinancialYear.objects.filter(is_projected=False).order_by('-end_date').first()
    if not year:
        print('❌ No financial year found')
        return False

    print(f'✅ Using year: {year.label}')

    # Get admin user for attribution
    User = get_user_model()
    admin_user = User.objects.filter(username=os.getenv('ADMIN_USER')).first()
    if not admin_user:
        print('⚠️  No admin user found - proceeding without attribution')

    # Count existing feed updates before our test
    initial_feed_count = FeedUpdate.objects.count()
    print(f'📊 Initial feed updates count: {initial_feed_count}')

    # Create or update a financial figure with realistic reserves data
    figure, created = FinancialFigure.objects.get_or_create(
        council=council,
        field=field,
        year=year,
        defaults={
            'value': '15600000',  # £15.6M reserves
            'source': 'Test data for feed system'
        }
    )

    if not created and figure.value != '15600000':
        print(f'🔄 Updating existing figure from {figure.value} to 15600000')
        old_value = figure.value
        figure.value = '15600000'
        if admin_user:
            figure._author = admin_user  # Set author for signal
        figure.save()
        print(f'✅ Updated reserves figure from £{old_value} to £15,600,000')
    else:
        print(f'➕ Created new reserves figure: £15,600,000')
        # For new figures, set author and trigger signal manually if needed
        if admin_user:
            figure._author = admin_user
        figure.save()

    # Check if feed updates were created
    final_feed_count = FeedUpdate.objects.count()
    print(f'📊 Final feed updates count: {final_feed_count}')
    
    if final_feed_count > initial_feed_count:
        print(f'🎉 SUCCESS: {final_feed_count - initial_feed_count} new feed update(s) created!')
        
        # Show the latest feed updates
        latest_updates = FeedUpdate.objects.order_by('-created_at')[:3]
        print('\n📝 Latest Feed Updates:')
        for update in latest_updates:
            print(f'  - {update.title}: {update.message}')
            print(f'    Type: {update.update_type}, Created: {update.created_at}')
            
        return True
    else:
        print('❌ FAILED: No new feed updates were created')
        print('   This suggests the signal handlers may not be working properly')
        return False

if __name__ == '__main__':
    success = test_feed_updates()
    sys.exit(0 if success else 1)