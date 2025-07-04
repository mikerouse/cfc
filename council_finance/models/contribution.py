from django.conf import settings
from django.db import models

from .council import Council, FinancialYear
from .field import DataField

class Contribution(models.Model):
    """Volunteer submitted data awaiting approval.

    Each contribution links a user to a particular council and data
    field. Depending on the submitter's trust tier the contribution
    may be auto-approved or require moderation.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, null=True, blank=True, on_delete=models.SET_NULL)
    value = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"Contribution by {self.user} for {self.council}"
