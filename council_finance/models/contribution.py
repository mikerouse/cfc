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
    edited = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"Contribution by {self.user} for {self.council}"

    @property
    def old_value(self) -> str:
        """Fetch the current value before this contribution is applied."""
        if self.field.slug == "council_website":
            return self.council.website or ""
        if self.field.slug == "council_type":
            return self.council.council_type_id or ""
        if self.field.slug == "council_nation":
            return self.council.council_nation_id or ""
        from .council import FigureSubmission

        fs = FigureSubmission.objects.filter(
            council=self.council, field=self.field, year=self.year
        ).first()
        return fs.value if fs else ""

    @property
    def display_old_value(self) -> str:
        """Old value rendered using the field helper."""
        return self.field.display_value(self.old_value)

    @property
    def display_new_value(self) -> str:        return self.field.display_value(self.value)