from django.db import models

class CouncilNation(models.Model):
    """Represents the UK nation a council belongs to."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Council nation"
        verbose_name_plural = "Council nations"

    def __str__(self) -> str:
        return self.name
