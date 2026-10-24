"""
Tests for the register, token (login), and logout endpoints under /api/auth/.

Everything runs against Django's temporary test database, never the real one.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"

REGISTER_PATH = "/api/auth/register/"
TOKEN_PATH = "/api/auth/token/"
LOGOUT_PATH = "/api/auth/logout/"


class RegisterEndpointTests(APITestCase):
    def test_register_returns_201_with_the_users_token(self):
        response = self.client.post(
            REGISTER_PATH,
            {"username": "new_user", "email": "new_user@example.com",
                "password": TEST_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(username="new_user")
        # The returned token is the one stored for this user
        self.assertEqual(response.data["token"],
                         Token.objects.get(user=new_user).key)
        self.assertEqual(response.data["username"], "new_user")
        # Sign-up never grants staff rights
        self.assertFalse(new_user.is_staff)

    def test_register_stores_a_hashed_password(self):
        self.client.post(
            REGISTER_PATH,
            {"username": "new_user", "password": TEST_PASSWORD},
            format="json",
        )

        new_user = User.objects.get(username="new_user")
        self.assertNotEqual(new_user.password, TEST_PASSWORD)
        self.assertTrue(new_user.check_password(TEST_PASSWORD))

    def test_register_rejects_a_weak_password(self):
        response = self.client.post(
            REGISTER_PATH,
            {"username": "new_user", "password": "123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(username="new_user").exists())

    def test_register_rejects_a_duplicate_username(self):
        User.objects.create_user(username="taken_name", password=TEST_PASSWORD)

        response = self.client.post(
            REGISTER_PATH,
            {"username": "taken_name", "password": TEST_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertEqual(User.objects.filter(username="taken_name").count(), 1)

    def test_register_requires_username_and_password(self):
        response = self.client.post(REGISTER_PATH, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)
        self.assertEqual(User.objects.count(), 0)


class TokenEndpointTests(APITestCase):
    def setUp(self):
        self.existing_user = User.objects.create_user(
            username="existing_user", password=TEST_PASSWORD
        )
        self.existing_token = Token.objects.create(user=self.existing_user)

    def test_valid_credentials_return_the_existing_token(self):
        response = self.client.post(
            TOKEN_PATH,
            {"username": "existing_user", "password": TEST_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["token"], self.existing_token.key)

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            TOKEN_PATH,
            {"username": "existing_user", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", response.data)


class LogoutEndpointTests(APITestCase):
    def setUp(self):
        self.existing_user = User.objects.create_user(
            username="existing_user", password=TEST_PASSWORD
        )
        self.existing_token = Token.objects.create(user=self.existing_user)

    def authenticate_with_existing_token(self):
        """Send the user's token on every request the test client makes."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.existing_token.key}")

    def test_logout_deletes_the_token(self):
        self.authenticate_with_existing_token()

        response = self.client.post(LOGOUT_PATH)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(
            user=self.existing_user).exists())

    def test_deleted_token_cannot_be_reused(self):
        self.authenticate_with_existing_token()
        self.client.post(LOGOUT_PATH)

        # Same header again, but the token row is gone
        response = self.client.post(LOGOUT_PATH)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_a_token_is_rejected(self):
        response = self.client.post(LOGOUT_PATH)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
