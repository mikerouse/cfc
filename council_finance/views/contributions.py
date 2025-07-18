import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.template.loader import render_to_string

from council_finance.models import (
    Council,
    FinancialYear,
    FigureSubmission,
    UserProfile,
    Contribution,
    DataField,
    DataIssue,
    ActivityLog,
)

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


def contribute(request):
    """Show a modern, real-time contribute interface with AJAX editing."""
    if request.method == "POST" and request.user.is_superuser and "mark_invalid" in request.POST:
        issue_id = request.POST.get("issue_id")
        DataIssue.objects.filter(id=issue_id).delete()
        return JsonResponse({"status": "ok", "message": "Issue marked invalid and removed."})

    characteristic_qs = (
        DataIssue.objects.filter(issue_type="missing", field__category="characteristic", council__status="active")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )

    financial_qs = (
        DataIssue.objects.filter(issue_type="missing", council__status="active")
        .exclude(field__category="characteristic")
        .select_related("council", "field", "year")
        .order_by("council__name")
    )

    char_paginator = Paginator(characteristic_qs, 25)
    char_page = char_paginator.get_page(1)

    financial_paginator = Paginator(financial_qs, 25)
    financial_page = financial_paginator.get_page(1)

    my_contribs = (
        Contribution.objects.filter(user=request.user).select_related("council", "field")
        if request.user.is_authenticated
        else []
    )

    points = None
    rank = None
    if request.user.is_authenticated:
        profile = request.user.profile
        points = profile.points
        rank = UserProfile.objects.filter(points__gt=points).count() + 1

    financial_years = list(FinancialYear.objects.order_by('-label'))

    return render(
        request,
        "council_finance/contribute_new.html",
        {
            "page_obj": char_page,
            "paginator": char_paginator,
            "missing_financial_page": financial_page,
            "missing_financial_paginator": financial_paginator,
            "my_contribs": my_contribs,
            "points": points,
            "rank": rank,
            "financial_years": financial_years,
        },
    )


@require_GET
def contribute_stats(request):
    """Return statistics for the contribute page sidebar."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")

    missing_total = DataIssue.objects.filter(issue_type='missing', council__status='active').count()
    missing_characteristics = DataIssue.objects.filter(
        issue_type='missing',
        field__category='characteristic',
        council__status='active'
    ).count()
    missing_financial = DataIssue.objects.filter(
        issue_type='missing',
        council__status='active'
    ).exclude(
        field__category='characteristic'
    ).count()

    try:
        from council_finance.smart_data_quality import get_data_collection_priorities
        data_priorities = get_data_collection_priorities()
        relevant_year_ids = {y.id for y in data_priorities.get('relevant_years', [])}
        high_priority_financial = DataIssue.objects.filter(
            issue_type='missing',
            council__status='active',
            year_id__in=relevant_year_ids
        ).exclude(field__category='characteristic').count() if relevant_year_ids else 0
        priority_stats = {
            'high_priority_financial': high_priority_financial,
            'other_financial': missing_financial - high_priority_financial,
            'current_year_label': data_priorities.get('current_year', {}).get('label') if data_priorities.get('current_year') else None,
            'relevant_year_count': len(relevant_year_ids)
        }
    except Exception:
        priority_stats = {
            'high_priority_financial': 0,
            'other_financial': missing_financial,
            'current_year_label': None,
            'relevant_year_count': 0
        }

    stats = {
        'missing': missing_total,
        'missing_characteristics': missing_characteristics,
        'missing_financial': missing_financial,
        'pending': Contribution.objects.filter(status='pending').count(),
        'suspicious': DataIssue.objects.filter(issue_type='suspicious').count(),
        'priority_stats': priority_stats,
    }

    return JsonResponse(stats)


@require_POST
def contribute_submit(request):
    """Handle AJAX contribution submissions from the quick edit modal."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("XHR required")

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)

    try:
        council_id = request.POST.get("council")
        field_slug = request.POST.get("field")
        year_id = request.POST.get("year")
        value = request.POST.get("value", "").strip()

        if not all([council_id, field_slug, value]):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        try:
            council = Council.objects.get(slug=council_id)
        except Council.DoesNotExist:
            return JsonResponse({"error": "Invalid council"}, status=400)

        try:
            field = DataField.objects.get(slug=field_slug)
        except DataField.DoesNotExist:
            return JsonResponse({"error": "Invalid field"}, status=400)

        year = None
        if year_id:
            try:
                year = FinancialYear.objects.get(pk=year_id)
            except FinancialYear.DoesNotExist:
                return JsonResponse({"error": "Invalid year"}, status=400)

        existing = Contribution.objects.filter(
            user=request.user,
            council=council,
            field=field,
            year=year,
            status="pending"
        ).first()

        if existing:
            return JsonResponse({"error": "You already have a pending contribution for this data point"}, status=400)

        contribution = Contribution.objects.create(
            user=request.user,
            council=council,
            field=field,
            year=year,
            value=value,
            ip_address=request.META.get('REMOTE_ADDR'),
            status="pending"
        )

        DataIssue.objects.filter(
            council=council,
            field=field,
            year=year,
            issue_type="missing"
        ).delete()

        log_activity(
            request,
            council=council,
            activity="submit_contribution",
            action=f"submitted {field.name} for {council.name}",
            extra={
                "field_slug": field_slug,
                "year_label": year.label if year else None,
                "value": value,
                "contribution_id": contribution.id
            }
        )

        profile = request.user.profile
        profile.points += 5
        profile.save()

        return JsonResponse({
            "message": f"Contribution submitted successfully for {field.name}",
            "status": "success",
            "contribution_id": contribution.id
        })

    except Exception as e:
        logger.error(f"Error in contribute_submit: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An error occurred while submitting your contribution"}, status=500)


def data_issues_table(request):
    """Return a page of data issues as HTML for the contribute tables."""
    try:
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return HttpResponseBadRequest("XHR required")

        from council_finance.data_quality import assess_data_issues

        issue_type = request.GET.get("type")
        type_mapping = {
            "missing_characteristics": ("missing", "characteristic"),
            "missing_financial": ("missing", "financial"),
            "missing": ("missing", None),
            "suspicious": ("suspicious", None),
            "pending": ("pending", None),
        }

        if not issue_type:
            return HttpResponseBadRequest("missing type parameter")

        if issue_type not in type_mapping:
            return HttpResponseBadRequest(f"invalid type: {issue_type}")

        actual_type, auto_category = type_mapping[issue_type]

        search = request.GET.get("q", "").strip()
        category = request.GET.get("category") or auto_category
        order = request.GET.get("order", "council")
        direction = request.GET.get("dir", "asc")
        allowed = {"council": "council__name", "field": "field__name", "year": "year__label", "value": "value"}
        order_by = allowed.get(order, "council__name")
        if direction == "desc":
            order_by = f"-{order_by}"

        if request.GET.get("refresh"):
            assess_data_issues()

        if actual_type == "pending":
            qs = Contribution.objects.filter(status="pending").select_related("council", "field", "user", "year")
            if search:
                qs = qs.filter(Q(council__name__icontains=search) | Q(field__name__icontains=search))
            qs = qs.order_by(order_by)
        else:
            qs = DataIssue.objects.filter(issue_type=actual_type, council__status="active").select_related("council", "field", "year")
            if category == "characteristic":
                qs = qs.filter(field__category="characteristic")
            elif category == "financial":
                qs = qs.exclude(field__category="characteristic")
            if search:
                qs = qs.filter(Q(council__name__icontains=search) | Q(field__name__icontains=search))
            qs = qs.order_by(order_by)

        page_size = int(request.GET.get("page_size", 50))
        paginator = Paginator(qs, page_size)
        page = paginator.get_page(request.GET.get("page"))

        if actual_type == "pending":
            html = render_to_string(
                "council_finance/pending_table.html",
                {"page_obj": page, "paginator": paginator},
                request=request,
            )
        else:
            show_year = not (actual_type == "missing" and category == "characteristic")
            html = render_to_string(
                "council_finance/data_issues_table_enhanced.html",
                {
                    "page_obj": page,
                    "paginator": paginator,
                    "issue_type": actual_type,
                    "show_year": show_year,
                },
                request=request,
            )

        return JsonResponse({
            "html": html,
            "total": paginator.count,
            "page": page.number,
            "page_size": page_size,
            "num_pages": paginator.num_pages
        })

    except Exception as e:
        import traceback
        return HttpResponseBadRequest(f"error: {str(e)}\n{traceback.format_exc()}")


def moderator_panel(request):
    """Return the moderator side panel HTML with flagged content."""
    if not request.user.is_authenticated or request.user.profile.tier.level < 3:
        return HttpResponseBadRequest("permission denied")

    from council_finance.services.flagging_services import FlaggingService
    from council_finance.models import FlaggedContent

    flagged_content = FlaggingService.get_flagged_content(
        status='open',
        limit=10
    )

    moderation_stats = FlaggingService.get_moderation_stats()

    html = render_to_string(
        "council_finance/moderator_panel.html",
        {
            "flagged_content": flagged_content,
            "moderation_stats": moderation_stats,
            "show_flagged_content": True
        },
        request=request,
    )
    return JsonResponse({"html": html})


def review_contribution(request, pk, action):
    """Review a contribution (approve/reject/delete)."""
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"error": "Authentication required"}, status=401)
        return redirect('login')

    try:
        contribution = get_object_or_404(Contribution, pk=pk)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"error": f"Contribution not found: {str(e)}"}, status=404)
        messages.error(request, "Contribution not found.")
        return redirect('contribute')

    user_can_moderate = request.user.is_superuser
    if hasattr(request.user, 'profile') and request.user.profile:
        try:
            if hasattr(request.user.profile, 'tier') and request.user.profile.tier:
                user_can_moderate = user_can_moderate or request.user.profile.tier.level >= 3
        except Exception:
            pass

    if not user_can_moderate:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"error": "Insufficient permissions"}, status=403)
        messages.error(request, "You don't have permission to moderate contributions.")
        return redirect('contribute')

    try:
        with transaction.atomic():
            if action == 'approve':
                contribution.status = 'approved'
                contribution.save()
                success = _apply_contribution(contribution)
                if success:
                    log_activity(
                        request,
                        activity="contribution_approved",
                        action=f"approved contribution for {contribution.council.name} - {contribution.field.name}",
                        extra={
                            'contribution_id': contribution.id,
                            'council': contribution.council.slug,
                            'field': contribution.field.slug,
                            'old_value': contribution.old_value,
                            'new_value': contribution.value
                        }
                    )
                    message = f"Contribution approved and applied successfully"
                else:
                    message = f"Contribution approved but failed to apply changes"
            elif action == 'reject':
                contribution.status = 'rejected'
                contribution.save()
                log_activity(
                    request,
                    activity="contribution_rejected",
                    action=f"rejected contribution for {contribution.council.name} - {contribution.field.name}",
                    extra={
                        'contribution_id': contribution.id,
                        'council': contribution.council.slug,
                        'field': contribution.field.slug,
                        'reason': request.POST.get('reason', 'No reason provided')
                    }
                )
                message = f"Contribution rejected successfully"
            elif action == 'delete':
                if not request.user.is_superuser:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({"error": "Insufficient permissions to delete"}, status=403)
                    messages.error(request, "You don't have permission to delete contributions.")
                    return redirect('contribute')
                log_activity(
                    request,
                    activity="contribution_deleted",
                    action=f"deleted contribution for {contribution.council.name} - {contribution.field.name}",
                    extra={
                        'contribution_id': contribution.id,
                        'council': contribution.council.slug,
                        'field': contribution.field.slug
                    }
                )
                contribution.delete()
                message = f"Contribution deleted successfully"
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"error": "Invalid action"}, status=400)
                messages.error(request, "Invalid action specified.")
                return redirect('contribute')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"error": f"Error processing contribution: {str(e)}"}, status=500)
        messages.error(request, f"Error processing contribution: {str(e)}")
        return redirect('contribute')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "status": "success",
            "message": message,
            "action": action
        })
    else:
        messages.success(request, message)
        return redirect('contribute')


def _apply_contribution(contribution):
    """Apply an approved contribution to the actual data."""
    try:
        field = contribution.field
        council = contribution.council
        value = contribution.value

        if field.slug == "council_website":
            council.website = value
            council.save()
        elif field.slug == "council_type":
            try:
                from council_finance.models import CouncilType
                council_type = CouncilType.objects.get(id=int(value))
                council.council_type = council_type
                council.save()
            except (ValueError, CouncilType.DoesNotExist):
                return False
        elif field.slug == "council_nation":
            try:
                from council_finance.models import CouncilNation
                council_nation = CouncilNation.objects.get(id=int(value))
                council.council_nation = council_nation
                council.save()
            except (ValueError, CouncilNation.DoesNotExist):
                return False
        elif field.slug == "council_name":
            council.name = value
            council.save()
        else:
            figure, created = FigureSubmission.objects.get_or_create(
                council=council,
                field=field,
                year=contribution.year,
                defaults={'value': value}
            )
            if not created:
                figure.value = value
                figure.save()
        return True
    except Exception as e:
        logger.error(f"Failed to apply contribution {contribution.id}: {str(e)}")
        return False


@require_POST
def submit_contribution(request):
    """Submit a contribution from the enhanced edit modal."""
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "You must be logged in to contribute"}, status=401)

    try:
        council_slug = request.POST.get('council')
        field_slug = request.POST.get('field')
        year_id = request.POST.get('year')
        value = request.POST.get('value', '').strip()
        source = request.POST.get('source', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not all([council_slug, field_slug, value]):
            return JsonResponse({
                "success": False,
                "message": "Council, field, and value are required"
            }, status=400)

        council = get_object_or_404(Council, slug=council_slug)
        field = get_object_or_404(DataField, slug=field_slug)
        year = None
        if year_id and year_id != 'none':
            year = get_object_or_404(FinancialYear, id=year_id)

        existing = Contribution.objects.filter(
            council=council,
            field=field,
            year=year,
            status='pending'
        ).first()

        if existing:
            return JsonResponse({
                "success": False,
                "message": "There is already a pending contribution for this field. Please wait for it to be reviewed."
            }, status=400)

        contribution = Contribution.objects.create(
            council=council,
            field=field,
            year=year,
            value=value,
            source=source if source else None,
            notes=notes if notes else None,
            user=request.user,
            status='approved'
        )

        try:
            _apply_contribution_v2(contribution, request.user, request)
            points = 3 if field.category == "characteristic" else 2
            profile = request.user.profile
            profile.points += points
            profile.approved_submission_count += 1
            profile.save()
            applied_successfully = True
        except Exception as e:
            logger.error(f"Error applying contribution {contribution.id}: {str(e)}")
            applied_successfully = False

        log_activity(
            request,
            activity="submit_contribution",
            action=f"submitted and applied contribution for {field.name}",
            council=council,
            extra={
                'field_slug': field_slug,
                'year_label': year.label if year else None,
                'value': value,
                'contribution_id': contribution.id,
                'applied_successfully': applied_successfully
            }
        )

        from council_finance.notifications import create_notification

        success_message = f"Your contribution for {field.name} has been accepted and applied!"
        if applied_successfully:
            success_message += f" You earned {points} points. Thank you!"
        else:
            success_message += " However, there was an issue applying the data. Moderators will review this."

        create_notification(
            user=request.user,
            title=f"Contribution accepted for {council.name}",
            message=success_message,
            notification_type='contribution_accepted',
            related_object=contribution
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                "success": True,
                "message": success_message,
                "status": "approved",
                "points_awarded": points if applied_successfully else 0
            })

        messages.success(request, success_message)
        return redirect('council_detail', slug=council_slug)

    except Exception as e:
        logger.error(f"Error submitting contribution: {str(e)}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                "success": False,
                "message": "An error occurred while submitting your contribution. Please try again."
            }, status=500)

        messages.error(request, "An error occurred while submitting your contribution. Please try again.")
        return redirect('council_detail', slug=council_slug)


def mark_issue_invalid(request, issue_id):
    """Mark a data issue as invalid."""
    return JsonResponse({"status": "success", "message": "Issue marked invalid"})


__all__ = [
    'contribute',
    'contribute_stats',
    'contribute_submit',
    'data_issues_table',
    'moderator_panel',
    'review_contribution',
    '_apply_contribution',
    'submit_contribution',
    'mark_issue_invalid',
]
