"""
github_search_fetcher.py

GitHub has no official trending API, so this fetcher uses the real,
versioned GitHub Search API instead:
https://api.github.com/search/repositories

This does NOT reproduce GitHub's curated trending algorithm (which weighs
recent star velocity in a way GitHub doesn't expose). Instead, it finds
"recently created, highly starred" repositories as a reasonable proxy -
different data, but from a source that won't silently break the way HTML
scraping can.

Auth: works unauthenticated, but the Search API caps unauthenticated
requests at 10/minute (tracked by IP). Authenticated requests (a free
personal access token, no paid tier needed) raise that to 30/minute.
The token only needs "Public Repositories (read-only)" access.

The token is read from the GITHUB_PERSONAL_ACCESS_TOKEN environment
variable. Inside Django, settings.py loads .env, so no loading happens here.
"""

import os
from datetime import date, timedelta

import requests

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")


def _build_request_headers():
    """
    Builds the headers for a GitHub API request. Includes the auth token
    only if one is configured, so this fetcher still works (at the lower
    rate limit) with no token set at all.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_PERSONAL_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_PERSONAL_ACCESS_TOKEN}"
    return headers


def fetch_recently_created_repositories(
    programming_language=None, days_back=7, result_limit=10
):
    """
    Fetch highly-starred repositories created within the last `days_back`
    days, using GitHub's real Search API.

    Args:
        programming_language: optional language filter, e.g. "python".
            None searches across all languages.
        days_back: how many days back to search for repo creation date.
        result_limit: how many results to return (GitHub allows up to 100
            per page; this fetcher keeps it small since it's a personal
            digest, not a bulk data pull).

    Returns:
        A list of dictionaries, one per repository, each with:
        owner, repository_name, full_name, repository_url, description,
        programming_language, total_stars, created_at.
    """
    creation_cutoff_date = date.today() - timedelta(days=days_back)
    search_query = f"created:>{creation_cutoff_date.isoformat()}"
    if programming_language:
        search_query += f" language:{programming_language}"

    response = requests.get(
        GITHUB_SEARCH_URL,
        params={
            "q": search_query,
            "sort": "stars",
            "order": "desc",
            "per_page": result_limit,
        },
        headers=_build_request_headers(),
        timeout=10,
    )
    response.raise_for_status()
    response_data = response.json()

    repositories = []
    for repository_item in response_data.get("items", []):
        repositories.append(
            {
                "owner": repository_item["owner"]["login"],
                "repository_name": repository_item["name"],
                "full_name": repository_item["full_name"],
                "repository_url": repository_item["html_url"],
                "description": repository_item.get("description"),
                "programming_language": repository_item.get("language"),
                "total_stars": repository_item["stargazers_count"],
                "created_at": repository_item["created_at"],
            }
        )

    return repositories


if __name__ == "__main__":
    recent_repositories = fetch_recently_created_repositories(days_back=7)
    print(
        f"Fetched {len(recent_repositories)} recently-created, "
        f"highly-starred repositories:\n"
    )
    for repository in recent_repositories[:5]:
        print(
            f"{repository['full_name']} "
            f"({repository['programming_language']}) "
            f"- {repository['total_stars']} stars"
        )
