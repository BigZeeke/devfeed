"""
Tests for the ingest_github management command.

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
    "articles.management.commands.ingest_github.fetch_recently_created_repositories"
)

# Two fake repositories in the shape the real fetcher returns:
# one with a description, one without.
FAKE_REPOSITORIES = [
    {
        "owner": "example-owner",
        "repository_name": "first-repository",
        "full_name": "example-owner/first-repository",
        "repository_url": "https://github.com/example-owner/first-repository",
        "description": "A described repository",
        "programming_language": "Python",
        "total_stars": 500,
        "created_at": "2026-10-15T12:00:00Z",
    },
    {
        "owner": "example-owner",
        "repository_name": "second-repository",
        "full_name": "example-owner/second-repository",
        "repository_url": "https://github.com/example-owner/second-repository",
        "description": None,
        "programming_language": None,
        "total_stars": 50,
        "created_at": "2026-10-16T08:30:00Z",
    },
]


def run_ingest_github(**command_options):
    """
    Runs the command the way manage.py would, capturing its printed
    output so it can be checked instead of cluttering the test run.
    """
    command_output = StringIO()
    call_command("ingest_github", stdout=command_output, **command_options)
    return command_output.getvalue()


class IngestGithubCommandTests(TestCase):
    @patch(FETCHER_PATH, return_value=FAKE_REPOSITORIES)
    def test_first_run_creates_source_and_articles(self, mock_fetcher):
        run_ingest_github()

        self.assertEqual(Source.objects.filter(name="GitHub").count(), 1)
        self.assertEqual(Article.objects.count(), 2)

    @patch(FETCHER_PATH, return_value=FAKE_REPOSITORIES)
    def test_second_run_creates_no_duplicates(self, mock_fetcher):
        run_ingest_github()
        second_run_output = run_ingest_github()

        # Same data twice: still one Source and two Articles,
        # and the command reports reusing the Source and skipping both.
        self.assertEqual(Source.objects.filter(name="GitHub").count(), 1)
        self.assertEqual(Article.objects.count(), 2)
        self.assertIn("Using existing Source: GitHub", second_run_output)
        self.assertIn("Created 0 new articles, skipped 2", second_run_output)

    @patch(FETCHER_PATH, return_value=FAKE_REPOSITORIES)
    def test_fields_are_mapped_onto_article(self, mock_fetcher):
        run_ingest_github()

        article = Article.objects.get(
            url="https://github.com/example-owner/first-repository"
        )
        self.assertEqual(
            article.title, "example-owner/first-repository: A described repository"
        )
        self.assertEqual(article.raw_score, 500)
        self.assertEqual(article.source.name, "GitHub")
        # Parsed from the ISO string into a timezone-aware datetime.
        self.assertIsNotNone(article.published_at.tzinfo)

    @patch(FETCHER_PATH, return_value=FAKE_REPOSITORIES)
    def test_title_without_description_is_full_name_only(self, mock_fetcher):
        run_ingest_github()

        article = Article.objects.get(
            url="https://github.com/example-owner/second-repository"
        )
        self.assertEqual(article.title, "example-owner/second-repository")

    def test_long_title_is_cut_to_column_length(self):
        # Same repository, but with a description far past the 500-character limit.
        long_description_repository = dict(FAKE_REPOSITORIES[0], description="x" * 1000)

        with patch(FETCHER_PATH, return_value=[long_description_repository]):
            run_ingest_github()

        self.assertEqual(len(Article.objects.get().title), 500)

    @patch(FETCHER_PATH, return_value=FAKE_REPOSITORIES)
    def test_command_options_are_passed_to_fetcher(self, mock_fetcher):
        run_ingest_github(limit=25, language="python", days_back=14)

        mock_fetcher.assert_called_once_with(
            programming_language="python", days_back=14, result_limit=25
        )
