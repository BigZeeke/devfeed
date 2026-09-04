"""
hn_fetcher.py

Hacker News has a real, documented, authentication-free search API
via Algolia: https://hn.algolia.com/api/v1/search

This is DevFeed's first ingestion source (per the build order: get one
source working end-to-end before adding GitHub/RSS).
"""

import requests

HACKER_NEWS_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def _build_discussion_page_url(story_object_id):
    """
    Builds a fallback URL pointing at the story's Hacker News discussion
    page. Used when a story has no external url (e.g. "Ask HN" posts,
    which are text-only and have url=None in the Algolia response), so
    every returned article still has a usable link.
    """
    return f"https://news.ycombinator.com/item?id={story_object_id}"


def fetch_hacker_news_stories(search_query=None, sort_by_date=True, result_limit=20):
    """
    Fetch stories from Hacker News via the Algolia Search API.

    Args:
        search_query: optional free-text filter (e.g. "django"). None
            returns stories with no keyword filter applied.
        sort_by_date: if True, hits the search_by_date endpoint (newest
            first). If False, hits the relevance/popularity-ranked
            search endpoint instead.
        result_limit: how many results to request per page (Algolia
            caps this around 1000, but a personal digest has no reason
            to pull that many at once).

    Returns:
        A list of dictionaries, one per story, each with:
        hacker_news_object_id, title, article_url, author,
        points, number_of_comments, created_at.
    """
    request_path = "search_by_date" if sort_by_date else "search"
    request_url = f"{HACKER_NEWS_SEARCH_URL.rsplit('/', 1)[0]}/{request_path}"

    request_parameters = {
        "tags": "story",
        "hitsPerPage": result_limit,
    }
    if search_query:
        request_parameters["query"] = search_query

    response = requests.get(request_url, params=request_parameters, timeout=10)
    response.raise_for_status()
    response_data = response.json()

    stories = []
    for hit in response_data.get("hits", []):
        story_object_id = hit["objectID"]
        article_url = hit.get("url") or _build_discussion_page_url(story_object_id)

        stories.append(
            {
                "hacker_news_object_id": story_object_id,
                "title": hit.get("title") or hit.get("story_title"),
                "article_url": article_url,
                "author": hit.get("author"),
                "points": hit.get("points"),
                "number_of_comments": hit.get("num_comments"),
                "created_at": hit.get("created_at"),
            }
        )

    return stories


if __name__ == "__main__":
    recent_stories = fetch_hacker_news_stories(sort_by_date=True, result_limit=10)
    print(f"Fetched {len(recent_stories)} recent Hacker News stories:\n")
    for story in recent_stories[:5]:
        print(f"[{story['points']} pts] {story['title']} - {story['article_url']}")
