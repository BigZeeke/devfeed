from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from articles.models import Article, Bookmark, Source, Tag, Vote
from articles.serializers import (
    ArticleSerializer,
    BookmarkSerializer,
    SourceSerializer,
    TagSerializer,
    VoteSerializer,
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

    # POST /api/articles/<id>/vote/. permission_classes here applies to this
    # action only: any logged-in user can vote, while creating, editing and
    # deleting articles stays staff-only through the global default.
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def vote(self, request, pk=None):
        """Set, switch, or clear the caller's vote on this article."""
        # 404 if the article doesn't exist
        article = self.get_object()

        vote_serializer = VoteSerializer(data=request.data)
        vote_serializer.is_valid(raise_exception=True)
        chosen_direction = vote_serializer.validated_data["direction"]

        # One Vote row per user+article: the first vote creates it, later votes
        # switch it, and null clears the direction without deleting the row.
        Vote.objects.update_or_create(
            user=request.user,
            article=article,
            defaults={"direction": chosen_direction},
        )

        # Count in the database with one query rather than loading every vote
        vote_counts = article.votes.aggregate(
            up_votes=Count("id", filter=Q(direction=Vote.Direction.UP)),
            down_votes=Count("id", filter=Q(direction=Vote.Direction.DOWN)),
        )
        return Response(
            {"article": article.id, "direction": chosen_direction, **vote_counts}
        )


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
