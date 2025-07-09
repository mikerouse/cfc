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
from .models.council_type import CouncilCapability
from .models.user_profile import UserProfile
from .models.user_follow import UserFollow
from .models.council_follow import CouncilFollow
from .models.council_update import (
    CouncilUpdate,
    CouncilUpdateLike,
    CouncilUpdateComment,
)
from .models.trust_tier import TrustTier
from .models.contribution import Contribution
from .models.pending_profile_change import PendingProfileChange
from .models.notification import Notification
from .forms import (
    CounterDefinitionForm,
)
from .models import DataField
from .models.field import PROTECTED_SLUGS
from .models.counter import CounterDefinition, CouncilCounter
from .models.setting import SiteSetting


class CouncilAdmin(admin.ModelAdmin):
    """Custom admin for councils."""

    # Allow admins to manage which counters show on each council via an inline.
    class CouncilCounterInline(admin.TabularInline):
        model = CouncilCounter
        extra = 0

    inlines = [CouncilCounterInline]



class CounterDefinitionAdmin(admin.ModelAdmin):
    """Admin for managing counter definitions."""

    form = CounterDefinitionForm
    list_display = (
        "name",
        "formula",
        "duration",
        "precision",
        "show_currency",
        "friendly_format",
        "show_by_default",
        "headline",
        "display_council_types",
    )
    prepopulated_fields = {"slug": ("name",)}

    def display_council_types(self, obj):
        """List council types associated with this counter."""
        return ", ".join(ct.name for ct in obj.council_types.all()) or "All"
    display_council_types.short_description = "Council types"


# Register core models in the Django admin.
# Using admin.site.register is sufficient for simple use cases.
# Use the custom admin class so staff can import JSON data.
admin.site.register(Council, CouncilAdmin)
admin.site.register(FinancialYear)
admin.site.register(FigureSubmission)
admin.site.register(DebtAdjustment)
admin.site.register(WhistleblowerReport)
admin.site.register(ModerationLog)
class CouncilTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "display_capabilities")

    def display_capabilities(self, obj):
        """Show capabilities for list view."""
        return ", ".join(cap.name for cap in obj.capabilities.all()) or "None"
    display_capabilities.short_description = "Capabilities"


admin.site.register(CouncilType, CouncilTypeAdmin)


class DataFieldAdmin(admin.ModelAdmin):
    # Expose dataset_type in the list display so staff can see which dataset a
    # list field is bound to at a glance.
    list_display = (
        "name",
        "slug",
        "category",
        "content_type",
        "dataset_type",
        "display_council_types",
        "required",
    )
    prepopulated_fields = {"slug": ("name",)}

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.slug in PROTECTED_SLUGS:
            return ("slug",)
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.slug in PROTECTED_SLUGS:
            return False
        return super().has_delete_permission(request, obj)

    def display_council_types(self, obj):
        """Return a comma separated list of associated council types."""
        return ", ".join(ct.name for ct in obj.council_types.all()) or "All"
    display_council_types.short_description = "Council types"


admin.site.register(DataField, DataFieldAdmin)
admin.site.register(UserProfile)
admin.site.register(UserFollow)
admin.site.register(CouncilFollow)
admin.site.register(CouncilUpdate)
admin.site.register(CouncilUpdateLike)
admin.site.register(CouncilUpdateComment)
admin.site.register(PendingProfileChange)
admin.site.register(Notification)
# Manage volunteer trust levels and their submissions
admin.site.register(TrustTier)
admin.site.register(Contribution)
admin.site.register(CounterDefinition, CounterDefinitionAdmin)
admin.site.register(CouncilCounter)
admin.site.register(SiteSetting)
admin.site.register(CouncilCapability)
