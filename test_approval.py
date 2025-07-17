#!/usr/bin/env python
"""
Simple test script to verify the contribution approval functionality works.
Run this with: python manage.py shell < test_approval.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

from django.contrib.auth.models import User
from council_finance.models import Contribution, Council, DataField, FinancialYear
from django.test import RequestFactory
from council_finance.views import review_contribution

def test_approval():
    print("Testing contribution approval functionality...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'is_superuser': True, 'is_staff': True}
    )
    if created:
        print("Created test user")
    
    # Check if there are any pending contributions
    pending_contributions = Contribution.objects.filter(status='pending')
    print(f"Found {pending_contributions.count()} pending contributions")
    
    if pending_contributions.count() > 0:
        contribution = pending_contributions.first()
        print(f"Testing with contribution {contribution.id}: {contribution.council.name} - {contribution.field.name}")
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post(f'/contribute/{contribution.id}/approve/')
        request.user = user
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        
        # Test the view
        try:
            response = review_contribution(request, contribution.id, 'approve')
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content.decode()}")
            
            # Check if contribution was approved
            contribution.refresh_from_db()
            print(f"Contribution status after approval: {contribution.status}")
            
        except Exception as e:
            print(f"Error during approval: {str(e)}")
    else:
        print("No pending contributions found. Creating a test contribution...")
        
        # Get a council and field for testing
        council = Council.objects.first()
        field = DataField.objects.filter(slug='council_nation').first()
        
        if council and field:
            # Create a test contribution
            contribution = Contribution.objects.create(
                user=user,
                council=council,
                field=field,
                value='1',  # England
                status='pending'
            )
            print(f"Created test contribution {contribution.id}")
            
            # Test approval
            factory = RequestFactory()
            request = factory.post(f'/contribute/{contribution.id}/approve/')
            request.user = user
            request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
            
            try:
                response = review_contribution(request, contribution.id, 'approve')
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.content.decode()}")
                
                contribution.refresh_from_db()
                print(f"Contribution status after approval: {contribution.status}")
                
            except Exception as e:
                print(f"Error during approval: {str(e)}")
        else:
            print("No council or field found for testing")

if __name__ == '__main__':
    test_approval()
