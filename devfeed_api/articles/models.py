from django.conf import settings
from django.db import models


class Source(models.Model):
    class SourceType(models.TextChoices):
        API = "api", "API"
        SCRAPE = "scrape", "Scrape"
        RSS = "rss", "RSS"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=SourceType.choices)
    url = models.URLField(max_length=500)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    label = models.CharField(max_length=100, unique=True, db_index=True)

    def __str__(self):
        return self.label


class Article(models.Model):
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, related_name="articles"
    )
    title = models.CharField(max_length=500, db_index=True)
    url = models.URLField(max_length=500, unique=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    raw_score = models.IntegerField(default=0)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # A plain ManyToManyField is enough here since article_tag has no extra
    # columns beyond the two foreign keys - Django creates and manages that
    # join table automatically, no explicit through-model needed.
    tags = models.ManyToManyField(Tag, related_name="articles", blank=True)

    def __str__(self):
        return self.title


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks"
    )
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="bookmarks"
    )
    note = models.CharField(max_length=500, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article"], name="unique_user_article_bookmark"
            )
        ]

    def __str__(self):
        return f"{self.user} saved {self.article}"


class Vote(models.Model):
    class Direction(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes"
    )
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="votes")
    # Nullable so a user can remove their vote entirely (up -> down -> no
    # vote) without deleting and recreating the row, per the design we
    # settled on: one Vote row per user+article, direction switches or
    # clears in place.
    direction = models.CharField(
        max_length=10, choices=Direction.choices, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article"], name="unique_user_article_vote"
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.article} ({self.direction})"
