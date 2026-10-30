"""
Tests for POST /api/articles/<id>/vote/: login required, one vote row per user
and article, switching and clearing votes, input validation, and vote counts.

Requests run as a regular (non-staff) user, since any logged-in user can vote.
Everything runs against Django's temporary test database, never the real one.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from articles.models import Article, Source, Vote

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"

ARTICLES_PATH = "/api/articles/"


def create_user_with_token(username):
    """Creates a regular (non-staff) user and returns the user and their token key."""
    new_user = User.objects.create_user(username=username, password=TEST_PASSWORD)
    new_token = Token.objects.create(user=new_user)
    return new_user, new_token.key


class VoteEndpointTests(APITestCase):
    def setUp(self):
        self.voting_user, self.voting_token_key = create_user_with_token("voting_user")
        self.other_user, _ = create_user_with_token("other_user")

        source = Source.objects.create(
            name="Test Source", type=Source.SourceType.API, url="https://example.com"
        )
        self.article = Article.objects.create(
            source=source, title="Votable Article", url="https://example.com/votable"
        )
        self.vote_path = f"{ARTICLES_PATH}{self.article.id}/vote/"

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.voting_token_key}")

    def send_vote(self, direction):
        """POST a vote with the given direction ("up", "down", or None)."""
        return self.client.post(self.vote_path, {"direction": direction}, format="json")

    def callers_vote_rows(self):
        return Vote.objects.filter(user=self.voting_user, article=self.article)

    # --- Login required ---

    def test_vote_without_token_is_rejected(self):
        self.client.credentials()  # clear the token set in setUp

        response = self.send_vote("up")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Vote.objects.exists())

    # --- Voting, switching, clearing ---

    def test_first_vote_creates_one_row(self):
        response = self.send_vote("up")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"article": self.article.id, "direction": "up", "up_votes": 1, "down_votes": 0},
        )
        self.assertEqual(self.callers_vote_rows().get().direction, "up")

    def test_switching_vote_updates_the_same_row(self):
        self.send_vote("up")
        original_vote_id = self.callers_vote_rows().get().id

        response = self.send_vote("down")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["up_votes"], 0)
        self.assertEqual(response.data["down_votes"], 1)
        switched_vote = self.callers_vote_rows().get()
        self.assertEqual(switched_vote.id, original_vote_id)
        self.assertEqual(switched_vote.direction, "down")

    def test_null_clears_the_vote_but_keeps_the_row(self):
        self.send_vote("up")

        response = self.send_vote(None)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["direction"])
        self.assertEqual(response.data["up_votes"], 0)
        self.assertEqual(response.data["down_votes"], 0)
        self.assertIsNone(self.callers_vote_rows().get().direction)

    def test_repeating_the_same_vote_never_adds_a_row(self):
        self.send_vote("up")
        response = self.send_vote("up")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["up_votes"], 1)
        self.assertEqual(self.callers_vote_rows().count(), 1)

    def test_counts_include_other_users_votes(self):
        Vote.objects.create(user=self.other_user, article=self.article, direction="up")

        response = self.send_vote("down")

        self.assertEqual(response.data["up_votes"], 1)
        self.assertEqual(response.data["down_votes"], 1)

    # --- Validation and missing articles ---

    def test_invalid_direction_returns_400(self):
        response = self.send_vote("sideways")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("direction", response.data)
        self.assertFalse(Vote.objects.exists())

    def test_missing_direction_returns_400(self):
        response = self.client.post(self.vote_path, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Vote.objects.exists())

    def test_vote_on_unknown_article_returns_404(self):
        response = self.client.post(
            f"{ARTICLES_PATH}999999/vote/", {"direction": "up"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Vote.objects.exists())

    # --- Voting doesn't loosen article permissions ---

    def test_voting_user_still_cannot_edit_the_article(self):
        response = self.client.patch(
            f"{ARTICLES_PATH}{self.article.id}/", {"title": "Changed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Votable Article")
