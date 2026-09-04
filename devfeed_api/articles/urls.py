from rest_framework.routers import DefaultRouter

from articles.views import ArticleViewSet, SourceViewSet, TagViewSet

router = DefaultRouter()
router.register("sources", SourceViewSet, basename="source")
router.register("tags", TagViewSet, basename="tag")
router.register("articles", ArticleViewSet, basename="article")

urlpatterns = router.urls
