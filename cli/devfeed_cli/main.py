"""Entry point for the "devfeed" command: parses arguments and runs one command.

Every command exits 0 on success and 1 on any error, with a one-line message.
"""

import argparse
import getpass
import os
import sys

from .api_client import ApiClient, normalize_api_url
from .errors import DevfeedError, SessionEndedError
from .session_store import SessionStore

DEFAULT_API_URL = "127.0.0.1:8000"


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
