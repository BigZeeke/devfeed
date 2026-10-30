"""
Tests for the /api/keywords/ endpoints: login required, keywords normalized to
lowercase, duplicates rejected regardless of case, and each user limited to
their own rows.

Everything runs against Django's temporary test database, never the real one.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from user_profiles.models import UserKeyword

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"

KEYWORDS_PATH = "/api/keywords/"


def create_user_with_token(username):
    """Creates a regular (non-staff) user and returns the user and their token key."""
    new_user = User.objects.create_user(username=username, password=TEST_PASSWORD)
    new_token = Token.objects.create(user=new_user)
    return new_user, new_token.key


class KeywordEndpointTests(APITestCase):
    def setUp(self):
        # The owner makes the requests; the other user's rows must stay out of reach
        self.owner_user, self.owner_token_key = create_user_with_token("owner_user")
        self.other_user, self.other_token_key = create_user_with_token("other_user")

        # A keyword that belongs to the other user
        self.other_users_keyword = UserKeyword.objects.create(
            user=self.other_user, keyword="rust", weight=2
        )
        self.other_users_keyword_path = f"{KEYWORDS_PATH}{self.other_users_keyword.id}/"

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token_key}")

    # --- Login required ---

    def test_request_without_token_is_rejected(self):
        self.client.credentials()  # clear the token set in setUp

        response = self.client.get(KEYWORDS_PATH)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Create and normalize ---

    def test_create_lowercases_and_trims_the_keyword(self):
        response = self.client.post(
            KEYWORDS_PATH, {"keyword": "  Python  ", "weight": 3}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["keyword"], "python")
        saved_keyword = UserKeyword.objects.get(id=response.data["id"])
        self.assertEqual(saved_keyword.keyword, "python")
        self.assertEqual(saved_keyword.weight, 3)
        self.assertEqual(saved_keyword.user, self.owner_user)

    def test_owner_in_request_body_is_ignored(self):
        response = self.client.post(
            KEYWORDS_PATH, {"keyword": "django", "user": self.other_user.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        saved_keyword = UserKeyword.objects.get(id=response.data["id"])
        self.assertEqual(saved_keyword.user, self.owner_user)

    def test_blank_keyword_returns_400(self):
        response = self.client.post(KEYWORDS_PATH, {"keyword": "   "}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("keyword", response.data)

    # --- Duplicates ---

    def test_duplicate_with_different_case_returns_400(self):
        UserKeyword.objects.create(user=self.owner_user, keyword="python")

        response = self.client.post(KEYWORDS_PATH, {"keyword": "PYTHON"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserKeyword.objects.filter(user=self.owner_user).count(), 1)

    def test_two_users_can_follow_the_same_keyword(self):
        # The other user already follows "rust" in setUp
        response = self.client.post(KEYWORDS_PATH, {"keyword": "rust"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserKeyword.objects.filter(keyword="rust").count(), 2)

    # --- Each user sees and changes only their own rows ---

    def test_list_shows_only_the_callers_keywords_in_alphabetical_order(self):
        UserKeyword.objects.create(user=self.owner_user, keyword="python")
        UserKeyword.objects.create(user=self.owner_user, keyword="django")

        response = self.client.get(KEYWORDS_PATH)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listed_keywords = [entry["keyword"] for entry in response.data["results"]]
        self.assertEqual(listed_keywords, ["django", "python"])

    def test_other_users_keyword_returns_404(self):
        response = self.client.get(self.other_users_keyword_path)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_other_users_keyword(self):
        response = self.client.patch(
            self.other_users_keyword_path, {"weight": 9}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_users_keyword.refresh_from_db()
        self.assertEqual(self.other_users_keyword.weight, 2)

    def test_cannot_delete_other_users_keyword(self):
        response = self.client.delete(self.other_users_keyword_path)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(UserKeyword.objects.filter(id=self.other_users_keyword.id).exists())

    def test_owner_can_update_weight(self):
        own_keyword = UserKeyword.objects.create(user=self.owner_user, keyword="python")

        response = self.client.patch(
            f"{KEYWORDS_PATH}{own_keyword.id}/", {"weight": 5}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        own_keyword.refresh_from_db()
        self.assertEqual(own_keyword.weight, 5)
