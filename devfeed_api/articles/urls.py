from rest_framework.routers import DefaultRouter

from articles.views import ArticleViewSet, BookmarkViewSet, SourceViewSet, TagViewSet

router = DefaultRouter()
router.register("sources", SourceViewSet, basename="source")
router.register("tags", TagViewSet, basename="tag")
router.register("articles", ArticleViewSet, basename="article")
# basename is required here because BookmarkViewSet has no queryset attribute
router.register("bookmarks", BookmarkViewSet, basename="bookmark")

urlpatterns = router.urls
