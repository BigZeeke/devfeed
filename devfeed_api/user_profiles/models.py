from django.conf import settings
from django.db import models


class UserKeyword(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="keyword_preferences",
    )
    keyword = models.CharField(max_length=100)
    weight = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "keyword"], name="unique_user_keyword"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.keyword} ({self.weight})"
