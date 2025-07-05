from django.conf import settings
from django.db import models

from .council import Council, FinancialYear, FigureSubmission
from .contribution import Contribution
from .field import DataField


class DataChangeLog(models.Model):
    """Record every approved contribution so we can roll back later."""

    contribution = models.ForeignKey(
        Contribution, on_delete=models.SET_NULL, null=True, blank=True
    )
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, null=True, blank=True, on_delete=models.SET_NULL)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def rollback(self):
        """Revert the change stored in this log."""
        if self.field.slug == "council_website":
            self.council.website = self.old_value
            self.council.save()
        elif self.field.slug == "council_type":
            self.council.council_type_id = self.old_value or None
            self.council.save()
        else:
            FigureSubmission.objects.update_or_create(
                council=self.council,
                field=self.field,
                year=self.year,
                defaults={"value": self.old_value, "needs_populating": False},
            )


