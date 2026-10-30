from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from articles.models import Article, Bookmark, Source, Tag
from articles.serializers import (
    ArticleSerializer,
    BookmarkSerializer,
    SourceSerializer,
    TagSerializer,
)


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


class BookmarkViewSet(ModelViewSet):
    """Each logged-in user can list, create, update and delete only their own bookmarks."""

    serializer_class = BookmarkSerializer
    # Overrides the global IsStaffOrReadOnly default: any logged-in user may
    # write here, and anonymous requests get 401.
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only the caller's rows exist from this view's point of view, so
        # another user's bookmark id returns 404 rather than 403, which
        # doesn't reveal that the row exists.
        return (
            Bookmark.objects.filter(user=self.request.user)
            .select_related("article")
            .order_by("-created_at")
        )
