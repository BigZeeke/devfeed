"""
ingest_hacker_news.py

Django management command for DevFeed's Step 3: fetches stories from
Hacker News via articles/ingestion/hn_fetcher.py and writes them into
the Source and Article models against the real Postgres database.

Usage:
    python manage.py ingest_hacker_news
    python manage.py ingest_hacker_news --limit 50
    python manage.py ingest_hacker_news --query django
"""

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from articles.ingestion.hn_fetcher import fetch_hacker_news_stories
from articles.models import Article, Source


class Command(BaseCommand):
    help = "Fetches stories from Hacker News and populates Source/Article models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="How many Hacker News stories to fetch (default: 20).",
        )
        parser.add_argument(
            "--query",
            type=str,
            default=None,
            help="Optional keyword filter (e.g. 'django'). Default: no filter.",
        )

    def handle(self, *args, **options):
        result_limit = options["limit"]
        search_query = options["query"]

        hacker_news_source, source_was_created = Source.objects.get_or_create(
            name="Hacker News",
            defaults={
                "type": Source.SourceType.API,
                "url": "https://hn.algolia.com/api/v1/search",
                "active": True,
            },
        )
        if source_was_created:
            self.stdout.write(self.style.SUCCESS("Created Source: Hacker News"))
        else:
            self.stdout.write("Using existing Source: Hacker News")

        stories = fetch_hacker_news_stories(
            search_query=search_query,
            sort_by_date=True,
            result_limit=result_limit,
        )
        self.stdout.write(f"Fetched {len(stories)} stories from the Hacker News API")

        created_count = 0
        skipped_count = 0

        for story in stories:
            published_at = None
            if story["created_at"]:
                published_at = parse_datetime(story["created_at"])

            article, article_was_created = Article.objects.get_or_create(
                url=story["article_url"],
                defaults={
                    "source": hacker_news_source,
                    "title": story["title"] or "(untitled)",
                    "published_at": published_at,
                    "raw_score": story["points"] or 0,
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
