from django.db import models

from articles.models import Article


class Digest(models.Model):
    generated_at = models.DateTimeField(auto_now_add=True)
    article_count = models.IntegerField(default=0)

    # Uses an explicit through-model (DigestItem) rather than a plain
    # ManyToManyField, because digest_item carries an extra column (rank)
    # beyond the two foreign keys - a plain M2M can't hold that.
    articles = models.ManyToManyField(
        Article, through="DigestItem", related_name="digests"
    )

    def __str__(self):
        return f"Digest #{self.pk} ({self.generated_at})"


class DigestItem(models.Model):
    digest = models.ForeignKey(Digest, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    rank = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["digest", "article"], name="unique_digest_article"
            )
        ]
        ordering = ["rank"]

    def __str__(self):
        return f"{self.digest} - {self.article} (rank {self.rank})"
