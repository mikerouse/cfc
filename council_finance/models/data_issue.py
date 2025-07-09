from django.db import models

from .council import Council, FinancialYear
from .field import DataField


class DataIssue(models.Model):
    """Record missing or suspicious data points for review."""

    ISSUE_TYPES = [
        ("missing", "Missing"),
        ("suspicious", "Suspicious"),
    ]

    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, null=True, blank=True, on_delete=models.SET_NULL)
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    value = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("council", "field", "year", "issue_type")
        ordering = ["council__name", "field__name"]

    def __str__(self) -> str:
        return f"{self.get_issue_type_display()} for {self.council} {self.field} {self.year or ''}".strip()
