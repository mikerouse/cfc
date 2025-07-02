# Django admin registration for finance models
# This file ensures backend users can manage imported data easily via /admin/

from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
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
from .models.user_profile import UserProfile
from .models.user_follow import UserFollow
from .models.pending_profile_change import PendingProfileChange
from .models.notification import Notification
from .forms import CouncilImportForm

class CouncilAdmin(admin.ModelAdmin):
    """Custom admin with a JSON import helper."""

    def get_urls(self):
        # Add an extra URL pointing to our import view
        urls = super().get_urls()
        custom = [
            path(
                "import-json/",
                self.admin_site.admin_view(self.import_json),
                name="council_finance_council_import",
            ),
        ]
        return custom + urls

    def import_json(self, request):
        """Handle upload and creation of council data."""
        if request.method == "POST":
            form = CouncilImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    data = json.load(form.cleaned_data["json_file"])
                except json.JSONDecodeError:
                    form.add_error("json_file", "Invalid JSON file")
                else:
                    # Loop through each council record mirroring ImporterAgent
                    for council_data in data.get("councils", []):
                        council, _ = Council.objects.get_or_create(
                            slug=council_data["slug"],
                            defaults={
                                "name": council_data.get("name", ""),
                                "website": council_data.get("website", ""),
                                "council_type": council_data.get("council_type", ""),
                            },
                        )
                        for field, year_map in council_data.get("values", {}).items():
                            for year_label, value in year_map.items():
                                fy, _ = FinancialYear.objects.get_or_create(label=year_label)
                                FigureSubmission.objects.update_or_create(
                                    council=council,
                                    year=fy,
                                    field_name=field,
                                    defaults={"value": value},
                                )
                    messages.success(request, "Council data imported successfully.")
                    return redirect("admin:council_finance_council_changelist")
        else:
            form = CouncilImportForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
        }
        return render(request, "admin/council_finance/council/import_json.html", context)

# Register core models in the Django admin.
# Using admin.site.register is sufficient for simple use cases.
# Use the custom admin class so staff can import JSON data.
admin.site.register(Council, CouncilAdmin)
admin.site.register(FinancialYear)
admin.site.register(FigureSubmission)
admin.site.register(DebtAdjustment)
admin.site.register(WhistleblowerReport)
admin.site.register(ModerationLog)
admin.site.register(UserProfile)
admin.site.register(UserFollow)
admin.site.register(PendingProfileChange)
admin.site.register(Notification)
