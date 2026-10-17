"""
Tests for github_search_fetcher.py.

requests.get is replaced with a fake response, so these tests make no
network calls. No database is involved, so SimpleTestCase is used.
"""

from datetime import date, timedelta
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from articles.ingestion.github_search_fetcher import (
    GITHUB_SEARCH_URL,
    fetch_recently_created_repositories,
)

# Patch requests.get as the fetcher module sees it.
REQUESTS_GET_PATH = "articles.ingestion.github_search_fetcher.requests.get"
TOKEN_PATH = "articles.ingestion.github_search_fetcher.GITHUB_PERSONAL_ACCESS_TOKEN"

# One repository in the shape GitHub's Search API returns it.
FAKE_GITHUB_ITEM = {
    "owner": {"login": "example-owner"},
    "name": "example-repository",
    "full_name": "example-owner/example-repository",
    "html_url": "https://github.com/example-owner/example-repository",
    "description": "An example repository",
    "language": "Python",
    "stargazers_count": 250,
    "created_at": "2026-10-15T12:00:00Z",
}


def build_fake_response(response_json):
    """
    Builds a stand-in for a requests response: .json() returns the given
    data and .raise_for_status() does nothing unless a test changes it.
    """
    fake_response = Mock()
    fake_response.json.return_value = response_json
    return fake_response


class GithubSearchFetcherTests(SimpleTestCase):
    @patch(REQUESTS_GET_PATH)
    def test_request_searches_by_creation_date_sorted_by_stars(self, mock_get):
        mock_get.return_value = build_fake_response({"items": []})

        fetch_recently_created_repositories(days_back=7, result_limit=5)

        # The cutoff is computed from today's date, same as the fetcher does.
        expected_cutoff = (date.today() - timedelta(days=7)).isoformat()
        request_call = mock_get.call_args
        self.assertEqual(request_call.args[0], GITHUB_SEARCH_URL)
        self.assertEqual(
            request_call.kwargs["params"],
            {
                "q": f"created:>{expected_cutoff}",
                "sort": "stars",
                "order": "desc",
                "per_page": 5,
            },
        )
        self.assertEqual(request_call.kwargs["timeout"], 10)

    @patch(REQUESTS_GET_PATH)
    def test_language_filter_is_added_to_query(self, mock_get):
        mock_get.return_value = build_fake_response({"items": []})

        fetch_recently_created_repositories(programming_language="python")

        search_query = mock_get.call_args.kwargs["params"]["q"]
        self.assertTrue(search_query.endswith(" language:python"))

    @patch(REQUESTS_GET_PATH)
    def test_authorization_header_sent_when_token_is_set(self, mock_get):
        mock_get.return_value = build_fake_response({"items": []})

        with patch(TOKEN_PATH, "test-token"):
            fetch_recently_created_repositories()

        request_headers = mock_get.call_args.kwargs["headers"]
        self.assertEqual(request_headers["Authorization"], "Bearer test-token")

    @patch(REQUESTS_GET_PATH)
    def test_no_authorization_header_without_token(self, mock_get):
        mock_get.return_value = build_fake_response({"items": []})

        with patch(TOKEN_PATH, None):
            fetch_recently_created_repositories()

        request_headers = mock_get.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", request_headers)

    @patch(REQUESTS_GET_PATH)
    def test_response_items_are_mapped_to_descriptive_fields(self, mock_get):
        mock_get.return_value = build_fake_response({"items": [FAKE_GITHUB_ITEM]})

        repositories = fetch_recently_created_repositories()

        self.assertEqual(
            repositories,
            [
                {
                    "owner": "example-owner",
                    "repository_name": "example-repository",
                    "full_name": "example-owner/example-repository",
                    "repository_url": "https://github.com/example-owner/example-repository",
                    "description": "An example repository",
                    "programming_language": "Python",
                    "total_stars": 250,
                    "created_at": "2026-10-15T12:00:00Z",
                }
            ],
        )

    @patch(REQUESTS_GET_PATH)
    def test_http_error_is_raised_instead_of_returning_empty_results(self, mock_get):
        # Simulates GitHub rejecting the request, e.g. for a rate limit.
        fake_response = build_fake_response({})
        fake_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = fake_response

        with self.assertRaises(requests.HTTPError):
            fetch_recently_created_repositories()
