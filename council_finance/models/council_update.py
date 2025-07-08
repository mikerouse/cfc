from django.conf import settings
from django.db import models

from .council import Council


class CouncilUpdate(models.Model):
    """Newsfeed item about a council."""

    council = models.ForeignKey(Council, related_name="updates", on_delete=models.CASCADE)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Update for {self.council}: {self.message[:50]}"


class CouncilUpdateLike(models.Model):
    """Keep track of which users liked an update."""

    update = models.ForeignKey(CouncilUpdate, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("update", "user")

    def __str__(self) -> str:
        return f"{self.user} likes {self.update_id}"


class CouncilUpdateComment(models.Model):
    """User comment on an update."""

    update = models.ForeignKey(CouncilUpdate, related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Comment by {self.user}"
