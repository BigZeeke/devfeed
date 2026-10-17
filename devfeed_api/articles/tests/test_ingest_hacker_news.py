"""
Tests for the ingest_hacker_news management command.

The fetcher is replaced with fake data, so these tests make no network
calls and run against Django's temporary test database, never the real one.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from articles.models import Article, Source

# Patch the fetcher where the command looks it up (inside the command module),
# not where it's defined, or the command would still call the real one.
FETCHER_PATH = (
    "articles.management.commands.ingest_hacker_news.fetch_hacker_news_stories"
)

# A complete story, in the shape the real fetcher returns.
COMPLETE_STORY = {
    "hacker_news_object_id": "1001",
    "title": "A complete story",
    "article_url": "https://example.com/complete-story",
    "author": "example-author",
    "points": 120,
    "number_of_comments": 30,
    "created_at": "2026-10-15T12:00:00Z",
}

# A story missing the fields the command has fallbacks for:
# title, points, and created_at.
SPARSE_STORY = {
    "hacker_news_object_id": "1002",
    "title": None,
    "article_url": "https://news.ycombinator.com/item?id=1002",
    "author": "example-author",
    "points": None,
    "number_of_comments": 0,
    "created_at": None,
}

FAKE_STORIES = [COMPLETE_STORY, SPARSE_STORY]


def run_ingest_hacker_news(**command_options):
    """
    Runs the command the way manage.py would, capturing its printed
    output so it can be checked instead of cluttering the test run.
    """
    command_output = StringIO()
    call_command("ingest_hacker_news", stdout=command_output, **command_options)
    return command_output.getvalue()


class IngestHackerNewsCommandTests(TestCase):
    @patch(FETCHER_PATH, return_value=FAKE_STORIES)
    def test_first_run_creates_source_and_articles(self, mock_fetcher):
        run_ingest_hacker_news()

        self.assertEqual(Source.objects.filter(name="Hacker News").count(), 1)
        self.assertEqual(Article.objects.count(), 2)

    @patch(FETCHER_PATH, return_value=FAKE_STORIES)
    def test_second_run_creates_no_duplicates(self, mock_fetcher):
        run_ingest_hacker_news()
        second_run_output = run_ingest_hacker_news()

        # Same data twice: still one Source and two Articles,
        # and the command reports reusing the Source and skipping both.
        self.assertEqual(Source.objects.filter(name="Hacker News").count(), 1)
        self.assertEqual(Article.objects.count(), 2)
        self.assertIn("Using existing Source: Hacker News", second_run_output)
        self.assertIn("Created 0 new articles, skipped 2", second_run_output)

    @patch(FETCHER_PATH, return_value=FAKE_STORIES)
    def test_fields_are_mapped_onto_article(self, mock_fetcher):
        run_ingest_hacker_news()

        article = Article.objects.get(url="https://example.com/complete-story")
        self.assertEqual(article.title, "A complete story")
        self.assertEqual(article.raw_score, 120)
        self.assertEqual(article.source.name, "Hacker News")
        # Parsed from the ISO string into a timezone-aware datetime.
        self.assertIsNotNone(article.published_at.tzinfo)

    @patch(FETCHER_PATH, return_value=FAKE_STORIES)
    def test_missing_fields_fall_back_to_defaults(self, mock_fetcher):
        run_ingest_hacker_news()

        article = Article.objects.get(url="https://news.ycombinator.com/item?id=1002")
        self.assertEqual(article.title, "(untitled)")
        self.assertEqual(article.raw_score, 0)
        self.assertIsNone(article.published_at)

    @patch(FETCHER_PATH, return_value=FAKE_STORIES)
    def test_command_options_are_passed_to_fetcher(self, mock_fetcher):
        run_ingest_hacker_news(limit=50, query="django")

        # The command always requests newest-first results.
        mock_fetcher.assert_called_once_with(
            search_query="django", sort_by_date=True, result_limit=50
        )
