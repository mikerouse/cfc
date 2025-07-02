# Django admin registration for finance models
# This file ensures backend users can manage imported data easily via /admin/

from django.contrib import admin

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

# Register core models in the Django admin.
# Using admin.site.register is sufficient for simple use cases.
admin.site.register(Council)
admin.site.register(FinancialYear)
admin.site.register(FigureSubmission)
admin.site.register(DebtAdjustment)
admin.site.register(WhistleblowerReport)
admin.site.register(ModerationLog)
admin.site.register(UserProfile)
admin.site.register(UserFollow)
admin.site.register(PendingProfileChange)
admin.site.register(Notification)
