from django.db import models

class DataField(models.Model):
    """Definition of a figure/field that can be populated for each council."""

    FIELD_CATEGORIES = [
        ("balance_sheet", "Balance Sheet"),
        ("cash_flow", "Cash Flow"),
        ("income", "Income"),
        ("spending", "Spending"),
        ("general", "General"),
        ("calculated", "Calculated"),
    ]

    CONTENT_TYPES = [
        ("monetary", "Monetary"),
        ("integer", "Integer"),
        ("text", "Text"),
        ("url", "URL"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=FIELD_CATEGORIES, default="general")
    explanation = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default="text")
    formula = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name
