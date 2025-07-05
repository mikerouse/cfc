from django.conf import settings
from django.db import models

from .council import Council, FinancialYear
from .field import DataField
from .contribution import Contribution

class RejectionLog(models.Model):
    """Store details whenever a contribution is rejected."""

    REASONS = [
        ("data_incorrect", "The data wasn't correct"),
        ("no_sources", "We can't find reliable sources"),
        ("invalid_field", "Invalid field"),
        ("other", "Other"),
    ]

    contribution = models.ForeignKey(
        Contribution, on_delete=models.SET_NULL, null=True, blank=True
    )
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    # Field may be null when logging issues like invalid field slugs
    field = models.ForeignKey(DataField, on_delete=models.CASCADE, null=True, blank=True)
    year = models.ForeignKey(FinancialYear, null=True, blank=True, on_delete=models.SET_NULL)
    value = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.CharField(max_length=50, choices=REASONS)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"Rejected contribution {self.contribution_id} for {self.council}"
