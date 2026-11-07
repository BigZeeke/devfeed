"""Handlers for feed, show and open: reading articles, no login needed."""

import math
import webbrowser
from urllib.parse import urlparse

from .errors import ApiError, DevfeedError
from .output import format_date, print_details, print_table

# Matches the API's page size (REST_FRAMEWORK PAGE_SIZE in settings.py)
ARTICLES_PAGE_SIZE = 20


def open_in_browser(article_url):
    """Open an article link, but only http and https links."""
    if urlparse(article_url or "").scheme not in ("http", "https"):
        raise DevfeedError("Not opening this link: only http and https links are opened.")
    # webbrowser.open returns False when no browser could be started
    if not webbrowser.open(article_url):
        raise DevfeedError(f"Couldn't open a browser for {article_url}")


def fetch_article(api_client, article_id):
    """GET one article; a missing id becomes a clear message."""
    try:
        return api_client.request("GET", f"/api/articles/{article_id}/")
    except ApiError as error:
        if error.status_code == 404:
            raise DevfeedError(f"Article {article_id} not found.")
        raise


def handle_feed(api_client, arguments):
    """Print one page of the feed, newest first, with a page footer."""
    try:
        feed_page = api_client.request("GET", f"/api/articles/?page={arguments.page}")
    except ApiError as error:
        # DRF answers 404 for a page number past the last page
        if error.status_code == 404:
            raise DevfeedError(f"Page {arguments.page} doesn't exist.")
        raise

    article_count = feed_page["count"]
    if article_count == 0:
        print("No articles yet.")
        return

    article_rows = [
        [
            str(article["id"]),
            article.get("source_name", ""),
            format_date(article.get("published_at")),
            str(article.get("raw_score", 0)),
            article.get("title", ""),
        ]
        for article in feed_page["results"]
    ]
    print_table(["ID", "SOURCE", "DATE", "SCORE", "TITLE"], article_rows)

    page_count = math.ceil(article_count / ARTICLES_PAGE_SIZE)
    print(f"\nPage {arguments.page} of {page_count} ({article_count} articles)")


def handle_show(api_client, arguments):
    """Print one article's details; --open also opens its link."""
    article = fetch_article(api_client, arguments.article_id)
    tag_labels = [tag["label"] for tag in article.get("tags", [])]
    print_details(
        [
            ("ID", str(article["id"])),
            ("Title", article.get("title", "")),
            ("Source", article.get("source_name", "")),
            ("Published", format_date(article.get("published_at"))),
            ("Score", str(article.get("raw_score", 0))),
            ("Tags", ", ".join(tag_labels) if tag_labels else "none"),
            ("URL", article.get("url", "")),
        ]
    )
    if arguments.open:
        open_in_browser(article.get("url"))


def handle_open(api_client, arguments):
    """Open one article's link without printing its details."""
    article = fetch_article(api_client, arguments.article_id)
    open_in_browser(article.get("url"))
    print(f"Opened article {arguments.article_id} in the browser")
