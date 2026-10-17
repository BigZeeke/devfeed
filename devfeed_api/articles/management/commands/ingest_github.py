"""
ingest_github.py

Django management command that fetches recently created, highly starred
repositories from the GitHub Search API via
articles/ingestion/github_search_fetcher.py and writes them into the
Source and Article models against the real Postgres database.

Usage:
    python manage.py ingest_github
    python manage.py ingest_github --limit 25
    python manage.py ingest_github --language python
    python manage.py ingest_github --days-back 14
"""

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

# The URL is imported rather than retyped so Source.url always matches
# the endpoint the fetcher actually calls.
from articles.ingestion.github_search_fetcher import (
    GITHUB_SEARCH_URL,
    fetch_recently_created_repositories,
)
from articles.models import Article, Source

# Matches max_length on Article.title.
ARTICLE_TITLE_MAX_LENGTH = 500


def build_article_title(repository):
    """
    Builds an Article title for a repository, since repositories have no
    title of their own: "owner/name: description", or just "owner/name"
    when the repository has no description. Cut to the Article.title
    column length so a long description can't cause a database error.
    """
    article_title = repository["full_name"]
    if repository["description"]:
        article_title = f"{article_title}: {repository['description']}"
    return article_title[:ARTICLE_TITLE_MAX_LENGTH]


class Command(BaseCommand):
    help = "Fetches recently created, highly starred GitHub repositories and populates Source/Article models."

    def add_arguments(self, parser):
        # Each option maps directly onto a fetcher parameter.
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="How many repositories to fetch (default: 10, GitHub maximum: 100).",
        )
        parser.add_argument(
            "--language",
            type=str,
            default=None,
            help="Optional programming language filter (e.g. 'python'). Default: all languages.",
        )
        parser.add_argument(
            "--days-back",
            type=int,
            default=7,
            help="Only include repositories created within this many days (default: 7).",
        )

    def handle(self, *args, **options):
        # argparse converts "--days-back" to the key "days_back".
        result_limit = options["limit"]
        programming_language = options["language"]
        days_back = options["days_back"]

        # One Source row for GitHub, created on the first run and reused after.
        github_source, source_was_created = Source.objects.get_or_create(
            name="GitHub",
            defaults={
                "type": Source.SourceType.API,
                "url": GITHUB_SEARCH_URL,
                "active": True,
            },
        )
        if source_was_created:
            self.stdout.write(self.style.SUCCESS("Created Source: GitHub"))
        else:
            self.stdout.write("Using existing Source: GitHub")

        repositories = fetch_recently_created_repositories(
            programming_language=programming_language,
            days_back=days_back,
            result_limit=result_limit,
        )
        self.stdout.write(
            f"Fetched {len(repositories)} repositories from the GitHub Search API")

        created_count = 0
        skipped_count = 0

        for repository in repositories:
            # GitHub returns ISO 8601 strings; Article.published_at needs a datetime.
            published_at = None
            if repository["created_at"]:
                published_at = parse_datetime(repository["created_at"])

            # Article.url is unique, so get_or_create makes reruns idempotent.
            # Existing rows are left unchanged, including their star count.
            article, article_was_created = Article.objects.get_or_create(
                url=repository["repository_url"],
                defaults={
                    "source": github_source,
                    "title": build_article_title(repository),
                    "published_at": published_at,
                    "raw_score": repository["total_stars"] or 0,
                },
            )

            if article_was_created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count} new articles, "
                f"skipped {skipped_count} already-existing articles."
            )
        )
