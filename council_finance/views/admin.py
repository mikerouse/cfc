import logging
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

from council_finance.models import (
    Council,
    FinancialYear,
    CouncilList,
    CounterDefinition,
    SiteCounter,
    GroupCounter,
    DataField,
    ActivityLog,
    CouncilCharacteristic,
    FinancialFigure,
    FinancialFigureHistory,
    CouncilCharacteristicHistory,
    AIProvider,
    AIModel,
    AIAnalysisTemplate,
    AIAnalysisConfiguration,
    CouncilAIAnalysis,
)
from council_finance.forms import (
    CounterDefinitionForm,
    SiteCounterForm,
    GroupCounterForm,
    DataFieldForm,
)
from council_finance.year_utils import previous_year_label
from ..activity_logging import log_activity

logger = logging.getLogger(__name__)


@login_required
def counter_definition_list(request):
    """Display a list of existing counters for quick management."""
    counters = CounterDefinition.objects.select_related('created_by').all().order_by('name')
    search_query = request.GET.get('search', '')
    if search_query:
        counters = counters.filter(name__icontains=search_query)

    type_filter = request.GET.get('type', '')
    if type_filter:
        if type_filter == 'headline':
            counters = counters.filter(headline=True)
        elif type_filter == 'default':
            counters = counters.filter(show_by_default=True)
        elif type_filter == 'currency':
            counters = counters.filter(show_currency=True)
        elif type_filter == 'friendly':
            counters = counters.filter(friendly_format=True)

    status_filter = request.GET.get('status', '')

    page_size = int(request.GET.get('page_size', 15))
    paginator = Paginator(counters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_definitions = CounterDefinition.objects.count()
    total_site_counters = SiteCounter.objects.count()
    total_group_counters = GroupCounter.objects.count()

    used_definition_ids = set()
    used_definition_ids.update(SiteCounter.objects.values_list('counter_id', flat=True))
    used_definition_ids.update(GroupCounter.objects.values_list('counter_id', flat=True))
    unused_counters = total_definitions - len(used_definition_ids)

    for counter in page_obj:
        counter.site_counter_count = SiteCounter.objects.filter(counter=counter).count()
        counter.group_counter_count = GroupCounter.objects.filter(counter=counter).count()
        counter.council_counter_count = 0

    stats = {
        'total_definitions': total_definitions,
        'total_site_counters': total_site_counters,
        'total_group_counters': total_group_counters,
        'unused_counters': unused_counters,
    }

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'search_query': search_query,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'page_size': page_size,
    }

    return render(
        request,
        "council_finance/counter_definition_list.html",
        context,
    )


@login_required
def counter_delete(request, slug):
    """Delete a counter definition if the user has permission."""
    counter = get_object_or_404(CounterDefinition, slug=slug)

    if not (request.user.is_superuser or counter.created_by == request.user):
        messages.error(request, "You don't have permission to delete this counter.")
        return redirect('counter_definitions')

    site_counter_count = SiteCounter.objects.filter(counter=counter).count()
    group_counter_count = GroupCounter.objects.filter(counter=counter).count()

    if site_counter_count > 0 or group_counter_count > 0:
        messages.warning(
            request,
            f"This counter is currently in use ({site_counter_count} site counters, {group_counter_count} group counters). "
            "Please remove those references first."
        )
        return redirect('counter_definitions')

    counter_name = counter.name
    counter.delete()

    messages.success(request, f"Counter '{counter_name}' was successfully deleted.")
    log_activity(
        request,
        activity="counter_delete",
        action=f"deleted counter definition: {slug}",
        extra={"counter_name": counter_name}
    )

    return redirect('counter_definitions')


@login_required
def site_counter_list(request):
    """List all site-wide counters."""
    counters = SiteCounter.objects.all().select_related('counter', 'year').order_by('name')
    search_query = request.GET.get('search', '')
    if search_query:
        counters = counters.filter(name__icontains=search_query)

    status_filter = request.GET.get('status', '')
    if status_filter:
        if status_filter == 'homepage':
            counters = counters.filter(promote_homepage=True)
        elif status_filter == 'currency':
            counters = counters.filter(show_currency=True)
        elif status_filter == 'friendly':
            counters = counters.filter(friendly_format=True)

    page_size = int(request.GET.get('page_size', 10))
    paginator = Paginator(counters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_counters = SiteCounter.objects.count()
    homepage_counters = SiteCounter.objects.filter(promote_homepage=True).count()
    available_base_counters = CounterDefinition.objects.count()

    context = {
        'page_obj': page_obj,
        'total_counters': total_counters,
        'homepage_counters': homepage_counters,
        'available_base_counters': available_base_counters,
        'search_query': search_query,
        'status_filter': status_filter,
        'page_size': page_size,
    }

    return render(
        request,
        "council_finance/site_counter_list.html",
        context,
    )


@login_required
def group_counter_list(request):
    """List all custom group counters."""
    counters = GroupCounter.objects.all().select_related('counter', 'year', 'council_list').order_by('name')
    search_query = request.GET.get('search', '')
    if search_query:
        counters = counters.filter(name__icontains=search_query)

    status_filter = request.GET.get('status', '')
    if status_filter:
        if status_filter == 'homepage':
            counters = counters.filter(promote_homepage=True)
        elif status_filter == 'currency':
            counters = counters.filter(show_currency=True)
        elif status_filter == 'friendly':
            counters = counters.filter(friendly_format=True)

    page_size = int(request.GET.get('page_size', 10))
    paginator = Paginator(counters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_counters = GroupCounter.objects.count()
    homepage_counters = GroupCounter.objects.filter(promote_homepage=True).count()
    available_base_counters = CounterDefinition.objects.count()

    context = {
        'page_obj': page_obj,
        'total_counters': total_counters,
        'homepage_counters': homepage_counters,
        'available_base_counters': available_base_counters,
        'search_query': search_query,
        'status_filter': status_filter,
        'page_size': page_size,
    }

    return render(
        request,
        "council_finance/group_counter_list.html",
        context,
    )


@login_required
def site_counter_form(request, slug=None):
    """Create or edit a site-wide counter."""
    base_slug = request.GET.get('base')
    base_counter = None
    if base_slug:
        base_counter = CounterDefinition.objects.filter(slug=base_slug).first()

    counter = get_object_or_404(SiteCounter, slug=slug) if slug else None

    initial = {}
    if not counter and base_counter:
        initial = {
            'name': f"{base_counter.name} (Site)",
            'counter': base_counter,
            'show_currency': base_counter.show_currency,
            'friendly_format': base_counter.friendly_format,
            'precision': base_counter.precision,
            'duration': base_counter.duration,
        }

    form = SiteCounterForm(request.POST or None, instance=counter, initial=initial)

    if request.method == "POST" and form.is_valid():
        site_counter = form.save()
        messages.success(request, f"Site counter '{site_counter.name}' saved successfully.")
        log_activity(
            request,
            activity="site_counter_save",
            log_type="user",
            action=slug or "new",
            response="saved",
            extra={'counter_name': site_counter.name}
        )
        return redirect("site_counter_list")

    counter_choices = CounterDefinition.objects.all().order_by('name')
    year_choices = FinancialYear.objects.all().order_by('-label')

    context = {
        "form": form,
        "counter": counter,
        "is_edit": slug is not None,
        "base_counter": base_counter,
        "counter_choices": counter_choices,
        "year_choices": year_choices,
        "title": f"Edit {counter.name}" if counter else "Add Site-Wide Counter",
    }

    return render(
        request,
        "council_finance/site_counter_form.html",
        context,
    )


@login_required
def site_counter_delete(request, slug):
    """Delete a site counter."""
    counter = get_object_or_404(SiteCounter, slug=slug)
    counter_name = counter.name

    counter.delete()
    messages.success(request, f"Site counter '{counter_name}' was successfully deleted.")
    log_activity(
        request,
        activity="site_counter_delete",
        action=f"deleted site counter: {slug}",
        extra={"counter_name": counter_name}
    )

    return redirect('site_counter_list')


@login_required
def group_counter_form(request, slug=None):
    """Create or edit a custom group counter."""
    counter = get_object_or_404(GroupCounter, slug=slug) if slug else None
    form = GroupCounterForm(request.POST or None, instance=counter)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Counter saved.")
        log_activity(
            request,
            activity="counter_group",
            log_type="user",
            action=slug or "new",
            response="saved",
        )
        return redirect("group_counter_list")
    return render(
        request,
        "council_finance/group_counter_form.html",
        {"form": form},
    )


@login_required
def group_counter_delete(request, slug):
    """Delete a group counter."""
    counter = get_object_or_404(GroupCounter, slug=slug)
    counter_name = counter.name

    counter.delete()
    messages.success(request, f"Group counter '{counter_name}' was successfully deleted.")
    log_activity(
        request,
        activity="group_counter_delete",
        action=f"deleted group counter: {slug}",
        extra={"counter_name": counter_name}
    )

    return redirect('group_counter_list')


@login_required
def counter_definition_form(request, slug=None):
    """Create or edit a single counter definition, with live preview for selected council."""
    counter = get_object_or_404(CounterDefinition, slug=slug) if slug else None
    form = CounterDefinitionForm(request.POST or None, instance=counter)

    councils = Council.objects.all().order_by("name")
    years = list(FinancialYear.objects.order_by("-label"))
    for y in years:
        y.display_label = "Year to Date" if y.label.lower() == "general" else y.label
    preview_council_slug = request.GET.get("preview_council") or (
        councils[0].slug if councils else None
    )
    valid_year_labels = [y.label for y in years]
    requested_year = request.GET.get("preview_year")
    preview_year_label = (
        requested_year
        if requested_year in valid_year_labels
        else (years[0].label if years else None)
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Counter saved.")
        log_activity(
            request,
            activity="counter_definition",
            log_type="user",
            action=slug or "new",
            response="saved",
        )
        return redirect("counter_definitions")
    
    context = {
        "form": form,
        "available_fields": [f.slug for f in DataField.objects.all()],
        "councils": councils,
        "years": years,
        "preview_council_slug": preview_council_slug,
        "preview_year_label": preview_year_label,
    }
    return render(
        request,
        "council_finance/counter_definition_form.html",
        context,
    )


@login_required
def counter_factoid_assignment(request, slug):
    """Manage factoid template assignments for a counter."""
    counter = get_object_or_404(CounterDefinition, slug=slug)
    
    from ..forms import CounterFactoidAssignmentForm
    
    if request.method == "POST":
        form = CounterFactoidAssignmentForm(counter, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Factoid templates updated for {counter.name}")
            log_activity(
                request,
                activity="counter_factoid_assignment",
                log_type="user",
                action="updated",
                response="saved",
                extra={"counter_slug": slug}
            )
            return redirect("counter_definitions")
    else:
        form = CounterFactoidAssignmentForm(counter)
    
    context = {
        "counter": counter,
        "form": form,
    }
    return render(
        request,
        "council_finance/counter_factoid_assignment.html",
        context,
    )


@login_required
@require_GET
def preview_counter_value(request):
    from council_finance.agents.counter_agent import CounterAgent
    council_slug = request.GET.get("council")
    formula = request.GET.get("formula")
    year_label = request.GET.get("year")
    year = None
    if year_label:
        year = FinancialYear.objects.filter(label=year_label).first()
    if not year:
        year = FinancialYear.objects.order_by("-label").first()
    if not (council_slug and formula and year):
        return JsonResponse({"error": "Missing data"}, status=400)
    agent = CounterAgent()
    from council_finance.models import CounterDefinition

    try:
        council = Council.objects.get(slug=council_slug)
        figure_map = {}
        missing = set()        # Get financial figures for this council and year
        for f in FinancialFigure.objects.filter(council=council, year=year):
            slug = f.field.slug
            if f.value is None:
                missing.add(slug)
                continue
            try:
                figure_map[slug] = float(f.value)
            except (TypeError, ValueError):
                missing.add(slug)
        import ast, operator

        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Num):
                return node.n
            if isinstance(node, ast.BinOp):
                return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                return -_eval(node.operand)
            if isinstance(node, ast.Name):
                if node.id in missing:
                    raise ValueError(
                        (
                            "Counter failed - no %s figure is held for %s in %s. "
                            "Please populate the figure from the council's official sources and try again."
                        )
                        % (node.id.replace("_", " "), council.name, year.label)
                    )
                return figure_map.get(node.id, 0)
            raise ValueError("Unsupported expression element")

        tree = ast.parse(formula, mode="eval")
        value = float(_eval(tree))
        precision = int(request.GET.get("precision", 0))
        show_currency = request.GET.get("show_currency", "true") == "true"
        friendly_format = request.GET.get("friendly_format", "false") == "true"

        class Dummy:
            pass

        dummy = Dummy()
        dummy.precision = precision
        dummy.show_currency = show_currency
        dummy.friendly_format = friendly_format
        from council_finance.models.counter import CounterDefinition as CD

        formatted = CD.format_value(dummy, value)
        return JsonResponse({"value": value, "formatted": formatted})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        return JsonResponse({"error": "calculation failed"}, status=400)


@login_required
@require_GET
def preview_aggregate_counter(request):
    """Preview a site or group counter by summing across councils."""
    from council_finance.agents.counter_agent import CounterAgent

    counter_param = request.GET.get("counter")
    if not counter_param:
        return JsonResponse({"error": "Missing counter"}, status=400)
    
    # Handle both slug and ID lookups for counter
    if str(counter_param).isdigit():
        counter = CounterDefinition.objects.filter(pk=counter_param).first()
    else:
        counter = CounterDefinition.objects.filter(slug=counter_param).first()
    
    if not counter:
        return JsonResponse({"error": "Counter not found"}, status=400)
    
    counter_slug = counter.slug
    
    year_param = request.GET.get("year")
    if year_param and year_param != "all":
        year = (
            FinancialYear.objects.filter(pk=year_param).first()
            if str(year_param).isdigit()
            else FinancialYear.objects.filter(label=year_param).first()
        )
        if not year:
            return JsonResponse({"error": "Invalid year"}, status=400)
        years = [year]
    else:
        years = list(FinancialYear.objects.order_by("-label"))
    
    if not years:
        return JsonResponse({"error": "No financial years available"}, status=400)

    councils = Council.objects.all()
    cslugs = request.GET.get("councils")
    if cslugs:
        councils = councils.filter(slug__in=[s for s in cslugs.split(",") if s])
    clist = request.GET.get("council_list")
    if clist:
        try:
            cl = CouncilList.objects.get(pk=clist)
            councils = councils.filter(pk__in=cl.councils.values_list("pk", flat=True))
        except CouncilList.DoesNotExist:
            pass
    ctypes = request.GET.get("council_types")
    if ctypes:
        ids = [int(i) for i in ctypes.split(",") if i]
        councils = councils.filter(council_type_id__in=ids)

    agent = CounterAgent()
    total = 0
    for c in councils:
        for yr in years:
            values = agent.run(council_slug=c.slug, year_label=yr.label)
            result = values.get(counter_slug)
            if result and result.get("value") is not None:
                try:
                    total += float(result["value"])
                except (TypeError, ValueError):
                    pass

    dummy = type(
        "D",
        (),
        {
            "precision": int(request.GET.get("precision", 0)),
            "show_currency": request.GET.get("show_currency", "true") == "true",
            "friendly_format": request.GET.get("friendly_format", "false") == "true",
        },
    )()

    formatted = CounterDefinition.format_value(dummy, total)
    return JsonResponse({"value": total, "formatted": formatted})


def god_mode(request):
    """Admin god mode panel."""
    from django.contrib import messages
    from django.http import HttpResponseRedirect    
    from django.urls import reverse
    from ..models import (
        FinancialYear, Council, DataField, 
        DataIssue, Contribution, RejectionLog, UserProfile,
        CouncilCharacteristic, FinancialFigure
    )
    from ..year_utils import get_recommended_next_year
    from ..smart_data_quality import smart_assess_data_issues, get_data_collection_priorities, generate_missing_data_issues_for_council
    from datetime import datetime, timedelta
    
    # Handle POST requests for God Mode actions
    if request.method == 'POST':
        if 'add_financial_year' in request.POST:
            year_label = request.POST.get('new_year_label', '').strip()
            if year_label:
                try:
                    from ..year_utils import create_year_with_smart_defaults
                    year, created = create_year_with_smart_defaults(year_label, user=request.user)
                    if created:
                        messages.success(request, f"Financial year {year_label} created successfully")
                    else:
                        messages.info(request, f"Financial year {year_label} already exists")
                except Exception as e:
                    messages.error(request, f"Error creating financial year: {str(e)}")
            return HttpResponseRedirect(reverse('god_mode'))
        
        elif 'set_current_year' in request.POST:
            year_id = request.POST.get('current_year_id')
            if year_id:
                try:
                    # Clear existing current year
                    FinancialYear.objects.filter(is_current=True).update(is_current=False)
                    # Set new current year                    year = FinancialYear.objects.get(id=year_id)
                    year.is_current = True
                    year.save()
                    messages.success(request, f"Set {year.label} as current financial year")
                except Exception as e:
                    messages.error(request, f"Error setting current year: {str(e)}")
            return HttpResponseRedirect(reverse('god_mode'))
        
        elif 'assess_issues' in request.POST:
            try:
                issues_created = smart_assess_data_issues()
                messages.success(request, f"Assessment complete: {issues_created} data issues identified")
            except Exception as e:
                messages.error(request, f"Error during assessment: {str(e)}")
            return HttpResponseRedirect(reverse('god_mode'))
        
        elif 'delete_financial_year' in request.POST:
            year_id = request.POST.get('year_id')
            confirm = request.POST.get('confirm_deletion')
            if year_id and confirm == 'yes':
                try:
                    year = FinancialYear.objects.get(id=year_id)
                    if year.can_be_deleted():
                        year_label = year.label
                        year.delete()
                        messages.success(request, f"Financial year {year_label} deleted successfully")
                    else:
                        messages.error(request, f"Cannot delete year {year.label} - it has associated data")
                except FinancialYear.DoesNotExist:
                    messages.error(request, "Financial year not found")
                except Exception as e:
                    error_msg = str(e)
                    # Provide more helpful error messages for common database issues
                    if "no such table" in error_msg.lower():
                        messages.error(request, f"Database schema error: Some tables referenced by this financial year don't exist yet. This may indicate pending migrations. Please run 'python manage.py migrate' to ensure all tables are created.")
                    elif "foreign key constraint" in error_msg.lower():
                        messages.error(request, f"Cannot delete year - it has related data that must be removed first")
                    else:
                        messages.error(request, f"Error deleting financial year: {error_msg}")
            return HttpResponseRedirect(reverse('god_mode'))
    
    # Get financial years data
    financial_years = FinancialYear.objects.all().order_by('-label')
    recommended_year = get_recommended_next_year()
    
    # Get surveillance data
    now = datetime.now()
    day_ago = now - timedelta(days=1)    # User activity surveillance
    user_activity_surveillance = {
        'active_users_24h': UserProfile.objects.count(),  # TODO: Implement proper last_seen tracking
        'contributions_today': Contribution.objects.filter(created__date=now.date()).count(),
        'suspicious_activity_count': 0,  # TODO: Implement suspicious activity detection
    }
    
    # Get high activity users - using points as a proxy for activity
    high_activity_users = UserProfile.objects.filter(
        points__gt=0
    ).order_by('-points')[:5]
    
    # Data quality surveillance
    total_councils = Council.objects.filter(status='active').count()
    total_fields = DataField.objects.count()
    # Count total data points from both characteristics and financial figures
    total_characteristics = CouncilCharacteristic.objects.count()
    total_financial_figures = FinancialFigure.objects.count()
    total_submissions = total_characteristics + total_financial_figures
    max_possible_submissions = total_councils * total_fields * financial_years.count()
    
    data_quality_surveillance = {
        'completeness_percentage': round((total_submissions / max_possible_submissions * 100) if max_possible_submissions > 0 else 0, 1),
        'missing_data_issues': DataIssue.objects.filter(issue_type='missing').count(),
        'consistency_score': 85,  # TODO: Implement actual consistency scoring
    }
    
    # Security monitoring
    security_monitoring = {
        'bulk_operations_24h': 0,  # TODO: Implement bulk operation tracking
        'admin_activities_24h': 0,  # TODO: Implement admin activity tracking
        'unusual_patterns': 0,  # TODO: Implement unusual pattern detection
    }
    
    # Council activity hotspots - councils with most recent data updates
    council_activity_hotspots = Council.objects.filter(
        Q(financial_figures__isnull=False) | Q(characteristics__isnull=False)
    ).distinct()[:5]
    
    # Recent rejections
    recent_rejections = RejectionLog.objects.order_by('-created')[:10]
    
    # Get all councils for quick stats
    all_councils = Council.objects.all()
    
    # Council statistics for the new council management section
    councils_with_data = Council.objects.filter(
        Q(financial_figures__isnull=False) | Q(characteristics__isnull=False)
    ).distinct().count()
    councils_without_data = total_councils - councils_with_data
    councils_active_today = Council.objects.filter(
        Q(financial_figures__updated__date=now.date()) | 
        Q(characteristics__updated__date=now.date())
    ).distinct().count()
    
    # Data collection priorities
    try:
        data_priorities = get_data_collection_priorities()
    except Exception as e:
        data_priorities = {'relevant_years': [], 'year_stats': []}
    
    # Active alerts (placeholder)
    active_alerts = []
    
    context = {
        'financial_years': financial_years,
        'recommended_year': recommended_year,
        'user_activity_surveillance': user_activity_surveillance,
        'high_activity_users': high_activity_users,
        'data_quality_surveillance': data_quality_surveillance,
        'security_monitoring': security_monitoring,
        'council_activity_hotspots': council_activity_hotspots,
        'recent_rejections': recent_rejections,
        'all_councils': all_councils,
        'councils_with_data': councils_with_data,
        'councils_without_data': councils_without_data,
        'councils_active_today': councils_active_today,
        'data_priorities': data_priorities,
        'active_alerts': active_alerts,
    }
    
    return render(request, "council_finance/god_mode.html", context)


def activity_log_entries(request):
    """Get activity log entries."""
    return JsonResponse({"status": "success", "entries": []})


def activity_log_json(request, log_id):
    """Get activity log entry as JSON."""
    return JsonResponse({"status": "success", "log": {}})


__all__ = [
    'counter_definition_list',
    'counter_delete',
    'site_counter_list',
    'group_counter_list',
    'site_counter_form',
    'site_counter_delete',
    'group_counter_form',
    'group_counter_delete',
    'counter_definition_form',
    'preview_counter_value',
    'preview_aggregate_counter',
    'god_mode',
    'activity_log_entries',
    'activity_log_json',
    'ai_management_dashboard',
    'ai_model_form',
    'ai_template_form',
    'ai_configuration_form',
    'ai_analysis_detail',
]


# AI Management Views for God Mode

def ai_management_dashboard(request):
    if not request.user.is_superuser:
        return redirect('home')
    """Main AI management dashboard"""
    context = {
        'providers': AIProvider.objects.all().order_by('name'),
        'models': AIModel.objects.select_related('provider').order_by('provider__name', 'name'),
        'templates': AIAnalysisTemplate.objects.order_by('name'),
        'configurations': AIAnalysisConfiguration.objects.select_related('model', 'template').order_by('-is_default', 'name'),
        'recent_analyses': CouncilAIAnalysis.objects.select_related('council', 'year', 'configuration').order_by('-created')[:10],
    }
    
    return render(request, 'council_finance/ai_management/dashboard.html', context)


def ai_model_form(request, model_id=None):
    if not request.user.is_superuser:
        return redirect('home')
    """Add or edit AI model"""
    if model_id:
        model = get_object_or_404(AIModel, id=model_id)
    else:
        model = None
    
    if request.method == 'POST':
        try:
            provider_id = request.POST.get('provider')
            provider = get_object_or_404(AIProvider, id=provider_id)
            
            if model:
                model.provider = provider
                model.name = request.POST.get('name')
                model.model_id = request.POST.get('model_id') 
                model.max_tokens = int(request.POST.get('max_tokens', 2000))
                model.temperature = float(request.POST.get('temperature', 0.7))
                model.is_active = request.POST.get('is_active') == 'on'
                cost_per_token = request.POST.get('cost_per_token')
                model.cost_per_token = float(cost_per_token) if cost_per_token else None
                model.save()
                messages.success(request, f'AI model "{model.name}" updated successfully')
            else:
                model = AIModel.objects.create(
                    provider=provider,
                    name=request.POST.get('name'),
                    model_id=request.POST.get('model_id'),
                    max_tokens=int(request.POST.get('max_tokens', 2000)),
                    temperature=float(request.POST.get('temperature', 0.7)),
                    is_active=request.POST.get('is_active') == 'on',
                    cost_per_token=float(request.POST.get('cost_per_token')) if request.POST.get('cost_per_token') else None
                )
                messages.success(request, f'AI model "{model.name}" created successfully')
            
            return redirect('ai_management_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error saving AI model: {str(e)}')
    
    context = {
        'model': model,
        'providers': AIProvider.objects.filter(is_active=True).order_by('name'),
    }
    
    return render(request, 'council_finance/ai_management/model_form.html', context)


def ai_template_form(request, template_id=None):
    if not request.user.is_superuser:
        return redirect('home')
    """Add or edit AI analysis template"""
    if template_id:
        template = get_object_or_404(AIAnalysisTemplate, id=template_id)
    else:
        template = None
    
    if request.method == 'POST':
        try:
            if template:
                template.name = request.POST.get('name')
                template.description = request.POST.get('description')
                template.system_prompt = request.POST.get('system_prompt')
                template.analysis_type = request.POST.get('analysis_type')
                template.is_active = request.POST.get('is_active') == 'on'
                template.save()
                messages.success(request, f'AI template "{template.name}" updated successfully')
            else:
                template = AIAnalysisTemplate.objects.create(
                    name=request.POST.get('name'),
                    slug=request.POST.get('name').lower().replace(' ', '-'),
                    description=request.POST.get('description'),
                    system_prompt=request.POST.get('system_prompt'),
                    analysis_type=request.POST.get('analysis_type'),
                    is_active=request.POST.get('is_active') == 'on',
                    created_by=request.user
                )
                messages.success(request, f'AI template "{template.name}" created successfully')
            
            return redirect('ai_management_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error saving AI template: {str(e)}')
    
    # Get available template variables from database
    from council_finance.models import DataField
    
    # Get council characteristics (non-financial fields)
    characteristic_fields = DataField.objects.filter(
        category='characteristic'
    ).order_by('name')
    
    # Get financial fields grouped by category
    financial_fields = DataField.objects.exclude(
        category='characteristic'
    ).order_by('category', 'name')
    
    # Build dynamic variable list
    template_variables = [
        # Core council variables
        '{{ council.name }}',
        '{{ council.council_type.name }}',
        '{{ council.nation.name }}',
        '{{ year.label }}',
        '{{ current_data }}',
        '{{ previous_data }}',
        '{{ comparison_data }}',
    ]
    
    # Add characteristic variables
    for field in characteristic_fields:
        template_variables.append(f'{{{{ council.{field.slug} }}}}')
    
    # Add financial field variables grouped by category
    current_category = None
    for field in financial_fields:
        if field.category != current_category:
            current_category = field.category
            # Add category separator comment in the list
            template_variables.append(f'<!-- {field.get_category_display()} Fields -->')
        template_variables.append(f'{{{{ financial_data.{field.slug} }}}}')
    
    context = {
        'template': template,
        'analysis_types': AIAnalysisTemplate._meta.get_field('analysis_type').choices,
        'template_variables': template_variables,
        'characteristic_fields': characteristic_fields,
        'financial_fields': financial_fields,
    }
    
    return render(request, 'council_finance/ai_management/template_form.html', context)


def ai_configuration_form(request, config_id=None):
    if not request.user.is_superuser:
        return redirect('home')
    """Add or edit AI analysis configuration"""
    if config_id:
        configuration = get_object_or_404(AIAnalysisConfiguration, id=config_id)
    else:
        configuration = None
    
    if request.method == 'POST':
        try:
            model_id = request.POST.get('model')
            template_id = request.POST.get('template')
            model = get_object_or_404(AIModel, id=model_id)
            template = get_object_or_404(AIAnalysisTemplate, id=template_id)
            
            if configuration:
                configuration.name = request.POST.get('name')
                configuration.model = model
                configuration.template = template
                configuration.cache_duration_minutes = int(request.POST.get('cache_duration_minutes', 60))
                configuration.max_retries = int(request.POST.get('max_retries', 3))
                configuration.timeout_seconds = int(request.POST.get('timeout_seconds', 30))
                configuration.is_default = request.POST.get('is_default') == 'on'
                configuration.is_active = request.POST.get('is_active') == 'on'
                configuration.save()
                messages.success(request, f'AI configuration "{configuration.name}" updated successfully')
            else:
                configuration = AIAnalysisConfiguration.objects.create(
                    name=request.POST.get('name'),
                    model=model,
                    template=template,
                    cache_duration_minutes=int(request.POST.get('cache_duration_minutes', 60)),
                    max_retries=int(request.POST.get('max_retries', 3)),
                    timeout_seconds=int(request.POST.get('timeout_seconds', 30)),
                    is_default=request.POST.get('is_default') == 'on',
                    is_active=request.POST.get('is_active') == 'on'
                )
                messages.success(request, f'AI configuration "{configuration.name}" created successfully')
            
            return redirect('ai_management_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error saving AI configuration: {str(e)}')
    
    context = {
        'configuration': configuration,
        'models': AIModel.objects.filter(is_active=True).select_related('provider').order_by('provider__name', 'name'),
        'templates': AIAnalysisTemplate.objects.filter(is_active=True).order_by('name'),
    }
    
    return render(request, 'council_finance/ai_management/configuration_form.html', context)


def ai_analysis_detail(request, analysis_id):
    if not request.user.is_superuser:
        return redirect('home')
    """View detailed AI analysis results"""
    analysis = get_object_or_404(
        CouncilAIAnalysis.objects.select_related('council', 'year', 'configuration', 'configuration__model', 'configuration__template'),
        id=analysis_id
    )
    
    context = {
        'analysis': analysis,
    }
    
    return render(request, 'council_finance/ai_management/analysis_detail.html', context)


@login_required
def field_list(request):
    """Display and manage data fields and characteristics"""
    
    # Get all fields grouped by category
    fields = DataField.objects.all().order_by('category', 'name')
    
    search_query = request.GET.get('search', '')
    if search_query:
        fields = fields.filter(
            Q(name__icontains=search_query) | 
            Q(slug__icontains=search_query) |
            Q(explanation__icontains=search_query)
        )
    
    category_filter = request.GET.get('category', '')
    if category_filter:
        fields = fields.filter(category=category_filter)
    
    # Paginate results
    paginator = Paginator(fields, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get category choices for filter dropdown
    categories = DataField.FIELD_CATEGORIES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': categories,
        'total_fields': fields.count(),
    }
    
    log_activity(
        request,
        activity="field_management_access",
        log_type="admin",
        action="view_field_list",
        extra={
            'total_fields': fields.count(),
            'search_query': search_query,
            'category_filter': category_filter,
        }
    )
    
    return render(request, 'council_finance/admin/field_list.html', context)


def validate_calculated_field_formula(formula, current_field_id=None):
    """
    Validate a formula for a calculated field.
    
    Args:
        formula (str): The formula to validate
        current_field_id (int, optional): ID of the field being edited (to avoid self-references)
    
    Returns:
        list: List of validation error messages, empty if valid
    """
    errors = []
    
    if not formula or not formula.strip():
        errors.append("Calculated fields must have a formula")
        return errors
    
    # Get all existing field names (both variable_name and slug format)
    all_fields = DataField.objects.all()
    existing_field_names = []
    
    for field in all_fields:
        existing_field_names.append(field.variable_name)
        existing_field_names.append(field.slug)
    
    # Sort by length descending to match longer field names first
    existing_field_names.sort(key=len, reverse=True)
    
    # Extract field references by searching for known field names in the formula
    # Use a smarter approach that looks for field names directly in the formula
    field_references = []
    formula_remaining = formula
    
    for field_name in existing_field_names:
        # Check if this field name appears in the formula
        # For hyphenated field names, we need a more careful approach
        import re
        
        # First try exact word boundary match (works for most cases)
        pattern = r'\b' + re.escape(field_name) + r'\b'
        if re.search(pattern, formula_remaining):
            field_references.append(field_name)
            # Remove this field name from consideration to avoid overlaps
            formula_remaining = re.sub(pattern, '', formula_remaining)
        else:
            # For hyphenated names, try matching surrounded by operators or spaces
            # This handles cases where word boundaries don't work properly with hyphens
            operator_pattern = r'(?:^|[\s\+\-\*/\(\)])'+ re.escape(field_name) + r'(?=[\s\+\-\*/\(\)]|$)'
            if re.search(operator_pattern, formula_remaining):
                field_references.append(field_name)
                # Remove this field name from consideration to avoid overlaps
                formula_remaining = re.sub(operator_pattern, '', formula_remaining)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_field_references = []
    for ref in field_references:
        if ref not in seen:
            seen.add(ref)
            unique_field_references.append(ref)
    
    field_references = unique_field_references
    
    if not field_references:
        errors.append("Formula does not reference any fields")
        return errors
    
    # Check if referenced fields exist and validate them
    missing_fields = []
    for field_ref in set(field_references):  # Remove duplicates
        field_found = False
        referenced_field = None
        
        # Try to find the field by multiple methods
        # 1. Direct slug match
        try:
            referenced_field = DataField.objects.get(slug=field_ref)
            field_found = True
        except DataField.DoesNotExist:
            pass
        
        # 2. Direct variable_name match
        if not field_found:
            try:
                referenced_field = DataField.objects.get(slug=field_ref.replace('_', '-'))
                field_found = True
            except DataField.DoesNotExist:
                pass
        
        # 3. Convert underscores to hyphens and try slug
        if not field_found:
            slug_version = field_ref.replace('_', '-')
            try:
                referenced_field = DataField.objects.get(slug=slug_version)
                field_found = True
            except DataField.DoesNotExist:
                pass
        
        # 4. Convert hyphens to underscores and try to find by variable_name
        if not field_found:
            var_version = field_ref.replace('-', '_')
            for field in DataField.objects.all():
                if field.variable_name == var_version:
                    referenced_field = field
                    field_found = True
                    break
        
        if field_found and referenced_field:
            # Prevent self-reference
            if current_field_id and referenced_field.id == current_field_id:
                errors.append(f"Field cannot reference itself: {field_ref}")
                continue
                
            # Prevent circular references for calculated fields
            if referenced_field.category == 'calculated' and referenced_field.formula:
                if _check_circular_reference(referenced_field, current_field_id):
                    errors.append(f"Circular reference detected through field: {field_ref}")
        else:
            missing_fields.append(field_ref)
    
    if missing_fields:
        errors.append(f"Referenced fields do not exist: {', '.join(missing_fields)}")
    
    # Basic syntax validation
    syntax_errors = _validate_formula_syntax(formula)
    errors.extend(syntax_errors)
    
    return errors


def _check_circular_reference(field, current_field_id, visited=None):
    """
    Check for circular references in calculated field formulas.
    
    Args:
        field (DataField): The field to check
        current_field_id (int): ID of the field being created/edited
        visited (set): Set of visited field IDs to detect cycles
    
    Returns:
        bool: True if circular reference detected
    """
    if visited is None:
        visited = set()
    
    if field.id in visited:
        return True
    
    if field.id == current_field_id:
        return True
    
    if field.category != 'calculated' or not field.formula:
        return False
    
    visited.add(field.id)
    
    # Extract field references from this field's formula using improved logic
    all_fields = DataField.objects.all()
    existing_field_names = []
    
    for db_field in all_fields:
        existing_field_names.append(db_field.variable_name)
        existing_field_names.append(db_field.slug)
    
    # Sort by length descending to match longer field names first
    existing_field_names.sort(key=len, reverse=True)
    
    field_references = []
    formula_remaining = field.formula
    
    for field_name in existing_field_names:
        # First try exact word boundary match (works for most cases)
        pattern = r'\b' + re.escape(field_name) + r'\b'
        if re.search(pattern, formula_remaining):
            field_references.append(field_name)
            # Remove this field name from consideration to avoid overlaps
            formula_remaining = re.sub(pattern, '', formula_remaining)
        else:
            # For hyphenated names, try matching surrounded by operators or spaces
            operator_pattern = r'(?:^|[\s\+\-\*/\(\)])'+ re.escape(field_name) + r'(?=[\s\+\-\*/\(\)]|$)'
            if re.search(operator_pattern, formula_remaining):
                field_references.append(field_name)
                # Remove this field name from consideration to avoid overlaps
                formula_remaining = re.sub(operator_pattern, '', formula_remaining)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_field_references = []
    for ref in field_references:
        if ref not in seen:
            seen.add(ref)
            unique_field_references.append(ref)
    
    for field_ref in unique_field_references:
        # Try to find the referenced field
        referenced_field = None
        
        # Try direct slug match
        try:
            referenced_field = DataField.objects.get(slug=field_ref)
        except DataField.DoesNotExist:
            pass
        
        # Try variable_name conversion
        if not referenced_field:
            slug_version = field_ref.replace('_', '-')
            try:
                referenced_field = DataField.objects.get(slug=slug_version)
            except DataField.DoesNotExist:
                pass
        
        # Try reverse conversion
        if not referenced_field:
            var_version = field_ref.replace('-', '_')
            for f in DataField.objects.all():
                if f.variable_name == var_version:
                    referenced_field = f
                    break
        
        if referenced_field:
            if _check_circular_reference(referenced_field, current_field_id, visited.copy()):
                return True
    
    return False


def _validate_formula_syntax(formula):
    """
    Perform basic syntax validation on a formula.
    
    Args:
        formula (str): The formula to validate
    
    Returns:
        list: List of syntax error messages
    """
    errors = []
    
    # Check balanced parentheses
    open_count = 0
    for char in formula:
        if char == '(':
            open_count += 1
        elif char == ')':
            open_count -= 1
            if open_count < 0:
                errors.append("Unmatched closing parenthesis")
                break
    
    if open_count > 0:
        errors.append("Unmatched opening parenthesis")
    
    # Check for common syntax issues
    if '//' in formula:
        errors.append("Use single '/' for division")
    
    if '**' in formula and '^' in formula:
        errors.append("Use either '**' or '^' for exponentiation, not both")
    
    # Check for empty parentheses
    if '()' in formula:
        errors.append("Empty parentheses found")
    
    # Check for double operators
    double_operators = re.findall(r'[+\-*/]{2,}', formula)
    if double_operators:
        errors.append(f"Double operators found: {', '.join(set(double_operators))}")
    
    return errors


@login_required
def field_form(request, field_id=None):
    """Create or edit a data field"""
    
    if field_id:
        field = get_object_or_404(DataField, id=field_id)
        is_editing = True
    else:
        field = None
        is_editing = False
    
    if request.method == 'POST':
        form = DataFieldForm(request.POST, instance=field)
        if form.is_valid():
            try:
                # Enhanced validation for calculated fields
                if form.cleaned_data.get('category') == 'calculated':
                    formula_errors = validate_calculated_field_formula(
                        form.cleaned_data.get('formula', ''),
                        current_field_id=field_id
                    )
                    if formula_errors:
                        for error in formula_errors:
                            form.add_error('formula', error)
                        # Log validation failure
                        log_activity(
                            request,
                            activity="field_validation_failed",
                            log_type="admin",
                            action="validation_error",
                            extra={
                                'field_name': form.cleaned_data.get('name'),
                                'category': 'calculated',
                                'validation_errors': formula_errors,
                                'formula': form.cleaned_data.get('formula', ''),
                                'is_editing': is_editing,
                            }
                        )
                        # Re-render form with errors
                        context = {
                            'form': form,
                            'field': field,
                            'is_editing': is_editing,
                            'page_title': f"{'Edit' if is_editing else 'Add'} Field",
                        }
                        return render(request, 'council_finance/admin/field_form.html', context)
                
                saved_field = form.save()
                
                action = "edit" if is_editing else "create"
                log_activity(
                    request,
                    activity=f"field_{action}",
                    log_type="admin",
                    action=f"field_{action}d",
                    extra={
                        'field_id': saved_field.id,
                        'field_name': saved_field.name,
                        'field_slug': saved_field.slug,
                        'field_category': saved_field.category,
                        'formula': saved_field.formula,
                        'is_editing': is_editing,
                    }
                )
                
                messages.success(
                    request, 
                    f"Field '{saved_field.name}' {'updated' if is_editing else 'created'} successfully."
                )
                return redirect('field_list')
                
            except ValidationError as e:
                messages.error(request, f"Validation error: {e}")
                log_activity(
                    request,
                    activity="field_save_error",
                    log_type="admin",
                    action="save_error",
                    extra={
                        'error': str(e),
                        'field_name': form.cleaned_data.get('name', 'Unknown'),
                        'is_editing': is_editing,
                    }
                )
            except Exception as e:
                messages.error(request, f"Error saving field: {e}")
                logger.error(f"Error saving field: {e}", exc_info=True)
                log_activity(
                    request,
                    activity="field_save_error",
                    log_type="admin",
                    action="save_error",
                    extra={
                        'error': str(e),
                        'field_name': form.cleaned_data.get('name', 'Unknown') if hasattr(form, 'cleaned_data') else 'Unknown',
                        'is_editing': is_editing,
                    }
                )
    else:
        form = DataFieldForm(instance=field)
    
    # Get councils and years for formula testing - convert to JSON-serializable data
    councils_queryset = Council.objects.all().order_by("name")
    councils_data = [{'slug': c.slug, 'name': c.name} for c in councils_queryset]
    
    years_queryset = list(FinancialYear.objects.order_by("-label"))
    years_data = []
    for y in years_queryset:
        display_label = "Year to Date" if y.label.lower() == "general" else y.label
        years_data.append({'label': y.label, 'display_label': display_label})
    
    import json
    councils_json = json.dumps(councils_data)
    years_json = json.dumps(years_data)
    
    context = {
        'form': form,
        'field': field,
        'is_editing': is_editing,
        'page_title': f"{'Edit' if is_editing else 'Add'} Field",
        'councils_json': councils_json,
        'years_json': years_json,
    }
    
    return render(request, 'council_finance/admin/field_form.html', context)


@login_required
def field_delete(request, field_id):
    """Delete a data field with confirmation"""
    
    field = get_object_or_404(DataField, id=field_id)
    
    if request.method == 'POST':
        try:
            field_name = field.name
            field_slug = field.slug
            field_id_copy = field.id
            
            # Log the deletion before actually deleting
            log_activity(
                request,
                activity="field_delete",
                log_type="admin", 
                action="field_deleted",
                extra={
                    'field_id': field_id_copy,
                    'field_name': field_name,
                    'field_slug': field_slug,
                    'field_category': field.category,
                }
            )
            
            field.delete()
            messages.success(request, f"Field '{field_name}' deleted successfully.")
            return redirect('field_list')
            
        except Exception as e:
            messages.error(request, f"Error deleting field: {e}")
            logger.error(f"Error deleting field {field.id}: {e}", exc_info=True)
            return redirect('field_list')
    
    # Check if field is in use (has associated data)
    from ..models import FinancialFigure, CouncilCharacteristic
    
    financial_usage_count = FinancialFigure.objects.filter(field=field).count()
    characteristic_usage_count = CouncilCharacteristic.objects.filter(field=field).count()
    total_usage = financial_usage_count + characteristic_usage_count
    
    context = {
        'field': field,
        'financial_usage_count': financial_usage_count,
        'characteristic_usage_count': characteristic_usage_count,
        'total_usage': total_usage,
        'has_data': total_usage > 0,
    }
    
    return render(request, 'council_finance/admin/field_delete.html', context)


@login_required
@require_POST
def validate_formula_api(request):
    """
    API endpoint for real-time formula validation.
    
    Accepts:
        - formula: The formula to validate
        - field_id: Optional ID of field being edited (to avoid self-references)
    
    Returns:
        JSON response with validation results
    """
    try:
        formula = request.POST.get('formula', '').strip()
        field_id = request.POST.get('field_id')
        
        if field_id:
            try:
                field_id = int(field_id)
            except (ValueError, TypeError):
                field_id = None
        
        # Validate the formula
        errors = validate_calculated_field_formula(formula, field_id)
        
        response_data = {
            'success': True,
            'valid': len(errors) == 0,
            'errors': errors,
            'formula': formula
        }
        
        # Log validation attempt
        log_activity(
            request,
            activity="formula_validation",
            log_type="admin",
            action="validate_formula",
            extra={
                'formula': formula,
                'field_id': field_id,
                'validation_result': 'valid' if len(errors) == 0 else 'invalid',
                'error_count': len(errors),
                'errors': errors
            }
        )
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in formula validation API: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error during validation'
        }, status=500)


@login_required
def test_formula_api(request):
    """
    API endpoint for testing formula with sample data.
    
    Accepts:
        - formula: The formula to test
        - council_slug: Optional council to test against
        - year: Optional year for financial data
    
    Returns:
        JSON response with test results
    """
    try:
        formula = request.GET.get('formula', '').strip()
        council_slug = request.GET.get('council_slug')
        year = request.GET.get('year')
        
        if not formula:
            return JsonResponse({
                'success': False,
                'error': 'No formula provided'
            })
        
        # First validate the formula
        validation_errors = validate_calculated_field_formula(formula)
        if validation_errors:
            return JsonResponse({
                'success': False,
                'error': 'Formula validation failed',
                'validation_errors': validation_errors
            })
        
        # Try to evaluate the formula with sample data
        test_result = _test_formula_evaluation(formula, council_slug, year)
        
        # Log test attempt
        log_activity(
            request,
            activity="formula_test",
            log_type="admin",
            action="test_formula",
            extra={
                'formula': formula,
                'council_slug': council_slug,
                'year': year,
                'test_successful': test_result.get('success', False),
                'test_result': test_result.get('result')
            }
        )
        
        return JsonResponse(test_result)
        
    except Exception as e:
        logger.error(f"Error in formula testing API: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error during formula testing'
        }, status=500)


def _test_formula_evaluation(formula, council_slug=None, year=None):
    """
    Test formula evaluation with real or sample data.
    
    Args:
        formula (str): The formula to test
        council_slug (str, optional): Council to test against
        year (str, optional): Year for financial data
    
    Returns:
        dict: Test result with success status and result/error
    """
    try:
        # Extract field references from formula using improved field detection
        # Get all existing field names (both variable_name and slug format)
        all_fields = DataField.objects.all()
        existing_field_names = []
        
        for field in all_fields:
            existing_field_names.append(field.variable_name)
            existing_field_names.append(field.slug)
        
        # Sort by length descending to match longer field names first
        existing_field_names.sort(key=len, reverse=True)
        
        field_references = []
        formula_remaining = formula
        
        for field_name in existing_field_names:
            # First try exact word boundary match (works for most cases)
            pattern = r'\b' + re.escape(field_name) + r'\b'
            if re.search(pattern, formula_remaining):
                field_references.append(field_name)
                # Remove this field name from consideration to avoid overlaps
                formula_remaining = re.sub(pattern, '', formula_remaining)
            else:
                # For hyphenated names, try matching surrounded by operators or spaces
                operator_pattern = r'(?:^|[\s\+\-\*/\(\)])'+ re.escape(field_name) + r'(?=[\s\+\-\*/\(\)]|$)'
                if re.search(operator_pattern, formula_remaining):
                    field_references.append(field_name)
                    # Remove this field name from consideration to avoid overlaps
                    formula_remaining = re.sub(operator_pattern, '', formula_remaining)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_field_references = []
        for ref in field_references:
            if ref not in seen:
                seen.add(ref)
                unique_field_references.append(ref)
        
        field_references = unique_field_references
        
        # Get sample values for each referenced field
        field_values = {}
        
        for field_ref in field_references:
            field = None
            
            # Find the field using the same logic as validation
            try:
                field = DataField.objects.get(slug=field_ref)
            except DataField.DoesNotExist:
                try:
                    field = DataField.objects.get(slug=field_ref.replace('_', '-'))
                except DataField.DoesNotExist:
                    var_version = field_ref.replace('-', '_')
                    for f in DataField.objects.all():
                        if f.variable_name == var_version:
                            field = f
                            break
            
            if field:
                # Get sample value
                sample_value = _get_field_sample_value(field, council_slug, year)
                field_values[field_ref] = sample_value
        
        # Create a safe evaluation context
        # Note: In production, you'd want to use a proper expression evaluator
        # This is a simplified version for demonstration
        eval_formula = formula
        for field_ref, value in field_values.items():
            eval_formula = eval_formula.replace(field_ref, str(value))
        
        # Basic mathematical expression evaluation
        # WARNING: Using eval() is dangerous in production - use a proper math parser
        try:
            # Only allow safe mathematical operations
            allowed_chars = set('0123456789+-*/().,')
            if all(c in allowed_chars or c.isspace() for c in eval_formula):
                result = eval(eval_formula)
                return {
                    'success': True,
                    'result': result,
                    'field_values': field_values,
                    'evaluated_formula': eval_formula
                }
            else:
                return {
                    'success': False,
                    'error': 'Formula contains unsafe characters',
                    'field_values': field_values
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Formula evaluation error: {str(e)}',
                'field_values': field_values,
                'evaluated_formula': eval_formula
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Test evaluation error: {str(e)}'
        }


def _get_field_sample_value(field, council_slug=None, year=None):
    """
    Get a sample value for a field, either from real data or generate one.
    
    Args:
        field (DataField): The field to get a sample value for
        council_slug (str, optional): Council to get data from
        year (str, optional): Year for financial data
    
    Returns:
        float: Sample numeric value
    """
    try:
        if council_slug:
            council = Council.objects.get(slug=council_slug)
            
            if field.category == 'characteristic':
                # Get from CouncilCharacteristic
                try:
                    characteristic = CouncilCharacteristic.objects.get(
                        council=council, 
                        field=field
                    )
                    value = characteristic.value
                except CouncilCharacteristic.DoesNotExist:
                    value = None
            else:
                # Get from FinancialFigure
                if year:
                    try:
                        financial_year = FinancialYear.objects.get(label=year)
                        figure = FinancialFigure.objects.get(
                            council=council,
                            field=field,
                            year=financial_year
                        )
                        value = figure.value
                    except (FinancialYear.DoesNotExist, FinancialFigure.DoesNotExist):
                        value = None
                else:
                    value = None
            
            # Convert to numeric if possible
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass
        
        # Generate sample values based on field type
        if field.content_type == 'monetary':
            return 1000000.0  # £1M sample
        elif field.content_type == 'integer':
            return 100.0
        else:
            return 1.0  # Default numeric value
            
    except Exception:
        return 1.0  # Safe fallback
