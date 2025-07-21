import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string

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
)
from council_finance.forms import (
    CounterDefinitionForm,
    SiteCounterForm,
    GroupCounterForm,
    DataFieldForm,
)
from council_finance.factoids import previous_year_label

logger = logging.getLogger(__name__)


def log_activity(
    request,
    *,
    council=None,
    activity="",
    log_type="user",
    action="",
    request_data=None,
    response="",
    extra=None,
):
    """Helper to store troubleshooting events using the modern ActivityLog system."""
    import json
    import inspect

    if isinstance(extra, dict) or extra is None:
        extra_data = extra or {}
    else:
        try:
            extra_data = json.loads(extra)
        except Exception:
            extra_data = {"note": str(extra)}

    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller = frame.f_back
        module = caller.f_globals.get("__name__")
        func = caller.f_code.co_name
        cls = None
        if "self" in caller.f_locals:
            cls = caller.f_locals["self"].__class__.__name__
        extra_data.update({
            "module": module,
            "function": func,
        })
        if cls:
            extra_data["class"] = cls

    if request_data is None:
        request_data = request.method
    if isinstance(request_data, dict):
        request_data = json.dumps(request_data, ensure_ascii=False)
    elif request_data is None:
        request_data = ""

    activity_type_mapping = {
        'field_delete': 'delete',
        'apply_contribution': 'contribution',
        'submit_contribution': 'contribution',
        'review_contribution': 'moderation',
        'council_merge': 'council_merge',
        'financial_year': 'financial_year',
        'data_correction': 'data_correction',
    }

    modern_activity_type = activity_type_mapping.get(activity, 'system')

    ActivityLog.log_activity(
        activity_type=modern_activity_type,
        description=f"{activity}: {action}" if action else activity or "Legacy activity",
        user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        related_council=council,
        status='completed',
        details={
            'legacy_data': extra_data,
            'request_method': request_data,
            'response': response,
            'page': request.path,
            'action': action,
        },
        request=request
    )


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

    counter_slug = request.GET.get("counter")
    if not counter_slug:
        return JsonResponse({"error": "Missing counter"}, status=400)
    year_param = request.GET.get("year")
    if year_param and year_param != "all":
        year = (
            FinancialYear.objects.filter(pk=year_param).first()
            if str(year_param).isdigit()
            else FinancialYear.objects.filter(label=year_param).first()
        )
        if not year:
            return JsonResponse({"error": "Invalid data"}, status=400)
        years = [year]
    else:
        years = list(FinancialYear.objects.order_by("-label"))
    counter = CounterDefinition.objects.filter(slug=counter_slug).first()
    if not counter or not years:
        return JsonResponse({"error": "Invalid data"}, status=400)

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


@login_required
@require_GET
def preview_factoid(request):
    """Return the rendered factoid text for a counter, council and year."""
    from council_finance.agents.counter_agent import CounterAgent

    counter_value = request.GET.get("counter")
    council_slug = request.GET.get("council")
    year_label = request.GET.get("year")
    text = request.GET.get("text", "")
    ftype = request.GET.get("type", "")

    if not (counter_value and council_slug and year_label and text):
        return JsonResponse({"error": "Missing data"}, status=400)

    year = FinancialYear.objects.filter(label=year_label).first()
    if not year:
        return JsonResponse({"error": "Invalid year"}, status=400)

    counter = CounterDefinition.objects.filter(slug=counter_value).first()
    if not counter:
        try:
            counter = CounterDefinition.objects.filter(pk=int(counter_value)).first()
        except (TypeError, ValueError):
            counter = None
    if not counter:
        return JsonResponse({"error": "Invalid counter"}, status=400)    # Check if there's any financial data for this council and year
    if not FinancialFigure.objects.filter(council__slug=council_slug, year=year).exists():
        return JsonResponse({"error": "No data for the selected year"}, status=400)

    agent = CounterAgent()
    values = agent.run(council_slug=council_slug, year_label=year.label)
    result = values.get(counter.slug)
    if not result or result.get("value") in (None, ""):
        return JsonResponse({"error": "No data for the selected year"}, status=400)

    value_str = result.get("formatted")
    if ftype == "percent_change":
        prev_label = previous_year_label(year.label)
        prev_value = None
        if prev_label:
            prev_year = FinancialYear.objects.filter(label=prev_label).first()
            if prev_year:
                prev_values = agent.run(council_slug=council_slug, year_label=prev_year.label)
                prev = prev_values.get(counter.slug)
                if prev:
                    prev_value = prev.get("value")
        if prev_value in (None, ""):
            return JsonResponse({"error": "No previous data to compare"}, status=400)
        try:
            change = (float(result.get("value")) - float(prev_value)) / float(prev_value) * 100
            value_str = f"{change:.1f}%"
        except Exception:
            return JsonResponse({"error": "No previous data to compare"}, status=400)

    class SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    rendered = text.format_map(SafeDict(value=value_str))
    return JsonResponse({"text": rendered})


def field_list(request):
    """List all data fields for management."""
    if not request.user.is_authenticated:
        return redirect('login')

    fields = DataField.objects.all().prefetch_related('council_types').order_by('category', 'name')
    categories = DataField.FIELD_CATEGORIES

    context = {
        'title': 'Fields & Characteristics Manager',
        'fields': fields,
        'categories': categories,
    }

    log_activity(
        request,
        activity="field_list_view",
        action="viewed field management page",
        extra={'field_count': fields.count()}
    )

    return render(request, "council_finance/field_list.html", context)


def field_form(request, slug=None):
    """Create or edit a data field."""
    if not request.user.is_authenticated:
        return redirect('login')

    field = None
    is_edit = False
    if slug:
        field = get_object_or_404(DataField, slug=slug)
        is_edit = True

    if request.method == 'POST':
        form = DataFieldForm(request.POST, instance=field)
        if form.is_valid():
            field = form.save()

            action = "updated" if is_edit else "created"
            messages.success(request, f'Field "{field.name}" {action} successfully.')

            log_activity(
                request,
                activity="field_form",
                action=f"{action} field: {field.slug}",
                extra={'field_name': field.name, 'field_category': field.category}
            )

            return redirect('field_list')
    else:
        form = DataFieldForm(instance=field)

    context = {
        'title': f'{"Edit" if is_edit else "Add"} Field',
        'form': form,
        'field': field,
        'is_edit': is_edit,
    }

    return render(request, "council_finance/field_form.html", context)


def field_delete(request, slug):
    """Delete a data field."""
    if not request.user.is_authenticated:
        return redirect('login')

    field = get_object_or_404(DataField, slug=slug)

    if field.is_protected:
        messages.error(request, f'Field "{field.name}" is protected and cannot be deleted.')
        return redirect('field_list')

    if request.method == 'POST':
        try:
            field_name = field.name
            field.delete()
            messages.success(request, f'Field "{field_name}" deleted successfully.')

            log_activity(
                request,
                activity="field_delete",
                action=f"deleted field: {slug}",
                extra={'field_name': field_name}
            )

            return JsonResponse({"status": "success", "message": f"Field '{field_name}' deleted successfully"})
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error deleting field {slug}: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred while deleting the field"}, status=500)

    context = {
        'title': f'Delete Field: {field.name}',
        'field': field,
    }

    return render(request, "council_finance/field_delete.html", context)


def factoid_list(request):
    """List all factoids for management."""
    return render(request, "council_finance/factoid_list.html", {})


def factoid_form(request, slug=None):
    """Create or edit a factoid."""
    return render(request, "council_finance/factoid_form.html", {})


def factoid_delete(request, slug):
    """Delete a factoid."""
    return JsonResponse({"status": "success", "message": "Factoid deleted"})


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
                    # Set new current year
                    year = FinancialYear.objects.get(id=year_id)
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
        
        elif 'create_council' in request.POST:
            council_name = request.POST.get('council_name', '').strip()
            council_slug = request.POST.get('council_slug', '').strip()
            council_type = request.POST.get('council_type', '').strip()
            council_nation = request.POST.get('council_nation', '').strip()
            
            if council_name:
                try:
                    from django.utils.text import slugify
                    # Auto-generate slug if not provided
                    if not council_slug:
                        council_slug = slugify(council_name)
                    
                    # Check if council already exists
                    if Council.objects.filter(Q(name=council_name) | Q(slug=council_slug)).exists():
                        messages.error(request, f"Council with name '{council_name}' or slug '{council_slug}' already exists")
                    else:
                        # Create the council
                        council = Council.objects.create(
                            name=council_name,
                            slug=council_slug,
                            council_type=council_type if council_type else None,
                            status='active'
                        )
                        
                        # Set nation if provided
                        if council_nation:
                            from council_finance.models import CouncilNation
                            try:
                                nation = CouncilNation.objects.get(slug=council_nation)
                                council.council_nation = nation
                                council.save()
                            except CouncilNation.DoesNotExist:
                                pass  # Nation doesn't exist, skip it
                        
                        # Generate missing data issues for the new council
                        try:
                            issues_created = generate_missing_data_issues_for_council(council)
                            messages.success(request, f"Council '{council_name}' created successfully with {issues_created} data contribution opportunities added to queues")
                        except Exception as e:
                            # Council was created successfully, but data issue generation failed
                            messages.success(request, f"Council '{council_name}' created successfully")
                            messages.warning(request, f"Note: Could not auto-generate contribution queue entries: {str(e)}")
                        
                        # Log the activity
                        log_activity(
                            request,
                            council=council,
                            activity='council_creation',
                            action='Created new council',
                            extra=f"Council: {council_name}, Slug: {council_slug}, Type: {council_type}"
                        )
                        
                except Exception as e:
                    messages.error(request, f"Error creating council: {str(e)}")
            else:
                messages.error(request, "Council name is required")
            return HttpResponseRedirect(reverse('god_mode'))
        
        elif 'import_councils' in request.POST:
            import_file = request.FILES.get('council_import_file')
            preview_import = request.POST.get('preview_import') == '1'
            
            if import_file:
                try:
                    import pandas as pd
                    import json
                    
                    # Read the file based on its type
                    if import_file.name.endswith('.csv'):
                        df = pd.read_csv(import_file)
                    elif import_file.name.endswith('.xlsx'):
                        df = pd.read_excel(import_file)
                    elif import_file.name.endswith('.json'):
                        data = json.load(import_file)
                        df = pd.DataFrame(data)
                    else:
                        messages.error(request, "Unsupported file format. Please use CSV, Excel, or JSON.")
                        return HttpResponseRedirect(reverse('god_mode'))
                    
                    # Validate required columns
                    required_columns = ['name']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        messages.error(request, f"Missing required columns: {', '.join(missing_columns)}")
                        return HttpResponseRedirect(reverse('god_mode'))
                    
                    if preview_import:
                        # Preview mode - show what would be imported
                        preview_data = df.head(10).to_dict('records')
                        request.session['import_preview'] = {
                            'data': preview_data,
                            'total_rows': len(df)
                        }
                        messages.info(request, f"Preview: {len(df)} councils would be imported. Review the data and import again without preview to proceed.")
                    else:
                        # Import mode
                        from django.utils.text import slugify
                        created_count = 0
                        skipped_count = 0
                        total_issues_created = 0
                        new_councils = []
                        
                        for _, row in df.iterrows():
                            council_name = str(row['name']).strip()
                            council_slug = slugify(row.get('slug', council_name))
                            
                            # Check if council already exists
                            if not Council.objects.filter(Q(name=council_name) | Q(slug=council_slug)).exists():
                                council = Council.objects.create(
                                    name=council_name,
                                    slug=council_slug,
                                    council_type=row.get('council_type', ''),
                                    status='active'
                                )
                                
                                # Set additional fields if provided
                                if 'website' in row and pd.notna(row['website']):
                                    council.website = str(row['website'])
                                if 'postcode' in row and pd.notna(row['postcode']):
                                    council.postcode = str(row['postcode'])
                                if 'population' in row and pd.notna(row['population']):
                                    try:
                                        council.population = int(row['population'])
                                    except (ValueError, TypeError):
                                        pass
                                
                                council.save()
                                new_councils.append(council)
                                created_count += 1
                            else:
                                skipped_count += 1
                        
                        # Generate missing data issues for all new councils
                        if new_councils:
                            try:
                                for council in new_councils:
                                    issues_created = generate_missing_data_issues_for_council(council)
                                    total_issues_created += issues_created
                                messages.success(request, f"Import complete: {created_count} councils created, {skipped_count} skipped (already exist), {total_issues_created} data contribution opportunities added to queues")
                            except Exception as e:
                                messages.success(request, f"Import complete: {created_count} councils created, {skipped_count} skipped (already exist)")
                                messages.warning(request, f"Note: Could not auto-generate all contribution queue entries: {str(e)}")
                        else:
                            messages.success(request, f"Import complete: {created_count} councils created, {skipped_count} skipped (already exist)")
                        
                        # Log the import activity
                        log_activity(
                            request,
                            activity='bulk_council_import',
                            action='Imported councils from file',
                            extra=f"File: {import_file.name}, Created: {created_count}, Skipped: {skipped_count}"
                        )
                        
                except ImportError:
                    messages.error(request, "pandas library not available. Please install it to use the import feature.")
                except Exception as e:
                    messages.error(request, f"Error importing councils: {str(e)}")
            else:
                messages.error(request, "Please select a file to import")
            return HttpResponseRedirect(reverse('god_mode'))
        
        elif 'cleanup_duplicate_councils' in request.POST:
            try:
                from django.db import transaction
                duplicates_removed = 0
                
                # Find duplicate councils by name (case-insensitive)
                council_names = Council.objects.values_list('name', flat=True)
                seen_names = set()
                
                with transaction.atomic():
                    for council in Council.objects.all().order_by('id'):
                        name_lower = council.name.lower()
                        if name_lower in seen_names:
                            # This is a duplicate - check if it has any data
                            has_characteristics = council.characteristics.exists()
                            has_financial_figures = council.financial_figures.exists()
                            
                            if not has_characteristics and not has_financial_figures:
                                council.delete()
                                duplicates_removed += 1
                        else:
                            seen_names.add(name_lower)
                
                if duplicates_removed > 0:
                    messages.success(request, f"Cleanup complete: {duplicates_removed} duplicate councils removed")
                else:
                    messages.info(request, "No duplicate councils found or all duplicates have associated data")
                    
                # Log the cleanup activity
                log_activity(
                    request,
                    activity='duplicate_cleanup',
                    action='Cleaned up duplicate councils',
                    extra=f"Removed: {duplicates_removed} councils"
                )
                
            except Exception as e:
                messages.error(request, f"Error during cleanup: {str(e)}")
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
    'preview_factoid',
    'field_list',
    'field_form',
    'field_delete',
    'factoid_list',
    'factoid_form',
    'factoid_delete',
    'god_mode',
    'activity_log_entries',
    'activity_log_json',
]
