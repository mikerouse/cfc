import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET
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
    Factoid,
    FactoidTemplate,
    FactoidPlaylist,
    PlaylistItem,
)
from council_finance.forms import (
    CounterDefinitionForm,
    SiteCounterForm,
    GroupCounterForm,
    DataFieldForm,
)
from council_finance.factoids import previous_year_label
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


def factoid_template_list(request):
    """List all factoid templates for management."""
    templates = FactoidTemplate.objects.all().order_by('-priority', 'name')
    search_query = request.GET.get('search', '')
    if search_query:
        templates = templates.filter(
            Q(name__icontains=search_query) | 
            Q(template_text__icontains=search_query) |
            Q(factoid_type__icontains=search_query)
        )
    
    type_filter = request.GET.get('type', '')
    if type_filter:
        templates = templates.filter(factoid_type=type_filter)
    
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    templates_page = paginator.get_page(page_number)
    
    context = {
        'templates': templates_page,
        'search_query': search_query,
        'type_filter': type_filter,
        'factoid_types': FactoidTemplate.FACTOID_TYPES,
    }
    return render(request, "council_finance/factoid_template_list.html", context)


def factoid_template_form(request, slug=None):
    """Create or edit a factoid template."""
    template = None
    if slug:
        template = get_object_or_404(FactoidTemplate, slug=slug)
    
    if request.method == 'POST':
        try:
            if template:
                # Update existing template
                template.name = request.POST['name']
                template.factoid_type = request.POST['factoid_type']
                template.template_text = request.POST['template_text']
                template.emoji = request.POST.get('emoji', '')
                template.color_scheme = request.POST['color_scheme']
                template.animation_duration = int(request.POST.get('animation_duration', 5000))
                template.flip_animation = request.POST.get('flip_animation') == 'on'
                template.priority = int(request.POST.get('priority', 0))
                template.min_value = request.POST.get('min_value') or None
                template.max_value = request.POST.get('max_value') or None
                template.requires_previous_year = request.POST.get('requires_previous_year') == 'on'
                template.is_active = request.POST.get('is_active') == 'on'
                template.save()
                
                # Handle many-to-many relationships
                counters = request.POST.getlist('counters')
                template.counters.set(CounterDefinition.objects.filter(id__in=counters))
                
                council_types = request.POST.getlist('council_types')
                template.council_types.set(council_types)
                
                messages.success(request, f'Factoid template "{template.name}" updated successfully.')
                log_activity(request.user, 'factoid_template_updated', 'FactoidTemplate', template.id)
            else:
                # Create new template
                template = FactoidTemplate.objects.create(
                    name=request.POST['name'],
                    factoid_type=request.POST['factoid_type'],
                    template_text=request.POST['template_text'],
                    emoji=request.POST.get('emoji', ''),
                    color_scheme=request.POST['color_scheme'],
                    animation_duration=int(request.POST.get('animation_duration', 5000)),
                    flip_animation=request.POST.get('flip_animation') == 'on',
                    priority=int(request.POST.get('priority', 0)),
                    min_value=request.POST.get('min_value') or None,
                    max_value=request.POST.get('max_value') or None,
                    requires_previous_year=request.POST.get('requires_previous_year') == 'on',
                    is_active=request.POST.get('is_active', True) == 'on'
                )
                
                # Handle many-to-many relationships
                counters = request.POST.getlist('counters')
                template.counters.set(CounterDefinition.objects.filter(id__in=counters))
                
                council_types = request.POST.getlist('council_types')
                template.council_types.set(council_types)
                
                messages.success(request, f'Factoid template "{template.name}" created successfully.')
                log_activity(request.user, 'factoid_template_created', 'FactoidTemplate', template.id)
            
            return redirect('factoid_template_list')
        
        except (ValueError, ValidationError) as e:
            messages.error(request, f'Error saving factoid template: {str(e)}')
    
    # Get all available counters and council types for form
    counters = CounterDefinition.objects.all().order_by('name')
    from council_finance.models import CouncilType
    council_types = CouncilType.objects.all().order_by('name')
    
    context = {
        'template': template,
        'counters': counters,
        'council_types': council_types,
        'factoid_types': FactoidTemplate.FACTOID_TYPES,
        'color_schemes': FactoidTemplate.COLOR_SCHEMES,
    }
    return render(request, "council_finance/factoid_template_form.html", context)


def factoid_template_delete(request, slug):
    """Delete a factoid template."""
    template = get_object_or_404(FactoidTemplate, slug=slug)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'Factoid template "{template_name}" deleted successfully.')
        log_activity(request.user, 'factoid_template_deleted', 'FactoidTemplate', None)
        return redirect('factoid_template_list')
    
    context = {'template': template}
    return render(request, "council_finance/factoid_template_delete.html", context)


def factoid_playlist_list(request):
    """List factoid playlists for management."""
    playlists = FactoidPlaylist.objects.select_related(
        'counter', 'council', 'year'
    ).prefetch_related('factoid_templates').all().order_by('-last_computed')
    
    search_query = request.GET.get('search', '')
    if search_query:
        playlists = playlists.filter(
            Q(counter__name__icontains=search_query) |
            Q(council__name__icontains=search_query) |
            Q(year__label__icontains=search_query)
        )
    
    paginator = Paginator(playlists, 20)
    page_number = request.GET.get('page')
    playlists_page = paginator.get_page(page_number)
    
    context = {
        'playlists': playlists_page,
        'search_query': search_query,
    }
    return render(request, "council_finance/factoid_playlist_list.html", context)


def factoid_playlist_regenerate(request, playlist_id):
    """Force regeneration of a factoid playlist."""
    playlist = get_object_or_404(FactoidPlaylist, id=playlist_id)
    
    if request.method == 'POST':
        from council_finance.factoid_engine import FactoidEngine
        
        engine = FactoidEngine()
        try:
            factoids = engine.generate_factoid_playlist(
                playlist.counter.slug,
                playlist.council.slug if playlist.council else None,
                playlist.year.label
            )
            messages.success(request, f'Playlist regenerated with {len(factoids)} factoids.')
            log_activity(request.user, 'factoid_playlist_regenerated', 'FactoidPlaylist', playlist.id)
        except Exception as e:
            messages.error(request, f'Error regenerating playlist: {str(e)}')
    
    return redirect('factoid_playlist_list')


# Legacy factoid views for backward compatibility
def factoid_list(request):
    """List legacy factoids for management."""
    factoids = Factoid.objects.all().order_by('name')
    context = {'factoids': factoids}
    return render(request, "council_finance/factoid_list.html", context)


def factoid_form(request, slug=None):
    """Create or edit a legacy factoid."""
    factoid = None
    if slug:
        factoid = get_object_or_404(Factoid, slug=slug)
    
    context = {'factoid': factoid}
    return render(request, "council_finance/factoid_form.html", context)


def factoid_delete(request, slug):
    """Delete a legacy factoid."""
    factoid = get_object_or_404(Factoid, slug=slug)
    if request.method == 'POST':
        factoid_name = factoid.name
        factoid.delete()
        messages.success(request, f'Legacy factoid "{factoid_name}" deleted.')
        return redirect('factoid_list')
    
    context = {'factoid': factoid}
    return render(request, "council_finance/factoid_delete.html", context)


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
    'preview_factoid',
    'field_list',
    'field_form',
    'field_delete',
    'factoid_template_list',
    'factoid_template_form',
    'factoid_template_delete',
    'factoid_playlist_list',
    'factoid_playlist_regenerate',
    'factoid_list',
    'factoid_form',
    'factoid_delete',
    'god_mode',
    'activity_log_entries',
    'activity_log_json',
]
