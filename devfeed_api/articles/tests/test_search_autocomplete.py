"""
Tests for GET /api/search/autocomplete/: case-insensitive prefix matching on tag
labels, case-insensitive ordering, the paginated response shape, literal handling
of % and _, parameter validation, and read-only access.

Requests run anonymously unless a test says otherwise, since anyone can read.
Everything runs against Django's temporary test database, never the real one.
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from articles.models import Tag

# Long, uncommon, and not numeric, so it passes Django's password validators
TEST_PASSWORD = "Correct-Horse-Battery-42"

SEARCH_PATH = "/api/search/autocomplete/"


class SearchAutocompleteTests(APITestCase):
    def setUp(self):
        # Mixed case on purpose, so matching and ordering must both ignore case.
        # The 100... labels check that % and _ are not treated as wildcards.
        for label in ["python", "PyTorch", "pytest", "rust", "100%_done", "100abc"]:
            Tag.objects.create(label=label)

    def search(self, query_parameters):
        """GET the endpoint; the test client turns the dict into a query string."""
        return self.client.get(SEARCH_PATH, query_parameters)

    def result_labels(self, response):
        """Returns the labels from a response, in the order the API sent them."""
        return [result["label"] for result in response.data["results"]]

    # --- Matching and ordering ---

    def test_prefix_returns_only_matching_tags(self):
        response = self.search({"field": "tag", "query": "py"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(self.result_labels(response)), {"python", "PyTorch", "pytest"})

    def test_matching_ignores_case(self):
        response = self.search({"field": "tag", "query": "PY"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(self.result_labels(response)), {"python", "PyTorch", "pytest"})

    def test_results_are_sorted_ignoring_case(self):
        response = self.search({"field": "tag", "query": "py"})

        # A case-sensitive sort would put PyTorch first
        self.assertEqual(self.result_labels(response), ["pytest", "python", "PyTorch"])

    def test_response_uses_the_paginated_tag_shape(self):
        response = self.search({"field": "tag", "query": "rust"})
        rust_tag = Tag.objects.get(label="rust")

        # Same wrapper and result fields as GET /api/tags/
        self.assertEqual(
            response.data,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{"id": rust_tag.id, "label": "rust"}],
            },
        )

    def test_percent_and_underscore_match_literally(self):
        percent_response = self.search({"field": "tag", "query": "100%"})
        underscore_response = self.search({"field": "tag", "query": "100_"})

        # As SQL wildcards, both queries would match both 100... tags
        self.assertEqual(self.result_labels(percent_response), ["100%_done"])
        self.assertEqual(self.result_labels(underscore_response), [])

    # --- Parameter validation ---

    def test_unknown_field_returns_400(self):
        response = self.search({"field": "source", "query": "py"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"field": ["Must be one of: tag."]})

    def test_missing_field_returns_400(self):
        response = self.search({"query": "py"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("field", response.data)

    def test_whitespace_only_query_returns_400(self):
        response = self.search({"field": "tag", "query": "   "})

        # Whitespace is stripped first, so this counts as a blank query
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"query": ["This parameter is required."]})

    def test_bare_request_reports_both_errors(self):
        response = self.search({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"field", "query"})

    # --- Read-only ---

    def test_staff_user_cannot_post(self):
        staff_user = User.objects.create_user(
            username="staff_user", password=TEST_PASSWORD, is_staff=True
        )
        staff_token = Token.objects.create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {staff_token.key}")

        response = self.client.post(SEARCH_PATH, {"label": "new"}, format="json")

        # Staff passes IsStaffOrReadOnly, so this 405 comes from the view itself
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(Tag.objects.filter(label="new").exists())
