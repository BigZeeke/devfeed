"""
Tests for project-level environment config: CORS headers from django-cors-headers,
and the read_comma_separated_setting() helper that parses list values from .env.

CORS tests set their own allowed origins with override_settings, so they pass the
same way whatever the local .env holds. Requests run anonymously, since anyone can
read /api/tags/. Everything runs against Django's temporary test database.
"""

import os
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from devfeed_api.settings import read_comma_separated_setting

ALLOWED_ORIGIN = "http://localhost:5173"
UNLISTED_ORIGIN = "http://not-allowed.example"

TAGS_PATH = "/api/tags/"
BOOKMARKS_PATH = "/api/bookmarks/"

# Variable name used only by these tests, so no real setting is touched
TEST_VARIABLE_NAME = "DEVFEED_TEST_COMMA_SEPARATED"


@override_settings(CORS_ALLOWED_ORIGINS=[ALLOWED_ORIGIN])
class CorsHeaderTests(APITestCase):
    def get_tags_from(self, origin):
        """GET /api/tags/ as a browser page on the given origin would."""
        return self.client.get(TAGS_PATH, headers={"Origin": origin})

    # --- Simple requests ---

    def test_allowed_origin_gets_allow_origin_header(self):
        response = self.get_tags_from(ALLOWED_ORIGIN)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN)

    def test_unlisted_origin_gets_no_allow_origin_header(self):
        response = self.get_tags_from(UNLISTED_ORIGIN)

        # The data still comes back; the browser is what blocks the page from reading it
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_request_without_origin_gets_no_allow_origin_header(self):
        # curl and server-to-server calls send no Origin header
        response = self.client.get(TAGS_PATH)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_empty_origin_list_allows_no_origin(self):
        # The production default: NGINX serves frontend and API from one origin
        response = self.get_tags_from(ALLOWED_ORIGIN)

        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    # --- Preflight ---

    def test_preflight_allows_authorization_and_content_type_for_post(self):
        # The OPTIONS request a browser sends before a logged-in JSON POST
        response = self.client.options(
            BOOKMARKS_PATH,
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type",
            },
        )
        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN)
        self.assertIn("authorization", allowed_headers)
        self.assertIn("content-type", allowed_headers)
        self.assertIn("POST", allowed_methods)


class ReadCommaSeparatedSettingTests(SimpleTestCase):
    # patch.dict restores the real environment when each block ends

    def test_strips_spaces_and_drops_blank_entries(self):
        with patch.dict(os.environ, {TEST_VARIABLE_NAME: " first , second,, "}):
            self.assertEqual(read_comma_separated_setting(TEST_VARIABLE_NAME), ["first", "second"])

    def test_missing_variable_returns_empty_list(self):
        with patch.dict(os.environ):
            os.environ.pop(TEST_VARIABLE_NAME, None)
            self.assertEqual(read_comma_separated_setting(TEST_VARIABLE_NAME), [])

    def test_blank_value_returns_empty_list(self):
        with patch.dict(os.environ, {TEST_VARIABLE_NAME: "   "}):
            self.assertEqual(read_comma_separated_setting(TEST_VARIABLE_NAME), [])
