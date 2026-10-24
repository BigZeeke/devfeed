"""
Tests for IsStaffOrReadOnly, the default permission on sources, tags, and articles.

Requests send real "Authorization: Token <key>" headers, so these also exercise
TokenAuthentication. Everything runs against Django's temporary test database.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from articles.models import Article, Source, Tag

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"


class IsStaffOrReadOnlyTests(APITestCase):
    def setUp(self):
        # One regular user and one staff user, each with an API token
        self.regular_user = User.objects.create_user(
            username="regular_user", password=TEST_PASSWORD
        )
        self.staff_user = User.objects.create_user(
            username="staff_user", password=TEST_PASSWORD, is_staff=True
        )
        self.regular_user_token = Token.objects.create(user=self.regular_user)
        self.staff_user_token = Token.objects.create(user=self.staff_user)

        # One source and one article for the update and delete tests
        self.source = Source.objects.create(
            name="Test Source", type=Source.SourceType.API, url="https://example.com"
        )
        self.article = Article.objects.create(
            source=self.source,
            title="Test Article",
            url="https://example.com/test-article",
        )

    def authenticate_as(self, token):
        """Send this token on every request the test client makes."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_anonymous_user_can_read_articles(self):
        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_user_cannot_create_tag(self):
        response = self.client.post(
            "/api/tags/", {"label": "python"}, format="json")

        # 401: no credentials were sent at all
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Tag.objects.filter(label="python").exists())

    def test_invalid_token_is_rejected_even_for_reads(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")

        response = self.client.get("/api/articles/")

        # A bad token fails authentication before permissions are checked
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_create_tag(self):
        self.authenticate_as(self.regular_user_token)

        response = self.client.post(
            "/api/tags/", {"label": "python"}, format="json")

        # 403: the user is identified but not allowed to write
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Tag.objects.filter(label="python").exists())

    def test_regular_user_cannot_update_source(self):
        self.authenticate_as(self.regular_user_token)

        response = self.client.patch(
            f"/api/sources/{self.source.id}/", {"name": "Renamed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.source.refresh_from_db()
        self.assertEqual(self.source.name, "Test Source")

    def test_regular_user_cannot_delete_article(self):
        self.authenticate_as(self.regular_user_token)

        response = self.client.delete(f"/api/articles/{self.article.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Article.objects.filter(id=self.article.id).exists())

    def test_staff_user_can_create_tag(self):
        self.authenticate_as(self.staff_user_token)

        response = self.client.post(
            "/api/tags/", {"label": "python"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tag.objects.filter(label="python").exists())
