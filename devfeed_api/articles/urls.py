from django.urls import path
from rest_framework.routers import DefaultRouter

from articles.views import (
    ArticleViewSet,
    BookmarkViewSet,
    SearchAutocompleteView,
    SourceViewSet,
    TagViewSet,
)

router = DefaultRouter()
router.register("sources", SourceViewSet, basename="source")
router.register("tags", TagViewSet, basename="tag")
router.register("articles", ArticleViewSet, basename="article")
# basename is required here because BookmarkViewSet has no queryset attribute
router.register("bookmarks", BookmarkViewSet, basename="bookmark")

urlpatterns = router.urls + [
    # Not a viewset, so it's added as a plain path next to the router's routes
    path("search/autocomplete/", SearchAutocompleteView.as_view(), name="search-autocomplete"),
]
