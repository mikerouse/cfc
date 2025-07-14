"""
New views for the improved data architecture.
These views handle contributions using the new CouncilCharacteristic and FinancialFigure models.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST
import logging

from .models import Council, DataField, FinancialYear
from .models.new_data_model import (
    CouncilCharacteristic, 
    FinancialFigure, 
    ContributionV2,
    CouncilCharacteristicHistory,
    FinancialFigureHistory
)

logger = logging.getLogger(__name__)


@require_POST
@login_required
def submit_contribution_v2(request):
    """
    Handle contribution submissions using the new data architecture.
    
    This replaces the problematic _apply_contribution function that was causing
    database constraint violations when trying to store council characteristics
    in the FigureSubmission model.
    """
    try:
        # Get form data
        council_id = request.POST.get('council_id')
        field_slug = request.POST.get('field_slug')
        year_slug = request.POST.get('year_slug')  # May be None for characteristics
        value = request.POST.get('value', '').strip()
        source_description = request.POST.get('source_description', '').strip()
        
        # Validate required fields
        if not all([council_id, field_slug, value]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: council, field, and value are required'
            })
        
        # Get objects
        council = get_object_or_404(Council, id=council_id)
        field = get_object_or_404(DataField, slug=field_slug)
        
        # Year is optional for characteristics
        year = None
        if year_slug:
            year = get_object_or_404(FinancialYear, slug=year_slug)
        
        # Determine if this is a characteristic or financial figure
        is_characteristic = field.category == 'characteristic'
        
        if is_characteristic and year_slug:
            return JsonResponse({
                'success': False,
                'error': 'Council characteristics should not have a year specified'
            })
        
        if not is_characteristic and not year_slug:
            return JsonResponse({
                'success': False,
                'error': 'Financial figures must specify a year'
            })
        
        # Get current value for comparison
        current_value = None
        if is_characteristic:
            try:
                current_char = CouncilCharacteristic.objects.get(
                    council=council,
                    field=field
                )
                current_value = current_char.value
            except CouncilCharacteristic.DoesNotExist:
                current_value = None
        else:
            try:
                current_figure = FinancialFigure.objects.get(
                    council=council,
                    field=field,
                    year=year
                )
                current_value = current_figure.value
            except FinancialFigure.DoesNotExist:
                current_value = None
        
        # Check if the value is actually different
        if current_value == value:
            return JsonResponse({
                'success': False,
                'error': 'The submitted value is the same as the current value'
            })
        
        # Create the contribution
        with transaction.atomic():
            contribution = ContributionV2.objects.create(
                user=request.user,
                council=council,
                field=field,
                year=year,  # Will be None for characteristics
                value=value,
                current_value=current_value,
                source_description=source_description,
                status='pending',
                created=timezone.now()
            )
            
            logger.info(
                f"New contribution submitted: {contribution.id} by {request.user.username} "
                f"for {council.name} - {field.name} = {value}"
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Thank you! Your contribution for {field.name} has been submitted for review.',
            'contribution_id': contribution.id
        })
        
    except Exception as e:
        logger.error(f"Error in submit_contribution_v2: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your contribution. Please try again.'
        })


@login_required
def approve_contribution_v2(request, contribution_id):
    """
    Approve a contribution using the new data architecture.
    
    This replaces the problematic approval system that was causing database
    constraint violations.
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to approve contributions.")
        return redirect('contribute')
    
    try:
        contribution = get_object_or_404(ContributionV2, id=contribution_id, status='pending')
        
        with transaction.atomic():
            # Determine if this is a characteristic or financial figure
            is_characteristic = contribution.field.category == 'characteristic'
            
            if is_characteristic:
                # Update or create council characteristic
                characteristic, created = CouncilCharacteristic.objects.get_or_create(
                    council=contribution.council,
                    field=contribution.field,
                    defaults={
                        'value': contribution.value,
                        'last_updated': timezone.now(),
                        'updated_by': request.user
                    }
                )
                
                if not created:
                    # Store history before updating
                    CouncilCharacteristicHistory.objects.create(
                        characteristic=characteristic,
                        old_value=characteristic.value,
                        new_value=contribution.value,
                        changed_by=request.user,
                        changed_date=timezone.now(),
                        reason=f"Approved contribution #{contribution.id}"
                    )
                    
                    # Update the characteristic
                    characteristic.value = contribution.value
                    characteristic.last_updated = timezone.now()
                    characteristic.updated_by = request.user
                    characteristic.save()
                
            else:
                # Update or create financial figure
                figure, created = FinancialFigure.objects.get_or_create(
                    council=contribution.council,
                    field=contribution.field,
                    year=contribution.year,
                    defaults={
                        'value': contribution.value,
                        'last_updated': timezone.now(),
                        'updated_by': request.user
                    }
                )
                
                if not created:
                    # Store history before updating
                    FinancialFigureHistory.objects.create(
                        figure=figure,
                        old_value=figure.value,
                        new_value=contribution.value,
                        changed_by=request.user,
                        changed_date=timezone.now(),
                        reason=f"Approved contribution #{contribution.id}"
                    )
                    
                    # Update the figure
                    figure.value = contribution.value
                    figure.last_updated = timezone.now()
                    figure.updated_by = request.user
                    figure.save()
            
            # Mark contribution as approved
            contribution.status = 'approved'
            contribution.approved_by = request.user
            contribution.approved_date = timezone.now()
            contribution.save()
            
            logger.info(
                f"Contribution approved: {contribution.id} by {request.user.username} "
                f"for {contribution.council.name} - {contribution.field.name}"
            )
            
            messages.success(request, f"Contribution approved successfully!")
            
    except Exception as e:
        logger.error(f"Error approving contribution {contribution_id}: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while approving the contribution.")
    
    return redirect('contribute')


@require_POST
@login_required
def reject_contribution_v2(request, contribution_id):
    """Reject a contribution with an optional reason."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        contribution = get_object_or_404(ContributionV2, id=contribution_id, status='pending')
        
        rejection_reason = request.POST.get('reason', '').strip()
        
        contribution.status = 'rejected'
        contribution.rejected_by = request.user
        contribution.rejected_date = timezone.now()
        contribution.rejection_reason = rejection_reason
        contribution.save()
        
        logger.info(
            f"Contribution rejected: {contribution.id} by {request.user.username} "
            f"for {contribution.council.name} - {contribution.field.name}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Contribution rejected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error rejecting contribution {contribution_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while rejecting the contribution.'
        })


def get_council_data_v2(request, council_id):
    """
    Get council data using the new data architecture.
    Returns both characteristics and financial figures.
    """
    try:
        council = get_object_or_404(Council, id=council_id)
        
        # Get characteristics
        characteristics = {}
        for char in CouncilCharacteristic.objects.filter(council=council).select_related('field'):
            characteristics[char.field.slug] = {
                'value': char.value,
                'last_updated': char.last_updated.isoformat() if char.last_updated else None,
                'field_name': char.field.name
            }
        
        # Get financial figures
        financial_data = {}
        for figure in FinancialFigure.objects.filter(council=council).select_related('field', 'year'):
            year_slug = figure.year.slug if figure.year else 'unknown'
            if year_slug not in financial_data:
                financial_data[year_slug] = {}
            
            financial_data[year_slug][figure.field.slug] = {
                'value': figure.value,
                'last_updated': figure.last_updated.isoformat() if figure.last_updated else None,
                'field_name': figure.field.name
            }
        
        return JsonResponse({
            'success': True,
            'council': {
                'id': council.id,
                'name': council.name,
                'characteristics': characteristics,
                'financial_data': financial_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting council data for {council_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while fetching council data.'
        })


def pending_contributions_v2(request):
    """
    View to show pending contributions using the new data architecture.
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view pending contributions.")
        return redirect('home')
    
    pending_contributions = ContributionV2.objects.filter(
        status='pending'
    ).select_related(
        'user', 'council', 'field', 'year'
    ).order_by('-created')
    
    context = {
        'pending_contributions': pending_contributions,
        'title': 'Pending Contributions (New System)'
    }
    
    return render(request, 'council_finance/pending_contributions_v2.html', context)
