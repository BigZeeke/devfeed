from rest_framework import serializers

from articles.models import Article, Bookmark, Source, Tag


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ["id", "name", "type", "url", "active"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "label"]


class ArticleSerializer(serializers.ModelSerializer):
    # Read-only nested representation - a GET returns full tag objects
    # (id + label), not just IDs the client would have to look up.
    tags = TagSerializer(many=True, read_only=True)

    # Write-only field accepting plain tag label strings. create()/update()
    # below get_or_create's a Tag row per label, so a client can attach
    # tags without knowing or pre-creating Tag IDs.
    tag_labels = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
    )

    # Convenience read-only field so a client showing an article list
    # doesn't need a second request just to display which source it's from.
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "source",
            "source_name",
            "title",
            "url",
            "published_at",
            "raw_score",
            "is_read",
            "created_at",
            "tags",
            "tag_labels",
        ]

    def create(self, validated_data):
        tag_labels = validated_data.pop("tag_labels", [])
        article = Article.objects.create(**validated_data)
        self._apply_tag_labels(article, tag_labels)
        return article

    def update(self, instance, validated_data):
        tag_labels = validated_data.pop("tag_labels", None)
        for field_name, field_value in validated_data.items():
            setattr(instance, field_name, field_value)
        instance.save()

        if tag_labels is not None:
            self._apply_tag_labels(instance, tag_labels)

        return instance

    def _apply_tag_labels(self, article, tag_labels):
        tags = []
        for label in tag_labels:
            tag, _ = Tag.objects.get_or_create(label=label)
            tags.append(tag)
        article.tags.set(tags)


class BookmarkSerializer(serializers.ModelSerializer):
    # The owner always comes from the logged-in user, never from the request
    # body. HiddenField keeps "user" out of the input and the output, but DRF
    # still sees it during validation, so the unique user+article constraint
    # is checked here and a duplicate returns 400 instead of a database 500.
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # Read-only convenience field so a saved-articles list can show titles
    # without a second request per bookmark.
    article_title = serializers.CharField(source="article.title", read_only=True)

    class Meta:
        model = Bookmark
        fields = [
            "id",
            "user",
            "article",
            "article_title",
            "note",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
