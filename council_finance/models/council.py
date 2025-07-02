from django.db import models

# The CouncilType model lives in a separate module so it can be edited
# independently in the admin. We import lazily to avoid circular imports
# when Django loads models during migrations.
from .council_type import CouncilType

class Council(models.Model):
    """Basic local authority info."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)
    # Link to a CouncilType so the admin form can offer a drop-down list and
    # staff can manage available types.
    council_type = models.ForeignKey(
        CouncilType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

class FinancialYear(models.Model):
    """Represents a financial year label (e.g. 2023/24)."""
    label = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.label

class FigureSubmission(models.Model):
    """Stores individual financial figures for a council in a given year."""
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    # Track when the figure value is missing so staff can easily find gaps
    # in the data and populate them later. A blank or null ``value`` will
    # automatically set this flag via imports and migrations.
    needs_populating = models.BooleanField(
        default=False,
        help_text="True if the source dataset did not provide this value",
    )

    class Meta:
        unique_together = ('council', 'year', 'field_name')

class DebtAdjustment(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

class WhistleblowerReport(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

class ModerationLog(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
