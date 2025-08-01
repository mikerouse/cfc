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

logger = logging.getLogger(__name__)


def is_tier_5_user(user):
    """Check if user has God Mode (Tier 5) permissions"""
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.tier and user.profile.tier.level >= 5)


@login_required
@user_passes_test(is_tier_5_user)
def council_management_dashboard(request):
    """
    Main council management dashboard with overview, search, and quick actions
    """    # Get search and filter parameters
    search_query = request.GET.get('q', '')
    council_type_filter = request.GET.get('type', '')
    nation_filter = request.GET.get('nation', '')
    status_filter = request.GET.get('status', 'active')
    
    # Build queryset with filters
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
    
    # Pagination
    paginator = Paginator(councils, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_councils = Council.objects.count()
    active_councils = Council.objects.filter(status='active').count()
    inactive_councils = Council.objects.filter(status='inactive').count()
    councils_with_data = Council.objects.annotate(
        data_count=Count('financial_figures') + Count('characteristics')
    ).filter(data_count__gt=0).count()
    
    # Get dropdown options
    council_types = CouncilType.objects.all().order_by('name')
    nations = CouncilNation.objects.all().order_by('name')
    
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
    
    return render(request, 'council_finance/council_management/dashboard.html', context)


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
        
        if not council_name:
            messages.error(request, "Council name is required")
            return redirect('council_management_dashboard')
        
        try:
            # Auto-generate slug if not provided
            if not council_slug:
                council_slug = slugify(council_name)
            
            # Check if council already exists
            if Council.objects.filter(Q(name=council_name) | Q(slug=council_slug)).exists():
                messages.error(request, f"Council with name '{council_name}' or slug '{council_slug}' already exists")
                return redirect('council_management_dashboard')
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
                    website=website or None,
                    latest_population=int(population) if population.isdigit() else None,
                    status='active'
                )
                
                # Add postcode as a council characteristic if provided
                if postcode:
                    try:
                        postcode_field = DataField.objects.get(slug='council_hq_post_code')
                        CouncilCharacteristic.objects.create(
                            council=council,
                            field=postcode_field,
                            value=postcode
                        )
                    except DataField.DoesNotExist:
                        logger.warning(f"Postcode field (council_hq_post_code) not found, skipping postcode '{postcode}' for council {council.name}")
                
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
    
    context = {
        'council_types': council_types,
        'nations': nations,
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
            if council.postcode != (postcode or None):
                changes.append(f"Postcode: '{council.postcode or ''}' → '{postcode or ''}'")
            
            pop_value = int(population) if population.isdigit() else None
            if council.population != pop_value:
                changes.append(f"Population: '{council.population or ''}' → '{pop_value or ''}'")
            if council.status != status:
                changes.append(f"Status: '{council.status}' → '{status}'")
            
            # Update the council
            with transaction.atomic():
                council.name = council_name
                council.slug = council_slug
                council.council_type = council_type
                council.council_nation = council_nation
                council.website = website or None
                council.postcode = postcode or None
                council.population = pop_value
                council.status = status
                council.save()
                
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
    
    context = {
        'council': council,
        'council_types': council_types,
        'nations': nations,
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
    Bulk import councils from CSV/Excel/JSON with progress tracking
    """
    if request.method == 'POST':
        import_file = request.FILES.get('council_import_file')
        preview_import = request.POST.get('preview_import') == '1'
        confirm_import = request.POST.get('confirm_import') == '1'
        
        if not import_file and not confirm_import:
            messages.error(request, "Please select a file to import")
            return redirect('bulk_import_councils')
        
        try:
            import pandas as pd
            import json
            
            if confirm_import and request.session.get('import_preview'):
                # Confirmed import from session data
                preview_data = request.session['import_preview']
                df = pd.DataFrame(preview_data['data'])
            else:
                # New file upload
                if import_file.name.endswith('.csv'):
                    df = pd.read_csv(import_file)
                elif import_file.name.endswith('.xlsx'):
                    df = pd.read_excel(import_file)
                elif import_file.name.endswith('.json'):
                    data = json.load(import_file)
                    df = pd.DataFrame(data)
                else:
                    messages.error(request, "Unsupported file format. Please use CSV, Excel, or JSON.")
                    return redirect('bulk_import_councils')
            
            # Validate required columns
            required_columns = ['name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                messages.error(request, f"Missing required columns: {', '.join(missing_columns)}")
                return redirect('bulk_import_councils')
            
            if preview_import and not confirm_import:
                # Preview mode - show what would be imported
                preview_data = df.head(20).to_dict('records')  # Show more in preview
                request.session['import_preview'] = {
                    'data': df.to_dict('records'),  # Store all data
                    'total_rows': len(df)
                }
                
                context = {
                    'preview_data': preview_data,
                    'total_rows': len(df),
                    'file_name': import_file.name if import_file else 'Session Data',
                }
                
                return render(request, 'council_finance/council_management/import_preview.html', context)
            else:
                # Actual import
                created_count = 0
                skipped_count = 0
                error_count = 0
                total_issues_created = 0
                new_councils = []
                errors = []
                
                with transaction.atomic():
                    for index, row in df.iterrows():
                        try:
                            council_name = str(row['name']).strip()
                            if not council_name or council_name.lower() in ['nan', 'none', '']:
                                continue
                                
                            council_slug = slugify(row.get('slug', council_name))
                            
                            # Check if council already exists
                            if not Council.objects.filter(Q(name=council_name) | Q(slug=council_slug)).exists():
                                # Get related objects
                                council_type = None
                                if 'council_type' in row and pd.notna(row['council_type']):
                                    try:
                                        council_type = CouncilType.objects.get(slug=str(row['council_type']).lower())
                                    except CouncilType.DoesNotExist:
                                        try:
                                            council_type = CouncilType.objects.get(name__icontains=str(row['council_type']))
                                        except CouncilType.DoesNotExist:
                                            pass
                                
                                council_nation = None
                                if 'nation' in row and pd.notna(row['nation']):
                                    try:
                                        council_nation = CouncilNation.objects.get(slug=str(row['nation']).lower())
                                    except CouncilNation.DoesNotExist:
                                        try:
                                            council_nation = CouncilNation.objects.get(name__icontains=str(row['nation']))
                                        except CouncilNation.DoesNotExist:
                                            pass
                                
                                # Create council
                                council = Council.objects.create(
                                    name=council_name,
                                    slug=council_slug,
                                    council_type=council_type,
                                    council_nation=council_nation,
                                    website=str(row['website']).strip() if 'website' in row and pd.notna(row['website']) else None,
                                    postcode=str(row['postcode']).strip() if 'postcode' in row and pd.notna(row['postcode']) else None,
                                    population=int(row['population']) if 'population' in row and pd.notna(row['population']) and str(row['population']).replace('.0', '').isdigit() else None,
                                    status='active'
                                )
                                
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
                
        except ImportError:
            messages.error(request, "pandas library not available. Please install it to use the import feature.")
        except Exception as e:
            logger.error(f"Error during bulk import: {e}")
            messages.error(request, f"Error importing councils: {str(e)}")
    
    return redirect('council_management_dashboard')


@login_required
@user_passes_test(is_tier_5_user)
def import_page(request):
    """
    Show the bulk import page with form and instructions
    """
    context = {
        'max_file_size': '10MB',  # Could be made configurable
    }
    
    return render(request, 'council_finance/council_management/import.html', context)


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