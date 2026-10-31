from django.db.models import Count, Q
from django.db.models.functions import Lower
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
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


class SearchAutocompleteView(ListAPIView):
    """GET /api/search/autocomplete/?field=tag&query=<text>

    Returns rows whose text starts with the query (ignoring case), sorted
    alphabetically, in the same paginated shape as the matching list
    endpoint. Read-only: ListAPIView only accepts GET, HEAD and OPTIONS.
    """

    # One entry per field a client can autocomplete. Supporting a new field
    # means adding an entry here; the URL and the view code stay the same.
    SEARCHABLE_FIELDS = {
        "tag": {"model": Tag, "column": "label", "serializer_class": TagSerializer},
    }

    def get_search_settings(self):
        """Validate the field and query parameters; return (field settings, query text)."""
        field_name = self.request.query_params.get("field", "")
        query_text = self.request.query_params.get("query", "").strip()

        # Collect both problems so one 400 response reports everything wrong
        errors = {}
        if field_name not in self.SEARCHABLE_FIELDS:
            allowed_fields = ", ".join(sorted(self.SEARCHABLE_FIELDS))
            errors["field"] = [f"Must be one of: {allowed_fields}."]
        if not query_text:
            errors["query"] = ["This parameter is required."]
        if errors:
            raise ValidationError(errors)

        return self.SEARCHABLE_FIELDS[field_name], query_text

    def get_queryset(self):
        field_settings, query_text = self.get_search_settings()
        column = field_settings["column"]
        # istartswith is a case-insensitive prefix match; Django escapes % and _
        # in query_text, so they match literally rather than as wildcards.
        # Sorting on Lower(column) gives pytest, python, PyTorch on any database
        # collation (some sort capitals first); the plain column breaks ties.
        return (
            field_settings["model"]
            .objects.filter(**{f"{column}__istartswith": query_text})
            .order_by(Lower(column), column)
        )

    def get_serializer_class(self):
        field_settings, _ = self.get_search_settings()
        return field_settings["serializer_class"]
