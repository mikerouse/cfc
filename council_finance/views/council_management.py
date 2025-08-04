"""
Council Management Views

This module provides comprehensive council management functionality including:
- Creating, editing, merging and deleting councils
- Bulk CSV import with progress tracking
- Council search and filtering
- Modern mobile-friendly interface
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.text import slugify
import json
import logging

from ..models import (
    Council, CouncilType, CouncilNation, DataField,
    CouncilCharacteristic, FinancialFigure, DataIssue,
    ActivityLog
)
from ..smart_data_quality import generate_missing_data_issues_for_council
from ..activity_logging import log_activity

# Import Event Viewer for comprehensive error reporting and analytics
try:
    from event_viewer.models import SystemEvent
    EVENT_VIEWER_AVAILABLE = True
except ImportError:
    EVENT_VIEWER_AVAILABLE = False

logger = logging.getLogger(__name__)


def log_council_management_event(request, level, category, title, message, details=None, council=None):
    """
    Log council management events to Event Viewer system for comprehensive monitoring.
    
    Args:
        request: HTTP request object
        level: Event level ('debug', 'info', 'warning', 'error', 'critical')  
        category: Event category ('user_activity', 'performance', 'exception', etc.)
        title: Brief event title
        message: Detailed event message
        details: Optional dictionary of additional event details
        council: Optional Council object for context
    """
    if not EVENT_VIEWER_AVAILABLE:
        return
        
    try:
        event_details = {
            'module': 'council_management',
            'function': request.resolver_match.url_name if hasattr(request, 'resolver_match') else 'unknown',
            'user_tier': getattr(request.user.profile, 'tier', {}).get('level') if hasattr(request.user, 'profile') else None,
            'request_method': request.method,
            'query_params': dict(request.GET),
        }
        
        if council:
            event_details.update({
                'council_id': council.id,
                'council_name': council.name,
                'council_slug': council.slug,
                'council_type': council.council_type.name if council.council_type else None,
                'council_nation': council.council_nation.name if council.council_nation else None,
            })
            
        if details:
            event_details.update(details)
            
        SystemEvent.objects.create(
            source='council_management',
            level=level,
            category=category,
            title=title,
            message=message,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            details=event_details
        )
        
    except Exception as e:
        # Silently fail event logging to prevent breaking main functionality
        logger.error(f"Failed to log council management event: {e}")


def track_performance(request, action, start_time, details=None):
    """Track performance metrics for council management operations."""
    import time
    duration_ms = int((time.time() - start_time) * 1000)
    
    level = 'warning' if duration_ms > 2000 else 'info'
    
    log_council_management_event(
        request, 
        level, 
        'performance',
        f'Council Management Performance: {action}',
        f'{action} completed in {duration_ms}ms',
        {
            'action': action,
            'duration_ms': duration_ms,
            'performance_threshold_exceeded': duration_ms > 2000,
            **(details or {})
        }
    )


def is_tier_5_user(user):
    """Check if user has God Mode (Tier 5) permissions"""
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.tier and user.profile.tier.level >= 5)


@login_required
@user_passes_test(is_tier_5_user)
def council_management_dashboard(request):
    """
    Main council management dashboard with overview, search, and quick actions.
    Enhanced with comprehensive error reporting and analytics logging.
    """
    import time
    start_time = time.time()
    
    try:
        # Log dashboard access
        log_council_management_event(
            request, 
            'info', 
            'user_activity',
            'Council Management Dashboard Accessed',
            f'User {request.user.username} accessed council management dashboard',
            {'access_time': timezone.now().isoformat()}
        )
        
        # Get search and filter parameters
        search_query = request.GET.get('q', '')
        council_type_filter = request.GET.get('type', '')
        nation_filter = request.GET.get('nation', '')
        status_filter = request.GET.get('status', 'active')
        
        # Log search/filter usage for analytics
        if search_query or council_type_filter or nation_filter or status_filter != 'active':
            log_council_management_event(
                request,
                'info',
                'user_activity', 
                'Council Search/Filter Applied',
                f'User applied filters: query="{search_query}", type="{council_type_filter}", nation="{nation_filter}", status="{status_filter}"',
                {
                    'search_query': search_query,
                    'council_type_filter': council_type_filter,
                    'nation_filter': nation_filter,
                    'status_filter': status_filter,
                    'has_search': bool(search_query),
                    'has_filters': bool(council_type_filter or nation_filter or status_filter != 'active')
                }
            )
        
        # Build queryset with filters - monitor database performance
        db_start = time.time()
        councils = Council.objects.select_related('council_type', 'council_nation')
        
        if search_query:
            councils = councils.filter(
                Q(name__icontains=search_query) |
                Q(slug__icontains=search_query)
            )
        
        if council_type_filter:
            councils = councils.filter(council_type__slug=council_type_filter)
        
        if nation_filter:
            councils = councils.filter(council_nation__slug=nation_filter)
        
        if status_filter:
            councils = councils.filter(status=status_filter)
            
        # Order by name
        councils = councils.order_by('name')
        
        # Pagination with performance monitoring
        paginator = Paginator(councils, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        db_duration = (time.time() - db_start) * 1000
        if db_duration > 500:  # Log slow database queries
            log_council_management_event(
                request,
                'warning',
                'performance',
                'Slow Database Query in Council Dashboard',
                f'Council listing query took {db_duration:.2f}ms',
                {
                    'query_duration_ms': db_duration,
                    'result_count': page_obj.paginator.count,
                    'has_search': bool(search_query),
                    'has_filters': bool(council_type_filter or nation_filter or status_filter != 'active')
                }
            )
        
        # Get statistics with error handling
        try:
            stats_start = time.time()
            total_councils = Council.objects.count()
            active_councils = Council.objects.filter(status='active').count()
            inactive_councils = Council.objects.filter(status='inactive').count()
            councils_with_data = Council.objects.annotate(
                data_count=Count('financial_figures') + Count('characteristics')
            ).filter(data_count__gt=0).count()
            
            stats_duration = (time.time() - stats_start) * 1000
            if stats_duration > 1000:  # Log slow statistics queries
                log_council_management_event(
                    request,
                    'warning',
                    'performance',
                    'Slow Statistics Query in Council Dashboard',
                    f'Statistics calculation took {stats_duration:.2f}ms',
                    {'stats_duration_ms': stats_duration}
                )
                
        except Exception as e:
            logger.error(f"Error calculating council statistics: {e}")
            log_council_management_event(
                request,
                'error',
                'exception',
                'Council Statistics Calculation Failed',
                f'Failed to calculate council statistics: {str(e)}',
                {'error_type': type(e).__name__, 'error_message': str(e)}
            )
            # Provide fallback values
            total_councils = active_councils = inactive_councils = councils_with_data = 0
        
        # Get dropdown options with error handling
        try:
            council_types = CouncilType.objects.all().order_by('name')
            nations = CouncilNation.objects.all().order_by('name')
        except Exception as e:
            logger.error(f"Error loading dropdown options: {e}")
            log_council_management_event(
                request,
                'error',
                'exception',
                'Dropdown Options Loading Failed',
                f'Failed to load council types/nations: {str(e)}',
                {'error_type': type(e).__name__, 'error_message': str(e)}
            )
            council_types = []
            nations = []
        
        # Build context
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'council_type_filter': council_type_filter,
            'nation_filter': nation_filter,
            'status_filter': status_filter,
            'council_types': council_types,
            'nations': nations,
            'stats': {
                'total': total_councils,
                'active': active_councils,
                'inactive': inactive_councils,
                'with_data': councils_with_data,
            },
        }
        
        # Track overall performance
        track_performance(
            request, 
            'dashboard_load', 
            start_time,
            {
                'result_count': page_obj.paginator.count,
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'has_search': bool(search_query),
                'has_filters': bool(council_type_filter or nation_filter or status_filter != 'active')
            }
        )
        
        return render(request, 'council_finance/council_management/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Critical error in council management dashboard: {e}")
        log_council_management_event(
            request,
            'critical',
            'exception',
            'Council Management Dashboard Critical Error',
            f'Critical error loading dashboard: {str(e)}',
            {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'request_path': request.path,
                'request_method': request.method
            }
        )
        
        # Provide minimal error context for fallback rendering
        messages.error(request, 'An error occurred loading the council management dashboard. Please try again.')
        return render(request, 'council_finance/council_management/dashboard.html', {
            'page_obj': None,
            'search_query': '',
            'council_type_filter': '',
            'nation_filter': '',
            'status_filter': 'active',
            'council_types': [],
            'nations': [],
            'stats': {'total': 0, 'active': 0, 'inactive': 0, 'with_data': 0},
        })


@login_required
@user_passes_test(is_tier_5_user)
def create_council(request):
    """
    Create a new council with form validation and progress tracking
    """
    if request.method == 'POST':
        council_name = request.POST.get('council_name', '').strip()
        council_slug = request.POST.get('council_slug', '').strip()
        council_type_id = request.POST.get('council_type', '').strip()
        council_nation_id = request.POST.get('council_nation', '').strip()
        website = request.POST.get('website', '').strip()
        postcode = request.POST.get('postcode', '').strip()
        population = request.POST.get('population', '').strip()
        
        # Validate required fields
        errors = []
        
        if not council_name:
            errors.append("Council name is required")
        
        if not website:
            errors.append("Council website is required")
        
        if not council_type_id:
            errors.append("Council type is required") 
            
        if not council_nation_id:
            errors.append("Council nation is required")
            
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('create_council')
        
        try:
            # Auto-generate slug if not provided
            if not council_slug:
                council_slug = slugify(council_name)
            
            # Check if council already exists
            if Council.objects.filter(Q(name=council_name) | Q(slug=council_slug)).exists():
                messages.error(request, f"Council with name '{council_name}' or slug '{council_slug}' already exists")
                return redirect('create_council')
                
            # Validate required characteristic fields
            characteristic_fields = DataField.objects.filter(category='characteristic', required=True)
            missing_required = []
            
            for field in characteristic_fields:
                field_value = request.POST.get(f'characteristic_{field.slug}', '').strip()
                if not field_value and field.slug not in ['council_type', 'council_nation', 'council_name']:
                    missing_required.append(field.name)
            
            if missing_required:
                messages.error(request, f"Required fields missing: {', '.join(missing_required)}")
                return redirect('create_council')
                
            # Get related objects
            council_type = None
            if council_type_id:
                try:
                    council_type = CouncilType.objects.get(id=council_type_id)
                except CouncilType.DoesNotExist:
                    pass
            
            council_nation = None
            if council_nation_id:
                try:
                    council_nation = CouncilNation.objects.get(id=council_nation_id)
                except CouncilNation.DoesNotExist:
                    pass
                    
            # Create the council
            with transaction.atomic():
                council = Council.objects.create(
                    name=council_name,
                    slug=council_slug,
                    council_type=council_type,
                    council_nation=council_nation,
                    website=website,  # No fallback to None since it's now validated as required
                    latest_population=int(population) if population.isdigit() else None,
                    status='active'
                )
                
                # Save all characteristic fields dynamically
                all_characteristic_fields = DataField.objects.filter(category='characteristic')
                for field in all_characteristic_fields:
                    # Skip fields handled by the main council model
                    if field.slug in ['council_type', 'council_nation', 'council_name']:
                        continue
                        
                    field_value = request.POST.get(f'characteristic_{field.slug}', '').strip()
                    
                    # Handle special cases for backwards compatibility
                    if field.slug == 'council_hq_post_code' and not field_value:
                        field_value = postcode
                    elif field.slug == 'population' and not field_value:
                        field_value = population
                    
                    if field_value:
                        try:
                            CouncilCharacteristic.objects.create(
                                council=council,
                                field=field,
                                value=field_value
                            )
                        except Exception as e:
                            logger.warning(f"Could not save characteristic {field.slug} for council {council.name}: {e}")
                
                # Generate missing data issues for contribution queues
                try:
                    issues_created = generate_missing_data_issues_for_council(council)
                    messages.success(
                        request, 
                        f"Council '{council_name}' created successfully with {issues_created} data contribution opportunities added to queues"
                    )
                except Exception as e:
                    logger.error(f"Error generating data issues for council {council.id}: {e}")
                    messages.success(request, f"Council '{council_name}' created successfully")
                    messages.warning(request, f"Note: Could not auto-generate contribution queue entries: {str(e)}")
                
                # Log the activity
                log_activity(
                    request,
                    council=council,
                    activity='council_creation',
                    action='Created new council via management interface',
                    extra=f"Council: {council_name}, Slug: {council_slug}, Type: {council_type}, Nation: {council_nation}"
                )
                
        except Exception as e:
            logger.error(f"Error creating council: {e}")
            messages.error(request, f"Error creating council: {str(e)}")
        
        return redirect('council_management_dashboard')
    
    # GET request - show create form
    council_types = CouncilType.objects.all().order_by('name')
    nations = CouncilNation.objects.all().order_by('name')
    
    # Get all characteristic fields for dynamic form generation
    characteristic_fields = DataField.objects.filter(
        category='characteristic'
    ).exclude(
        slug__in=['council_type', 'council_nation', 'council_name']  # Exclude fields handled separately
    ).order_by('display_order', 'name')
    
    context = {
        'council_types': council_types,
        'nations': nations,
        'characteristic_fields': characteristic_fields,
    }
    
    return render(request, 'council_finance/council_management/create.html', context)


@login_required
@user_passes_test(is_tier_5_user)
def edit_council(request, council_id):
    """
    Edit an existing council
    """
    council = get_object_or_404(Council, id=council_id)
    
    if request.method == 'POST':
        council_name = request.POST.get('council_name', '').strip()
        council_slug = request.POST.get('council_slug', '').strip()
        council_type_id = request.POST.get('council_type', '').strip()
        council_nation_id = request.POST.get('council_nation', '').strip()
        website = request.POST.get('website', '').strip()
        postcode = request.POST.get('postcode', '').strip()
        population = request.POST.get('population', '').strip()
        status = request.POST.get('status', 'active')
        
        if not council_name:
            messages.error(request, "Council name is required")
            return redirect('edit_council', council_id=council.id)
        
        try:
            # Auto-generate slug if not provided
            if not council_slug:
                council_slug = slugify(council_name)
            
            # Check if another council already exists with this name/slug
            existing_council = Council.objects.filter(
                Q(name=council_name) | Q(slug=council_slug)
            ).exclude(id=council.id).first()
            
            if existing_council:
                messages.error(request, f"Another council with name '{council_name}' or slug '{council_slug}' already exists")
                return redirect('edit_council', council_id=council.id)
            
            # Get related objects
            council_type = None
            if council_type_id:
                try:
                    council_type = CouncilType.objects.get(id=council_type_id)
                except CouncilType.DoesNotExist:
                    pass
            
            council_nation = None
            if council_nation_id:
                try:
                    council_nation = CouncilNation.objects.get(id=council_nation_id)
                except CouncilNation.DoesNotExist:
                    pass
            
            # Track changes
            changes = []
            if council.name != council_name:
                changes.append(f"Name: '{council.name}' → '{council_name}'")
            if council.slug != council_slug:
                changes.append(f"Slug: '{council.slug}' → '{council_slug}'")
            if council.council_type != council_type:
                old_type = council.council_type.name if council.council_type else 'None'
                new_type = council_type.name if council_type else 'None'
                changes.append(f"Type: '{old_type}' → '{new_type}'")
            if council.council_nation != council_nation:
                old_nation = council.council_nation.name if council.council_nation else 'None'
                new_nation = council_nation.name if council_nation else 'None'
                changes.append(f"Nation: '{old_nation}' → '{new_nation}'")
            if council.website != (website or None):
                changes.append(f"Website: '{council.website or ''}' → '{website or ''}'")
            
            pop_value = int(population) if population.isdigit() else None
            if (council.latest_population or 0) != (pop_value or 0):
                changes.append(f"Population: '{council.latest_population or ''}' → '{pop_value or ''}'")
            if council.status != status:
                changes.append(f"Status: '{council.status}' → '{status}'")
            
            # Update the council
            with transaction.atomic():
                council.name = council_name
                council.slug = council_slug
                council.council_type = council_type
                council.council_nation = council_nation
                council.website = website or None
                council.latest_population = pop_value
                council.status = status
                council.save()
                
                # Update all characteristic fields dynamically
                all_characteristic_fields = DataField.objects.filter(category='characteristic')
                for field in all_characteristic_fields:
                    # Skip fields handled by the main council model
                    if field.slug in ['council_type', 'council_nation', 'council_name']:
                        continue
                        
                    field_value = request.POST.get(f'characteristic_{field.slug}', '').strip()
                    
                    # Handle special cases for backwards compatibility
                    if field.slug == 'council_hq_post_code' and not field_value:
                        field_value = postcode
                    elif field.slug == 'population' and not field_value:
                        field_value = population
                    
                    # Get or create the characteristic
                    characteristic, created = CouncilCharacteristic.objects.get_or_create(
                        council=council,
                        field=field,
                        defaults={'value': field_value}
                    )
                    
                    # Update the value if it changed
                    if not created and characteristic.value != field_value:
                        old_value = characteristic.value
                        characteristic.value = field_value
                        characteristic.save()
                        changes.append(f"{field.name}: '{old_value or ''}' → '{field_value or ''}'")
                    elif created and field_value:
                        changes.append(f"{field.name}: '' → '{field_value}'")
                
                # Log the activity
                if changes:
                    log_activity(
                        request,
                        council=council,
                        activity='council_update',
                        action='Updated council via management interface',
                        extra=f"Changes: {'; '.join(changes)}"
                    )
                
                messages.success(request, f"Council '{council_name}' updated successfully")
                
        except Exception as e:
            logger.error(f"Error updating council {council.id}: {e}")
            messages.error(request, f"Error updating council: {str(e)}")
        
        return redirect('council_management_dashboard')
    
    # GET request - show edit form
    council_types = CouncilType.objects.all().order_by('name')
    nations = CouncilNation.objects.all().order_by('name')
    
    # Get all characteristic fields for dynamic form generation
    characteristic_fields = DataField.objects.filter(
        category='characteristic'
    ).exclude(
        slug__in=['council_type', 'council_nation', 'council_name']  # Exclude fields handled separately
    ).order_by('display_order', 'name')
    
    # Get existing characteristic values for this council
    existing_characteristics = {}
    for char in CouncilCharacteristic.objects.filter(council=council).select_related('field'):
        existing_characteristics[char.field.slug] = char.value
    
    context = {
        'council': council,
        'council_types': council_types,
        'nations': nations,
        'characteristic_fields': characteristic_fields,
        'existing_characteristics': existing_characteristics,
    }
    
    return render(request, 'council_finance/council_management/edit.html', context)


@login_required
@user_passes_test(is_tier_5_user)
def delete_council(request, council_id):
    """
    Delete a council (with safety checks)
    """
    council = get_object_or_404(Council, id=council_id)
    
    if request.method == 'POST':
        # Check if council has data
        has_financial_data = FinancialFigure.objects.filter(council=council).exists()
        has_characteristic_data = CouncilCharacteristic.objects.filter(council=council).exists()
        
        if has_financial_data or has_characteristic_data:
            messages.error(request, f"Cannot delete council '{council.name}' - it has associated data. Please remove all data first.")
            return redirect('council_management_dashboard')
        
        try:
            council_name = council.name
            with transaction.atomic():
                # Log the activity before deletion
                log_activity(
                    request,
                    council=council,
                    activity='council_deletion',
                    action='Deleted council via management interface',
                    extra=f"Council: {council_name} (ID: {council.id})"
                )
                
                # Delete the council
                council.delete()
                
                messages.success(request, f"Council '{council_name}' deleted successfully")
                
        except Exception as e:
            logger.error(f"Error deleting council {council.id}: {e}")
            messages.error(request, f"Error deleting council: {str(e)}")
    
    return redirect('council_management_dashboard')


@login_required
@user_passes_test(is_tier_5_user)
def bulk_import(request):
    """
    Bulk import councils from CSV/Excel/JSON with progress tracking.
    Enhanced with comprehensive error reporting and analytics logging.
    """
    import time
    start_time = time.time()
    
    if request.method == 'POST':
        import_file = request.FILES.get('council_import_file')
        preview_import = request.POST.get('preview_import') == '1'
        confirm_import = request.POST.get('confirm_import') == '1'
        
        # Log import attempt
        log_council_management_event(
            request,
            'info',
            'user_activity',
            'Council Bulk Import Attempted',
            f'User {request.user.username} initiated bulk import process',
            {
                'has_file': bool(import_file),
                'file_name': import_file.name if import_file else None,
                'file_size': import_file.size if import_file else None,
                'preview_mode': preview_import,
                'is_confirmation': confirm_import
            }
        )
        
        if not import_file and not confirm_import:
            log_council_management_event(
                request,
                'warning',
                'user_activity',
                'Council Import Failed: No File Selected',
                'User attempted import without selecting a file',
                {'error_type': 'validation_error'}
            )
            messages.error(request, "Please select a file to import")
            return redirect('bulk_import_councils')
        
        try:
            import csv
            import json
            import io
            
            # Try to import pandas for Excel support, but fall back to CSV-only if not available
            pandas_available = False
            try:
                import pandas as pd
                pandas_available = True
                log_council_management_event(
                    request,
                    'info',
                    'configuration',
                    'Council Import: Pandas Available',
                    'Excel file support enabled via pandas library'
                )
            except ImportError:
                pd = None
                log_council_management_event(
                    request,
                    'warning',
                    'configuration',
                    'Council Import: Pandas Not Available',
                    'Excel file support disabled - pandas library not installed',
                    {'limitation': 'csv_json_only'}
                )
            
            # Track file parsing performance
            parse_start = time.time()
            
            if confirm_import and request.session.get('import_preview'):
                # Confirmed import from session data
                preview_data = request.session['import_preview']
                data_records = preview_data['data']
                
                log_council_management_event(
                    request,
                    'info',
                    'user_activity',
                    'Council Import Confirmed from Preview',
                    f'User confirmed import of {len(data_records)} records from preview',
                    {
                        'record_count': len(data_records),
                        'source': 'session_preview_data'
                    }
                )
            else:
                # New file upload - parse based on file type
                file_extension = import_file.name.lower().split('.')[-1] if import_file else 'unknown'
                
                try:
                    if import_file.name.endswith('.csv'):
                        # Use native CSV parsing - always available
                        import_file.seek(0)  # Reset file pointer
                        try:
                            content = import_file.read().decode('utf-8')
                        except UnicodeDecodeError as e:
                            log_council_management_event(
                                request,
                                'error',
                                'data_quality',
                                'Council Import: CSV Encoding Error',
                                f'Failed to decode CSV file as UTF-8: {str(e)}',
                                {
                                    'file_name': import_file.name,
                                    'file_size': import_file.size,
                                    'encoding_error': str(e)
                                }
                            )
                            messages.error(request, "CSV file encoding error. Please ensure file is saved as UTF-8.")
                            return redirect('bulk_import_councils')
                            
                        csv_reader = csv.DictReader(io.StringIO(content))
                        data_records = list(csv_reader)
                        
                        log_council_management_event(
                            request,
                            'info',
                            'data_processing',
                            'Council Import: CSV Parsed Successfully',
                            f'Successfully parsed CSV file with {len(data_records)} records',
                            {
                                'file_name': import_file.name,
                                'file_size': import_file.size,
                                'record_count': len(data_records),
                                'columns': list(data_records[0].keys()) if data_records else []
                            }
                        )
                        
                    elif import_file.name.endswith('.xlsx'):
                        # Excel requires pandas
                        if not pandas_available:
                            log_council_management_event(
                                request,
                                'error',
                                'configuration',
                                'Council Import: Excel Not Supported',
                                'User attempted Excel import but pandas not available',
                                {
                                    'file_name': import_file.name,
                                    'file_size': import_file.size,
                                    'required_library': 'pandas'
                                }
                            )
                            messages.error(request, "Excel files require pandas library. Please install pandas or use CSV format instead.")
                            return redirect('bulk_import_councils')
                            
                        data_records = pd.read_excel(import_file).to_dict('records')
                        
                        log_council_management_event(
                            request,
                            'info',
                            'data_processing',
                            'Council Import: Excel Parsed Successfully',
                            f'Successfully parsed Excel file with {len(data_records)} records',
                            {
                                'file_name': import_file.name,
                                'file_size': import_file.size,
                                'record_count': len(data_records),
                                'columns': list(data_records[0].keys()) if data_records else []
                            }
                        )
                        
                    elif import_file.name.endswith('.json'):
                        # JSON parsing - always available
                        import_file.seek(0)  # Reset file pointer
                        try:
                            data = json.load(import_file)
                        except json.JSONDecodeError as e:
                            log_council_management_event(
                                request,
                                'error',
                                'data_quality',
                                'Council Import: JSON Parse Error',
                                f'Failed to parse JSON file: {str(e)}',
                                {
                                    'file_name': import_file.name,
                                    'file_size': import_file.size,
                                    'json_error': str(e),
                                    'error_line': getattr(e, 'lineno', None),
                                    'error_column': getattr(e, 'colno', None)
                                }
                            )
                            messages.error(request, f"JSON file parsing error: {str(e)}")
                            return redirect('bulk_import_councils')
                            
                        if isinstance(data, list):
                            data_records = data
                            
                            log_council_management_event(
                                request,
                                'info',
                                'data_processing',
                                'Council Import: JSON Parsed Successfully',
                                f'Successfully parsed JSON file with {len(data_records)} records',
                                {
                                    'file_name': import_file.name,
                                    'file_size': import_file.size,
                                    'record_count': len(data_records)
                                }
                            )
                        else:
                            log_council_management_event(
                                request,
                                'error',
                                'data_quality',
                                'Council Import: Invalid JSON Structure',
                                'JSON file does not contain an array of objects',
                                {
                                    'file_name': import_file.name,
                                    'file_size': import_file.size,
                                    'actual_type': type(data).__name__
                                }
                            )
                            messages.error(request, "JSON file must contain an array of council objects.")
                            return redirect('bulk_import_councils')
                    else:
                        log_council_management_event(
                            request,
                            'error',
                            'user_activity',
                            'Council Import: Unsupported File Format',
                            f'User attempted to import unsupported file format: {file_extension}',
                            {
                                'file_name': import_file.name,
                                'file_extension': file_extension,
                                'supported_formats': ['csv', 'xlsx', 'json']
                            }
                        )
                        messages.error(request, "Unsupported file format. Please use CSV, Excel (.xlsx), or JSON.")
                        return redirect('bulk_import_councils')
                        
                except Exception as e:
                    log_council_management_event(
                        request,
                        'error',
                        'exception',
                        'Council Import: File Parsing Critical Error',
                        f'Unexpected error parsing file: {str(e)}',
                        {
                            'file_name': import_file.name,
                            'file_size': import_file.size,
                            'file_extension': file_extension,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    )
                    messages.error(request, f"Error parsing file: {str(e)}")
                    return redirect('bulk_import_councils')
                    
                # Ensure we have data
                if not data_records:
                    log_council_management_event(
                        request,
                        'warning',
                        'data_quality',
                        'Council Import: Empty File',
                        'No data records found in uploaded file',
                        {
                            'file_name': import_file.name,
                            'file_size': import_file.size,
                            'file_extension': file_extension
                        }
                    )
                    messages.error(request, "No data found in the uploaded file.")
                    return redirect('bulk_import_councils')
                    
            # Track file parsing performance
            parse_duration = (time.time() - parse_start) * 1000
            if parse_duration > 1000:  # Log slow file parsing
                log_council_management_event(
                    request,
                    'warning',
                    'performance',
                    'Council Import: Slow File Parsing',
                    f'File parsing took {parse_duration:.2f}ms',
                    {
                        'parse_duration_ms': parse_duration,
                        'record_count': len(data_records),
                        'file_size': import_file.size if import_file else 0
                    }
                )
            
            # Convert to consistent format (list of dicts) and validate required columns
            if data_records and isinstance(data_records[0], dict):
                columns = set(data_records[0].keys())
            else:
                messages.error(request, "Invalid file format. Expected tabular data with column headers.")
                return redirect('bulk_import_councils')
            
            # Required columns for CSV import (database constraints)
            # Note: Only 'name' is required at database level
            # Additional business validation (website, type, nation) is performed during import
            required_columns = ['name']  # Database requirement - absolutely required
            recommended_columns = ['website', 'council_type', 'nation']  # Business validation requirements
            
            missing_columns = [col for col in required_columns if col not in columns]
            if missing_columns:
                messages.error(request, f"Missing required columns: {', '.join(missing_columns)}")
                return redirect('bulk_import_councils')
            
            # Check for recommended columns and warn if missing    
            missing_recommended = [col for col in recommended_columns if col not in columns]
            if missing_recommended:
                log_council_management_event(
                    request,
                    'warning',
                    'data_quality',
                    'Council Import: Missing Recommended Columns',
                    f'Import file missing recommended columns: {", ".join(missing_recommended)}',
                    {
                        'missing_columns': missing_recommended,
                        'available_columns': list(columns),
                        'impact': 'councils_may_be_incomplete'
                    }
                )
                messages.warning(request, f"Missing recommended columns (import will continue but councils may be incomplete): {', '.join(missing_recommended)}")
            
            if preview_import and not confirm_import:
                # Preview mode - show what would be imported
                preview_data = data_records[:20]  # Show first 20 records for preview
                request.session['import_preview'] = {
                    'data': data_records,  # Store all data
                    'total_rows': len(data_records)
                }
                
                # Log preview generation
                log_council_management_event(
                    request,
                    'info',
                    'user_activity',
                    'Council Import Preview Generated',
                    f'Generated preview for {len(data_records)} records, showing first {len(preview_data)}',
                    {
                        'total_records': len(data_records),
                        'preview_records': len(preview_data),
                        'file_name': import_file.name if import_file else 'Session Data',
                        'available_columns': list(columns),
                        'missing_recommended': missing_recommended
                    }
                )
                
                context = {
                    'preview_data': preview_data,
                    'total_rows': len(data_records),
                    'file_name': import_file.name if import_file else 'Session Data',
                }
                
                try:
                    return render(request, 'council_finance/council_management/import_preview.html', context)
                except Exception as e:
                    log_council_management_event(
                        request,
                        'error',
                        'exception',
                        'Council Import: Preview Template Error',
                        f'Failed to render import preview template: {str(e)}',
                        {
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'template_name': 'import_preview.html',
                            'context_keys': list(context.keys())
                        }
                    )
                    messages.error(request, f"Error displaying import preview: {str(e)}")
                    return redirect('bulk_import_councils')
            else:
                # Actual import
                created_count = 0
                skipped_count = 0
                error_count = 0
                total_issues_created = 0
                new_councils = []
                errors = []
                
                # Helper function to check if value is valid (defined once, used multiple times)
                def is_valid_value(value):
                    if value is None:
                        return False
                    str_val = str(value).strip()
                    return str_val and str_val.lower() not in ['nan', 'none', 'null', '']
                
                with transaction.atomic():
                    for index, row in enumerate(data_records):
                        try:
                            council_name = str(row.get('name', '')).strip()
                            if not council_name or council_name.lower() in ['nan', 'none', '']:
                                continue
                                
                            council_slug = slugify(row.get('slug', council_name))
                            
                            # Check if council already exists
                            if not Council.objects.filter(Q(name=council_name) | Q(slug=council_slug)).exists():
                                # Validate required business fields before creating council
                                validation_errors = []
                                
                                # Website is now considered required for new councils
                                if not ('website' in row and is_valid_value(row['website'])):
                                    validation_errors.append("Website is required")
                                
                                # Skip validation if we have critical errors
                                if validation_errors:
                                    error_count += 1
                                    errors.append(f"Row {index + 1} ({council_name}): {', '.join(validation_errors)}")
                                    continue
                                
                                # Get related objects - use proper None checking instead of pd.notna()
                                council_type = None
                                if 'council_type' in row and row['council_type'] and str(row['council_type']).strip():
                                    try:
                                        council_type = CouncilType.objects.get(slug=str(row['council_type']).lower())
                                    except CouncilType.DoesNotExist:
                                        try:
                                            council_type = CouncilType.objects.get(name__icontains=str(row['council_type']))
                                        except CouncilType.DoesNotExist:
                                            pass
                                
                                council_nation = None
                                if 'nation' in row and row['nation'] and str(row['nation']).strip():
                                    try:
                                        council_nation = CouncilNation.objects.get(slug=str(row['nation']).lower())
                                    except CouncilNation.DoesNotExist:
                                        try:
                                            council_nation = CouncilNation.objects.get(name__icontains=str(row['nation']))
                                        except CouncilNation.DoesNotExist:
                                            pass
                                
                                # Create council
                                website_value = None
                                if 'website' in row and is_valid_value(row['website']):
                                    website_value = str(row['website']).strip()
                                
                                population_value = None
                                if 'population' in row and is_valid_value(row['population']):
                                    pop_str = str(row['population']).replace('.0', '')
                                    if pop_str.isdigit():
                                        population_value = int(pop_str)
                                
                                council = Council.objects.create(
                                    name=council_name,
                                    slug=council_slug,
                                    council_type=council_type,
                                    council_nation=council_nation,
                                    website=website_value,
                                    latest_population=population_value,
                                    status='active'
                                )
                                
                                # Save all characteristic fields dynamically
                                all_characteristic_fields = DataField.objects.filter(category='characteristic')
                                for field in all_characteristic_fields:
                                    # Skip fields handled by the main council model
                                    if field.slug in ['council_type', 'council_nation', 'council_name']:
                                        continue
                                        
                                    field_value = None
                                    
                                    # Try different column name variations for this field
                                    possible_columns = [field.slug, field.slug.replace('-', '_'), field.name.lower()]
                                    for col_name in possible_columns:
                                        if col_name in row and is_valid_value(row[col_name]):
                                            field_value = str(row[col_name]).strip()
                                            break
                                    
                                    # Handle special backwards compatibility cases
                                    if not field_value:
                                        if field.slug == 'council_hq_post_code' and 'postcode' in row and is_valid_value(row['postcode']):
                                            field_value = str(row['postcode']).strip()
                                        elif field.slug == 'population' and 'population' in row and is_valid_value(row['population']):
                                            field_value = str(row['population']).strip()
                                        elif field.slug == 'council_website' and 'website' in row and is_valid_value(row['website']):
                                            field_value = str(row['website']).strip()
                                    
                                    if field_value:
                                        try:
                                            CouncilCharacteristic.objects.create(
                                                council=council,
                                                field=field,
                                                value=field_value
                                            )
                                        except Exception as e:
                                            logger.warning(f"Could not save characteristic {field.slug} during import for council {council.name}: {e}")
                                
                                new_councils.append(council)
                                created_count += 1
                            else:
                                skipped_count += 1
                                
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Row {index + 1}: {str(e)}")
                            logger.error(f"Error importing council from row {index + 1}: {e}")
                
                # Generate missing data issues for all new councils (outside the main transaction)
                if new_councils:
                    try:
                        for council in new_councils:
                            issues_created = generate_missing_data_issues_for_council(council)
                            total_issues_created += issues_created
                    except Exception as e:
                        logger.error(f"Error generating data issues during bulk import: {e}")
                        messages.warning(request, f"Import completed but some contribution queue entries may not have been generated: {str(e)}")
                
                # Clear session data
                if 'import_preview' in request.session:
                    del request.session['import_preview']
                
                # Success message
                success_msg = f"Import complete: {created_count} councils created, {skipped_count} skipped (already exist)"
                if total_issues_created > 0:
                    success_msg += f", {total_issues_created} data contribution opportunities added to queues"
                if error_count > 0:
                    success_msg += f", {error_count} errors encountered"
                
                messages.success(request, success_msg)
                
                if errors:
                    messages.warning(request, f"Errors encountered: {'; '.join(errors[:5])}")  # Show first 5 errors
                
                # Log the import activity
                log_activity(
                    request,
                    activity='bulk_council_import',
                    action='Bulk imported councils via management interface',
                    extra=f"Created: {created_count}, Skipped: {skipped_count}, Errors: {error_count}, Issues: {total_issues_created}"
                )
                
        except ImportError as e:
            # This should now only catch issues with other imports, not pandas
            log_council_management_event(
                request,
                'error',
                'configuration',
                'Council Import: Library Import Error',
                f'Required library not available: {str(e)}',
                {
                    'error_type': 'ImportError',
                    'error_message': str(e),
                    'missing_library': str(e).split("'")[1] if "'" in str(e) else 'unknown'
                }
            )
            messages.error(request, f"Required library not available: {str(e)}. Please contact administrator.")
            
        except Exception as e:
            logger.error(f"Error during bulk import: {e}")
            log_council_management_event(
                request,
                'critical',
                'exception',
                'Council Import: Critical Import Error',
                f'Critical error during council import: {str(e)}',
                {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'stack_trace': str(e.__traceback__) if hasattr(e, '__traceback__') else None,
                    'has_file': bool(import_file),
                    'file_name': import_file.name if import_file else None,
                    'preview_mode': preview_import,
                    'is_confirmation': confirm_import
                }
            )
            messages.error(request, f"Error importing councils: {str(e)}")
            
        finally:
            # Track overall import operation performance
            track_performance(
                request,
                'council_import_operation',
                start_time,
                {
                    'has_file': bool(import_file),
                    'preview_mode': preview_import,
                    'is_confirmation': confirm_import,
                    'operation_completed': True
                }
            )
    
    return redirect('council_management_dashboard')


@login_required
@user_passes_test(is_tier_5_user)
def import_page(request):
    """
    Show the bulk import page with form and instructions.
    Enhanced with error reporting and analytics logging.
    """
    import time
    start_time = time.time()
    
    try:
        # Log import page access
        log_council_management_event(
            request,
            'info',
            'user_activity',
            'Council Import Page Accessed',
            f'User {request.user.username} accessed council import page',
            {'access_time': timezone.now().isoformat()}
        )
        
        # Get all characteristic fields to show expected columns
        try:
            characteristic_fields = DataField.objects.filter(
                category='characteristic'
            ).exclude(
                slug__in=['council_type', 'council_nation', 'council_name']  # Exclude fields handled separately
            ).order_by('display_order', 'name')
            
        except Exception as e:
            logger.error(f"Error loading characteristic fields for import: {e}")
            log_council_management_event(
                request,
                'error',
                'exception',
                'Council Import: Failed to Load Field Metadata',
                f'Error loading characteristic fields: {str(e)}',
                {
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            characteristic_fields = []
            messages.warning(request, "Some import field information could not be loaded.")
        
        context = {
            'max_file_size': '10MB',  # Could be made configurable
            'characteristic_fields': characteristic_fields,
        }
        
        # Track page load performance
        track_performance(
            request,
            'import_page_load',
            start_time,
            {'field_count': len(characteristic_fields)}
        )
        
        return render(request, 'council_finance/council_management/import.html', context)
        
    except Exception as e:
        logger.error(f"Critical error loading council import page: {e}")
        log_council_management_event(
            request,
            'critical',
            'exception',
            'Council Import: Page Load Critical Error',
            f'Critical error loading import page: {str(e)}',
            {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'request_path': request.path
            }
        )
        messages.error(request, 'An error occurred loading the import page. Please try again.')
        return redirect('council_management_dashboard')


@login_required
@user_passes_test(is_tier_5_user)
@require_http_methods(["POST"])
def cancel_import(request):
    """
    Cancel an import preview and clear session data
    """
    if 'import_preview' in request.session:
        del request.session['import_preview']
    messages.info(request, "Import cancelled")
    return redirect('council_management_dashboard')