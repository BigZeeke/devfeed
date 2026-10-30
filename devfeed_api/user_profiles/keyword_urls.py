"""URL routes for followed keywords, mounted at /api/ (the list is /api/keywords/)."""

from rest_framework.routers import SimpleRouter

from .views import KeywordViewSet

# SimpleRouter, not DefaultRouter: the articles router already provides the
# /api/ root page, and a second DefaultRouter would add a duplicate one.
router = SimpleRouter()
# basename is required because KeywordViewSet has no queryset attribute
router.register("keywords", KeywordViewSet, basename="keyword")

urlpatterns = router.urls
