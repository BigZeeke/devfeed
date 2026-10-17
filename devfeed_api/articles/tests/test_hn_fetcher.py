"""
Tests for hn_fetcher.py.

requests.get is replaced with a fake response, so these tests make no
network calls. No database is involved, so SimpleTestCase is used.
"""

from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from articles.ingestion.hn_fetcher import fetch_hacker_news_stories

# Patch requests.get as the fetcher module sees it.
REQUESTS_GET_PATH = "articles.ingestion.hn_fetcher.requests.get"

# A normal story with an external link, in the shape Algolia returns it.
FAKE_LINKED_HIT = {
    "objectID": "2001",
    "title": "A story with a link",
    "url": "https://example.com/linked-story",
    "author": "example-author",
    "points": 80,
    "num_comments": 12,
    "created_at": "2026-10-15T12:00:00Z",
}

# A text-only post: no url, and the title arrives under story_title.
FAKE_TEXT_ONLY_HIT = {
    "objectID": "2002",
    "title": None,
    "story_title": "Ask HN: a text-only post",
    "url": None,
    "author": "example-author",
    "points": 5,
    "num_comments": 3,
    "created_at": "2026-10-16T08:30:00Z",
}


def build_fake_response(response_json):
    """
    Builds a stand-in for a requests response: .json() returns the given
    data and .raise_for_status() does nothing unless a test changes it.
    """
    fake_response = Mock()
    fake_response.json.return_value = response_json
    return fake_response


class HackerNewsFetcherTests(SimpleTestCase):
    @patch(REQUESTS_GET_PATH)
    def test_sort_by_date_uses_search_by_date_endpoint(self, mock_get):
        mock_get.return_value = build_fake_response({"hits": []})

        fetch_hacker_news_stories(sort_by_date=True)

        self.assertEqual(
            mock_get.call_args.args[0], "https://hn.algolia.com/api/v1/search_by_date"
        )

    @patch(REQUESTS_GET_PATH)
    def test_relevance_sort_uses_search_endpoint(self, mock_get):
        mock_get.return_value = build_fake_response({"hits": []})

        fetch_hacker_news_stories(sort_by_date=False)

        self.assertEqual(
            mock_get.call_args.args[0], "https://hn.algolia.com/api/v1/search"
        )

    @patch(REQUESTS_GET_PATH)
    def test_query_parameter_sent_only_when_given(self, mock_get):
        mock_get.return_value = build_fake_response({"hits": []})

        fetch_hacker_news_stories(search_query="django", result_limit=15)
        parameters_with_query = mock_get.call_args.kwargs["params"]

        fetch_hacker_news_stories(search_query=None, result_limit=15)
        parameters_without_query = mock_get.call_args.kwargs["params"]

        self.assertEqual(
            parameters_with_query,
            {"tags": "story", "hitsPerPage": 15, "query": "django"},
        )
        self.assertEqual(parameters_without_query, {"tags": "story", "hitsPerPage": 15})

    @patch(REQUESTS_GET_PATH)
    def test_linked_story_is_mapped_to_descriptive_fields(self, mock_get):
        mock_get.return_value = build_fake_response({"hits": [FAKE_LINKED_HIT]})

        stories = fetch_hacker_news_stories()

        self.assertEqual(
            stories,
            [
                {
                    "hacker_news_object_id": "2001",
                    "title": "A story with a link",
                    "article_url": "https://example.com/linked-story",
                    "author": "example-author",
                    "points": 80,
                    "number_of_comments": 12,
                    "created_at": "2026-10-15T12:00:00Z",
                }
            ],
        )

    @patch(REQUESTS_GET_PATH)
    def test_text_only_post_falls_back_to_discussion_url_and_story_title(
        self, mock_get
    ):
        mock_get.return_value = build_fake_response({"hits": [FAKE_TEXT_ONLY_HIT]})

        story = fetch_hacker_news_stories()[0]

        self.assertEqual(
            story["article_url"], "https://news.ycombinator.com/item?id=2002"
        )
        self.assertEqual(story["title"], "Ask HN: a text-only post")

    @patch(REQUESTS_GET_PATH)
    def test_http_error_is_raised_instead_of_returning_empty_results(self, mock_get):
        # Simulates Algolia rejecting the request or being unavailable.
        fake_response = build_fake_response({})
        fake_response.raise_for_status.side_effect = requests.HTTPError(
            "503 Service Unavailable"
        )
        mock_get.return_value = fake_response

        with self.assertRaises(requests.HTTPError):
            fetch_hacker_news_stories()
