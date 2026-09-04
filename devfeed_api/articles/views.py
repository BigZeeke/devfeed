from rest_framework.viewsets import ModelViewSet

from articles.models import Article, Source, Tag
from articles.serializers import ArticleSerializer, SourceSerializer, TagSerializer


class SourceViewSet(ModelViewSet):
    queryset = Source.objects.all().order_by("name")
    serializer_class = SourceSerializer


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all().order_by("label")
    serializer_class = TagSerializer


class ArticleViewSet(ModelViewSet):
    # select_related pulls Source in the same query (avoids N+1 when
    # serializing source_name for every article in a list). prefetch_related
    # does the same for the tags M2M.
    queryset = (
        Article.objects.select_related("source")
        .prefetch_related("tags")
        .order_by("-published_at")
    )
    serializer_class = ArticleSerializer
