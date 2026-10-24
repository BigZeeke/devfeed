"""
Tests for the article endpoints: updates, idempotency, tag_labels, and input validation.

All requests run as a staff user, since these test API behavior, not permissions
(see test_permissions.py). Everything runs against Django's temporary test database.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from articles.models import Article, Source, Tag

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"

ARTICLES_PATH = "/api/articles/"


def current_tag_labels(article):
    """Returns the article's tag labels as a set, so order doesn't matter."""
    return set(article.tags.values_list("label", flat=True))


class ArticleEndpointTests(APITestCase):
    def setUp(self):
        # Authenticate every request as a staff user
        staff_user = User.objects.create_user(
            username="staff_user", password=TEST_PASSWORD, is_staff=True
        )
        staff_token = Token.objects.create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {staff_token.key}")

        self.source = Source.objects.create(
            name="Test Source", type=Source.SourceType.API, url="https://example.com"
        )

        # The article each test works on, tagged python and django
        self.article = Article.objects.create(
            source=self.source,
            title="Original Title",
            url="https://example.com/original",
            raw_score=10,
        )
        self.article.tags.set([
            Tag.objects.create(label="python"),
            Tag.objects.create(label="django"),
        ])

        # A second article that should never be touched
        self.other_article = Article.objects.create(
            source=self.source,
            title="Other Article",
            url="https://example.com/other",
        )

        self.article_path = f"{ARTICLES_PATH}{self.article.id}/"

    def full_update_payload(self, **overrides):
        """All writable fields for a PUT, with any field replaceable per test."""
        payload = {
            "source": self.source.id,
            "title": "Updated Title",
            "url": "https://example.com/updated",
            "raw_score": 99,
        }
        payload.update(overrides)
        return payload

    # --- PUT changes the database ---

    def test_put_changes_the_database(self):
        response = self.client.put(
            self.article_path, self.full_update_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated Title")
        self.assertEqual(self.article.url, "https://example.com/updated")
        self.assertEqual(self.article.raw_score, 99)

    # --- Idempotency ---

    def test_repeated_put_leaves_the_same_state(self):
        first_response = self.client.put(
            self.article_path, self.full_update_payload(), format="json")
        second_response = self.client.put(
            self.article_path, self.full_update_payload(), format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        # Same request, same result, and no new rows
        self.assertEqual(first_response.data, second_response.data)
        self.assertEqual(Article.objects.count(), 2)

    def test_delete_removes_only_that_article(self):
        response = self.client.delete(self.article_path)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=self.article.id).exists())
        self.assertTrue(Article.objects.filter(
            id=self.other_article.id).exists())

    def test_second_delete_returns_404_and_changes_nothing(self):
        self.client.delete(self.article_path)

        response = self.client.delete(self.article_path)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Article.objects.count(), 1)

    # --- tag_labels on update ---

    def test_put_with_tag_labels_replaces_the_tags(self):
        response = self.client.put(
            self.article_path, self.full_update_payload(tag_labels=["rust"]), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(current_tag_labels(self.article), {"rust"})

    def test_patch_without_tag_labels_keeps_the_tags(self):
        response = self.client.patch(
            self.article_path, {"title": "Patched Title"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(current_tag_labels(
            self.article), {"python", "django"})

    def test_put_with_empty_tag_labels_clears_the_tags(self):
        response = self.client.put(
            self.article_path, self.full_update_payload(tag_labels=[]), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(current_tag_labels(self.article), set())

    # --- 400s for invalid input ---

    def test_create_without_required_fields_returns_400(self):
        response = self.client.post(ARTICLES_PATH, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for required_field in ["source", "title", "url"]:
            self.assertIn(required_field, response.data)
        self.assertEqual(Article.objects.count(), 2)

    def test_create_with_malformed_url_returns_400(self):
        response = self.client.post(
            ARTICLES_PATH, self.full_update_payload(url="not-a-url"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("url", response.data)
        self.assertEqual(Article.objects.count(), 2)

    def test_create_with_duplicate_url_returns_400(self):
        response = self.client.post(
            ARTICLES_PATH,
            self.full_update_payload(url="https://example.com/original"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("url", response.data)
        self.assertEqual(Article.objects.count(), 2)

    def test_create_with_unknown_source_returns_400(self):
        unknown_source_id = self.source.id + 1000

        response = self.client.post(
            ARTICLES_PATH, self.full_update_payload(source=unknown_source_id), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("source", response.data)
        self.assertEqual(Article.objects.count(), 2)

    def test_tag_label_over_100_characters_returns_400(self):
        response = self.client.post(
            ARTICLES_PATH, self.full_update_payload(tag_labels=["x" * 101]), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tag_labels", response.data)
        self.assertEqual(Article.objects.count(), 2)
