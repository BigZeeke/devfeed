"""Entry point for the "devfeed" command: parses arguments and runs one command.

Every command exits 0 on success and 1 on any error, with a one-line message.
"""

import argparse
import getpass
import os
import sys

from .api_client import ApiClient, normalize_api_url
from .article_commands import handle_feed, handle_open, handle_show
from .bookmark_commands import handle_note, handle_save, handle_saved, handle_unsave
from .errors import DevfeedError, SessionEndedError
from .keyword_commands import (
    handle_keywords_command,
    handle_keywords_follow,
    handle_keywords_unfollow,
)
from .session_store import SessionStore

DEFAULT_API_URL = "127.0.0.1:8000"


def positive_integer(raw_value):
    """argparse type for ids and page numbers: whole numbers from 1 up."""
    try:
        parsed_value = int(raw_value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw_value!r} is not a whole number")
    if parsed_value < 1:
        raise argparse.ArgumentTypeError(f"{raw_value!r} must be 1 or more")
    return parsed_value


def handle_login(api_client, arguments):
    """Ask for a username and password, then store the token for this server."""
    if api_client.session is not None:
        raise DevfeedError(
            f"Already logged in as {api_client.session['username']} on "
            f"{api_client.api_url}. Run: devfeed logout"
        )
    username = input("Username: ").strip()
    if not username:
        raise DevfeedError("A username is required.")
    # getpass reads the password without showing it on screen
    password = getpass.getpass("Password: ")
    # No token on this request: any invalid token would get 401
    token_response = api_client.request(
        "POST",
        "/api/auth/token/",
        json_body={"username": username, "password": password},
        send_token=False,
    )
    if not isinstance(token_response, dict) or not token_response.get("token"):
        raise DevfeedError("The API did not return a token.")
    api_client.session_store.save(api_client.api_url, username, token_response["token"])
    print(f"Logged in as {username} on {api_client.api_url}")


def handle_logout(api_client, arguments):
    """Delete the token on the server, then the stored session."""
    if api_client.session is None:
        print(f"Not logged in on {api_client.api_url}")
        return
    username = api_client.session["username"]
    try:
        api_client.request("POST", "/api/auth/logout/", needs_login=True)
    except SessionEndedError:
        # The server had already dropped the token; request() deleted the
        # stored session, so the result is the same as a normal log-out
        print(f"Logged out {username} from {api_client.api_url} (the server had already ended the session)")
        return
    api_client.session_store.delete(api_client.api_url)
    print(f"Logged out {username} from {api_client.api_url}")


def handle_whoami(api_client, arguments):
    """Report the stored session for this server without contacting it."""
    if api_client.session is None:
        print(f"Not logged in on {api_client.api_url}")
    else:
        print(f"Logged in as {api_client.session['username']} on {api_client.api_url}")


def build_argument_parser():
    """One subcommand per command, each with its handler attached."""
    argument_parser = argparse.ArgumentParser(
        prog="devfeed", description="Command-line client for the DevFeed API."
    )
    argument_parser.add_argument(
        "--api-url",
        help=f"API address (default: $DEVFEED_API_URL, else {DEFAULT_API_URL})",
    )
    subcommand_parsers = argument_parser.add_subparsers(dest="command", required=True)

    login_parser = subcommand_parsers.add_parser("login", help="log in and store a token")
    login_parser.set_defaults(handler=handle_login)

    logout_parser = subcommand_parsers.add_parser("logout", help="log out and forget the token")
    logout_parser.set_defaults(handler=handle_logout)

    whoami_parser = subcommand_parsers.add_parser("whoami", help="show who is logged in")
    whoami_parser.set_defaults(handler=handle_whoami)

    feed_parser = subcommand_parsers.add_parser("feed", help="list articles, newest first")
    feed_parser.add_argument("--page", type=positive_integer, default=1, help="page number (default 1)")
    feed_parser.set_defaults(handler=handle_feed)

    show_parser = subcommand_parsers.add_parser("show", help="show one article")
    show_parser.add_argument("article_id", type=positive_integer, help="article id from the feed")
    show_parser.add_argument("--open", action="store_true", help="also open the link in the browser")
    show_parser.set_defaults(handler=handle_show)

    open_parser = subcommand_parsers.add_parser("open", help="open an article's link in the browser")
    open_parser.add_argument("article_id", type=positive_integer, help="article id from the feed")
    open_parser.set_defaults(handler=handle_open)

    save_parser = subcommand_parsers.add_parser("save", help="save an article as a bookmark")
    save_parser.add_argument("article_id", type=positive_integer, help="article id from the feed")
    save_parser.add_argument("--note", default="", help="note to keep with the bookmark")
    save_parser.set_defaults(handler=handle_save)

    saved_parser = subcommand_parsers.add_parser("saved", help="list your bookmarks, newest first")
    saved_parser.add_argument("--page", type=positive_integer, default=1, help="page number (default 1)")
    saved_parser.set_defaults(handler=handle_saved)

    note_parser = subcommand_parsers.add_parser("note", help="replace a bookmark's note")
    note_parser.add_argument("bookmark_id", type=positive_integer, help="bookmark id from saved")
    note_parser.add_argument("note_text", help='new note; "" clears it')
    note_parser.set_defaults(handler=handle_note)

    unsave_parser = subcommand_parsers.add_parser("unsave", help="remove a bookmark")
    unsave_parser.add_argument("bookmark_id", type=positive_integer, help="bookmark id from saved")
    unsave_parser.add_argument("--yes", action="store_true", help="remove without asking first")
    unsave_parser.set_defaults(handler=handle_unsave)

    keywords_parser = subcommand_parsers.add_parser(
        "keywords", help="list followed keywords, or follow / unfollow one"
    )
    keywords_parser.set_defaults(handler=handle_keywords_command)
    keywords_subcommand_parsers = keywords_parser.add_subparsers(dest="keywords_action")

    follow_parser = keywords_subcommand_parsers.add_parser("follow", help="follow a keyword")
    follow_parser.add_argument("keyword", help="word to follow (stored lowercase)")
    follow_parser.add_argument("--weight", type=int, help="whole number; the API's default is 1")
    follow_parser.set_defaults(keywords_handler=handle_keywords_follow)

    unfollow_parser = keywords_subcommand_parsers.add_parser("unfollow", help="stop following a keyword")
    unfollow_parser.add_argument("keyword", help="followed word (any case)")
    unfollow_parser.add_argument("--yes", action="store_true", help="stop following without asking first")
    unfollow_parser.set_defaults(keywords_handler=handle_keywords_unfollow)

    return argument_parser


def choose_api_url(arguments):
    """--api-url first, then DEVFEED_API_URL, then the local default."""
    raw_api_url = arguments.api_url or os.environ.get("DEVFEED_API_URL") or DEFAULT_API_URL
    return normalize_api_url(raw_api_url)


def main(argument_list=None, session_store=None):
    """Run one command; return the exit code (also used by the tests)."""
    arguments = build_argument_parser().parse_args(argument_list)
    try:
        api_client = ApiClient(choose_api_url(arguments), session_store or SessionStore())
        arguments.handler(api_client, arguments)
    except DevfeedError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or Ctrl+D at a prompt
        print("\nCancelled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
