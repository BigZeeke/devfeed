"""
Tests for the /api/bookmarks/ endpoints: login required, owner set from the
logged-in user, duplicates rejected, and each user limited to their own rows.

Requests run as a regular (non-staff) user, since bookmarks are user-owned data.
Everything runs against Django's temporary test database, never the real one.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from articles.models import Article, Bookmark, Source

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"

BOOKMARKS_PATH = "/api/bookmarks/"


def create_user_with_token(username):
    """Creates a regular (non-staff) user and returns the user and their token key."""
    new_user = User.objects.create_user(username=username, password=TEST_PASSWORD)
    new_token = Token.objects.create(user=new_user)
    return new_user, new_token.key


class BookmarkEndpointTests(APITestCase):
    def setUp(self):
        # The owner makes the requests; the other user's rows must stay out of reach
        self.owner_user, self.owner_token_key = create_user_with_token("owner_user")
        self.other_user, self.other_token_key = create_user_with_token("other_user")

        source = Source.objects.create(
            name="Test Source", type=Source.SourceType.API, url="https://example.com"
        )
        self.first_article = Article.objects.create(
            source=source, title="First Article", url="https://example.com/first"
        )
        self.second_article = Article.objects.create(
            source=source, title="Second Article", url="https://example.com/second"
        )

        # A bookmark that belongs to the other user, on the first article
        self.other_users_bookmark = Bookmark.objects.create(
            user=self.other_user, article=self.first_article, note="Not yours"
        )
        self.other_users_bookmark_path = f"{BOOKMARKS_PATH}{self.other_users_bookmark.id}/"

        self.authenticate_as(self.owner_token_key)

    def authenticate_as(self, token_key):
        """Send this token on every request the test client makes."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")

    # --- Login required ---

    def test_request_without_token_is_rejected(self):
        self.client.credentials()  # clear the token set in setUp

        response = self.client.get(BOOKMARKS_PATH)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Owner comes from the logged-in user ---

    def test_create_saves_the_logged_in_user_as_owner(self):
        response = self.client.post(
            BOOKMARKS_PATH,
            {"article": self.second_article.id, "note": "Read later"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        saved_bookmark = Bookmark.objects.get(id=response.data["id"])
        self.assertEqual(saved_bookmark.user, self.owner_user)
        self.assertEqual(saved_bookmark.note, "Read later")
        # The owner is never exposed in the response
        self.assertNotIn("user", response.data)

    def test_owner_in_request_body_is_ignored(self):
        response = self.client.post(
            BOOKMARKS_PATH,
            {"article": self.second_article.id, "user": self.other_user.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        saved_bookmark = Bookmark.objects.get(id=response.data["id"])
        self.assertEqual(saved_bookmark.user, self.owner_user)

    # --- Duplicates and validation ---

    def test_two_users_can_bookmark_the_same_article(self):
        # The other user already bookmarked first_article in setUp
        response = self.client.post(
            BOOKMARKS_PATH, {"article": self.first_article.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bookmark.objects.filter(article=self.first_article).count(), 2)

    def test_duplicate_bookmark_returns_400(self):
        first_response = self.client.post(
            BOOKMARKS_PATH, {"article": self.second_article.id}, format="json"
        )
        duplicate_response = self.client.post(
            BOOKMARKS_PATH, {"article": self.second_article.id}, format="json"
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Bookmark.objects.filter(user=self.owner_user).count(), 1)

    def test_note_over_500_characters_returns_400(self):
        response = self.client.post(
            BOOKMARKS_PATH,
            {"article": self.second_article.id, "note": "x" * 501},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("note", response.data)
        self.assertFalse(Bookmark.objects.filter(user=self.owner_user).exists())

    # --- Each user sees and changes only their own rows ---

    def test_list_shows_only_the_callers_bookmarks(self):
        own_bookmark = Bookmark.objects.create(
            user=self.owner_user, article=self.second_article
        )

        response = self.client.get(BOOKMARKS_PATH)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listed_ids = [bookmark["id"] for bookmark in response.data["results"]]
        self.assertEqual(listed_ids, [own_bookmark.id])

    def test_other_users_bookmark_returns_404(self):
        response = self.client.get(self.other_users_bookmark_path)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_other_users_bookmark(self):
        response = self.client.patch(
            self.other_users_bookmark_path, {"note": "Changed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_users_bookmark.refresh_from_db()
        self.assertEqual(self.other_users_bookmark.note, "Not yours")

    def test_cannot_delete_other_users_bookmark(self):
        response = self.client.delete(self.other_users_bookmark_path)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Bookmark.objects.filter(id=self.other_users_bookmark.id).exists())

    def test_owner_can_update_note_and_read_flag(self):
        own_bookmark = Bookmark.objects.create(
            user=self.owner_user, article=self.second_article
        )

        response = self.client.patch(
            f"{BOOKMARKS_PATH}{own_bookmark.id}/",
            {"note": "Finished it", "is_read": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        own_bookmark.refresh_from_db()
        self.assertEqual(own_bookmark.note, "Finished it")
        self.assertTrue(own_bookmark.is_read)
