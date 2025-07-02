# Django admin registration for finance models
# This file ensures backend users can manage imported data easily via /admin/

from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
import json

from .models.council import (
    Council,
    FinancialYear,
    FigureSubmission,
    DebtAdjustment,
    WhistleblowerReport,
    ModerationLog,
)
from .models.council_type import CouncilType
from .models.user_profile import UserProfile
from .models.user_follow import UserFollow
from .models.pending_profile_change import PendingProfileChange
from .models.notification import Notification
from .forms import (
    CouncilImportForm,
    CouncilImportMappingForm,
    INTERNAL_FIELDS,
    CounterDefinitionForm,
)
from .models.counter import CounterDefinition, CouncilCounter

class CouncilAdmin(admin.ModelAdmin):
    """Custom admin with a JSON import helper."""

    # Use a custom change list template so we can expose a link to the
    # import view directly from the council list page.
    change_list_template = "admin/council_finance/council/change_list.html"
    # Allow admins to manage which counters show on each council via an inline.
    class CouncilCounterInline(admin.TabularInline):
        model = CouncilCounter
        extra = 0

    inlines = [CouncilCounterInline]

    def get_urls(self):
        # Add extra URLs pointing to the import flow and progress endpoint.
        urls = super().get_urls()
        custom = [
            path(
                "import-json/",
                self.admin_site.admin_view(self.import_json),
                name="council_finance_council_import",
            ),
            path(
                "import-json/progress/",
                self.admin_site.admin_view(self.import_progress),
                name="council_finance_council_import_progress",
            ),
        ]
        return custom + urls

    def import_json(self, request):
        """Multi-step JSON import with optional field mapping."""
        if request.method == "POST" and request.POST.get("step") == "upload":
            form = CouncilImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    data = json.load(form.cleaned_data["json_file"])
                except json.JSONDecodeError:
                    form.add_error("json_file", "Invalid JSON file")
                else:
                    request.session["import_data"] = data
                    fields = [f["name"] for f in data.get("fields", [])]
                    map_form = CouncilImportMappingForm(available_fields=fields)
                    context = {**self.admin_site.each_context(request), "map_form": map_form}
                    return render(request, "admin/council_finance/council/import_map.html", context)
        elif request.method == "POST" and request.POST.get("step") == "map":
            data = request.session.get("import_data", {})
            fields = [f["name"] for f in data.get("fields", [])]
            map_form = CouncilImportMappingForm(request.POST, available_fields=fields)
            if map_form.is_valid():
                request.session["import_mapping"] = {k: v for k, v in map_form.cleaned_data.items() if v}
                request.session["import_index"] = 0
                total = len(data.get("councils", []))
                context = {**self.admin_site.each_context(request), "total": total}
                return render(request, "admin/council_finance/council/import_progress.html", context)

        form = CouncilImportForm()
        context = {**self.admin_site.each_context(request), "form": form}
        return render(request, "admin/council_finance/council/import_upload.html", context)

    def import_progress(self, request):
        """Process a single council and return JSON progress."""
        data = request.session.get("import_data", {})
        mapping = request.session.get("import_mapping", {})
        index = request.session.get("import_index", 0)

        councils = data.get("councils", [])
        total = len(councils)
        if index >= total:
            request.session.pop("import_data", None)
            request.session.pop("import_mapping", None)
            request.session.pop("import_index", None)
            return JsonResponse({"complete": True})

        council_data = councils[index]
        council_type_name = council_data.get("council_type", "")
        council_type = None
        if council_type_name:
            council_type, _ = CouncilType.objects.get_or_create(name=council_type_name)

        council, _ = Council.objects.get_or_create(
            slug=council_data["slug"],
            defaults={
                "name": council_data.get("name", ""),
                "website": council_data.get("website", ""),
                "council_type": council_type,
            },
        )

        for field, year_map in council_data.get("values", {}).items():
            mapped = mapping.get(field) or field
            if mapped not in INTERNAL_FIELDS:
                continue
            for year_label, value in year_map.items():
                fy, _ = FinancialYear.objects.get_or_create(label=year_label)
                FigureSubmission.objects.update_or_create(
                    council=council,
                    year=fy,
                    field_name=mapped,
                    defaults={"value": value},
                )

        request.session["import_index"] = index + 1
        return JsonResponse({"complete": False, "processed": index + 1, "total": total})


class CounterDefinitionAdmin(admin.ModelAdmin):
    """Admin for managing counter definitions."""

    form = CounterDefinitionForm
    list_display = ("name", "formula", "duration")
    prepopulated_fields = {"slug": ("name",)}

# Register core models in the Django admin.
# Using admin.site.register is sufficient for simple use cases.
# Use the custom admin class so staff can import JSON data.
admin.site.register(Council, CouncilAdmin)
admin.site.register(FinancialYear)
admin.site.register(FigureSubmission)
admin.site.register(DebtAdjustment)
admin.site.register(WhistleblowerReport)
admin.site.register(ModerationLog)
admin.site.register(CouncilType)
admin.site.register(UserProfile)
admin.site.register(UserFollow)
admin.site.register(PendingProfileChange)
admin.site.register(Notification)
admin.site.register(CounterDefinition, CounterDefinitionAdmin)
admin.site.register(CouncilCounter)
