"""Handlers for save, saved, note and unsave: the logged-in user's bookmarks.

Saving uses the article id (shown by feed); note and unsave use the
bookmark id (shown by saved).
"""

import math

from .errors import ApiError, DevfeedError
from .output import clean_text, print_table, shorten

# Matches the API's page size (REST_FRAMEWORK PAGE_SIZE in settings.py)
BOOKMARKS_PAGE_SIZE = 20
# Titles are cut to this width in the saved list so the note column stays visible
SAVED_TITLE_WIDTH = 40


def is_duplicate_bookmark_error(error):
    """True for the API's 400 when the user already saved this article."""
    if error.status_code != 400 or not isinstance(error.response_data, dict):
        return False
    non_field_messages = error.response_data.get("non_field_errors", [])
    return any("unique" in str(message) for message in non_field_messages)


def handle_save(api_client, arguments):
    """Save an article as a bookmark, with an optional note."""
    try:
        new_bookmark = api_client.request(
            "POST",
            "/api/bookmarks/",
            json_body={"article": arguments.article_id, "note": arguments.note},
            needs_login=True,
        )
    except ApiError as error:
        if is_duplicate_bookmark_error(error):
            raise DevfeedError("You already saved this article.")
        # An unknown article id is a field error on "article", not a 404
        if error.status_code == 400 and "article" in (error.response_data or {}):
            raise DevfeedError(f"Article {arguments.article_id} not found.")
        raise
    print(
        f"Saved article {new_bookmark['article']} as bookmark {new_bookmark['id']}: "
        f"{new_bookmark.get('article_title', '')}"
    )


def handle_saved(api_client, arguments):
    """Print one page of the user's bookmarks, newest first."""
    try:
        bookmarks_page = api_client.request(
            "GET", f"/api/bookmarks/?page={arguments.page}", needs_login=True
        )
    except ApiError as error:
        # DRF answers 404 for a page number past the last page
        if error.status_code == 404:
            raise DevfeedError(f"Page {arguments.page} doesn't exist.")
        raise

    bookmark_count = bookmarks_page["count"]
    if bookmark_count == 0:
        print("No saved articles yet. Save one with: devfeed save <article-id>")
        return

    bookmark_rows = [
        [
            str(bookmark["id"]),
            str(bookmark["article"]),
            "yes" if bookmark.get("is_read") else "no",
            shorten(bookmark.get("article_title", ""), SAVED_TITLE_WIDTH),
            bookmark.get("note", ""),
        ]
        for bookmark in bookmarks_page["results"]
    ]
    print_table(["ID", "ARTICLE", "READ", "TITLE", "NOTE"], bookmark_rows)

    page_count = math.ceil(bookmark_count / BOOKMARKS_PAGE_SIZE)
    print(f"\nPage {arguments.page} of {page_count} ({bookmark_count} saved)")


def handle_note(api_client, arguments):
    """Replace a bookmark's note; an empty string clears it."""
    try:
        updated_bookmark = api_client.request(
            "PATCH",
            f"/api/bookmarks/{arguments.bookmark_id}/",
            json_body={"note": arguments.note_text},
            needs_login=True,
        )
    except ApiError as error:
        # Also what another user's bookmark id returns
        if error.status_code == 404:
            raise DevfeedError(f"Bookmark {arguments.bookmark_id} not found.")
        raise
    print(
        f"Updated the note on bookmark {updated_bookmark['id']}: "
        f"{updated_bookmark.get('article_title', '')}"
    )


def handle_unsave(api_client, arguments):
    """Delete a bookmark by its bookmark id, after asking unless --yes."""
    bookmark_path = f"/api/bookmarks/{arguments.bookmark_id}/"
    try:
        # Fetch first so a wrong id fails before the question, and the
        # question can show which article would be removed
        bookmark = api_client.request("GET", bookmark_path, needs_login=True)
    except ApiError as error:
        # Also what another user's bookmark id returns
        if error.status_code == 404:
            raise DevfeedError(f"Bookmark {arguments.bookmark_id} not found.")
        raise

    if not arguments.yes:
        answer = input(
            f"Remove bookmark {arguments.bookmark_id} "
            f"({clean_text(bookmark.get('article_title', ''))})? [y/N] "
        )
        # Only an explicit yes removes it; Return or anything else keeps it
        if answer.strip().lower() not in ("y", "yes"):
            print(f"Kept bookmark {arguments.bookmark_id}")
            return

    try:
        api_client.request("DELETE", bookmark_path, needs_login=True)
    except ApiError as error:
        if error.status_code == 404:
            raise DevfeedError(f"Bookmark {arguments.bookmark_id} not found.")
        raise
    print(f"Removed bookmark {arguments.bookmark_id}")
