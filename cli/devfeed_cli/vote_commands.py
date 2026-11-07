"""Handlers for vote and unvote: one vote per user and article.

Both use POST /api/articles/<id>/vote/. unvote sends {"direction": null},
which clears the vote and keeps the row (the API has no DELETE here).
"""

from .article_commands import fetch_article
from .errors import ApiError, DevfeedError
from .output import clean_text


def send_vote(api_client, article_id, direction):
    """POST the direction ("up", "down" or None) and return the new counts."""
    try:
        return api_client.request(
            "POST",
            f"/api/articles/{article_id}/vote/",
            json_body={"direction": direction},
            needs_login=True,
        )
    except ApiError as error:
        if error.status_code == 404:
            raise DevfeedError(f"Article {article_id} not found.")
        raise


def describe_counts(vote_response):
    """"up 3, down 1" from the API's vote response."""
    return f"up {vote_response['up_votes']}, down {vote_response['down_votes']}"


def handle_vote(api_client, arguments):
    """Vote an article up or down; voting again switches the vote."""
    vote_response = send_vote(api_client, arguments.article_id, arguments.direction)
    print(
        f"Voted {vote_response['direction']} on article {vote_response['article']} "
        f"({describe_counts(vote_response)})"
    )


def handle_unvote(api_client, arguments):
    """Take back your vote on an article, after asking unless --yes."""
    # The article GET below is public, so check the login before asking
    if api_client.session is None:
        raise DevfeedError("Not logged in. Run: devfeed login")
    if not arguments.yes:
        # Fetch first so a wrong id fails before the question, and the
        # question can show the title (the API can't report your own vote)
        article = fetch_article(api_client, arguments.article_id)
        answer = input(
            f"Remove your vote on article {arguments.article_id} "
            f"({clean_text(article.get('title', ''))})? [y/N] "
        )
        # Only an explicit yes clears it; Return or anything else keeps it
        if answer.strip().lower() not in ("y", "yes"):
            print(f"Kept your vote on article {arguments.article_id}")
            return

    vote_response = send_vote(api_client, arguments.article_id, None)
    print(
        f"Removed your vote on article {vote_response['article']} "
        f"({describe_counts(vote_response)})"
    )
