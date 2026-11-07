"""Handlers for keywords, keywords follow and keywords unfollow.

Keywords are stored lowercase by the API, so "Django" and "django" are the
same keyword everywhere in the CLI.
"""

from .errors import ApiError, DevfeedError
from .output import clean_text, print_table


def fetch_all_keywords(api_client):
    """GET every page of /api/keywords/ and return one list, alphabetical."""
    all_keywords = []
    page_number = 1
    while True:
        keywords_page = api_client.request(
            "GET", f"/api/keywords/?page={page_number}", needs_login=True
        )
        all_keywords.extend(keywords_page["results"])
        # "next" is null on the last page
        if not keywords_page.get("next"):
            return all_keywords
        page_number += 1


def is_duplicate_keyword_error(error):
    """True for the API's 400 when the user already follows this keyword."""
    if error.status_code != 400 or not isinstance(error.response_data, dict):
        return False
    non_field_messages = error.response_data.get("non_field_errors", [])
    return any("unique" in str(message) for message in non_field_messages)


def handle_keywords(api_client, arguments):
    """List every followed keyword with its weight."""
    all_keywords = fetch_all_keywords(api_client)
    if not all_keywords:
        print("You're not following any keywords. Follow one with: devfeed keywords follow <word>")
        return
    # The weight goes first so the keyword (the longer text) is the last column
    keyword_rows = [[str(keyword["weight"]), keyword["keyword"]] for keyword in all_keywords]
    print_table(["WEIGHT", "KEYWORD"], keyword_rows)
    print(f"\n{len(all_keywords)} followed")


def handle_keywords_follow(api_client, arguments):
    """Follow a keyword; without --weight the API's default (1) applies."""
    request_body = {"keyword": arguments.keyword}
    if arguments.weight is not None:
        request_body["weight"] = arguments.weight
    try:
        new_keyword = api_client.request(
            "POST", "/api/keywords/", json_body=request_body, needs_login=True
        )
    except ApiError as error:
        if is_duplicate_keyword_error(error):
            raise DevfeedError("You're already following that keyword.")
        raise
    print(f"Following {clean_text(new_keyword['keyword'])} (weight {new_keyword['weight']})")


def handle_keywords_unfollow(api_client, arguments):
    """Find the keyword's id in the list, ask, then delete it."""
    wanted_keyword = arguments.keyword.strip().lower()
    matching_keyword = next(
        (
            keyword
            for keyword in fetch_all_keywords(api_client)
            if keyword["keyword"] == wanted_keyword
        ),
        None,
    )
    if matching_keyword is None:
        raise DevfeedError(f"You're not following {clean_text(wanted_keyword)}.")

    if not arguments.yes:
        answer = input(
            f"Stop following {clean_text(matching_keyword['keyword'])} "
            f"(weight {matching_keyword['weight']})? [y/N] "
        )
        # Only an explicit yes removes it; Return or anything else keeps it
        if answer.strip().lower() not in ("y", "yes"):
            print(f"Still following {clean_text(matching_keyword['keyword'])}")
            return

    try:
        api_client.request(
            "DELETE", f"/api/keywords/{matching_keyword['id']}/", needs_login=True
        )
    except ApiError as error:
        # Removed in another client between the list and the delete
        if error.status_code == 404:
            raise DevfeedError(f"You're not following {clean_text(wanted_keyword)}.")
        raise
    print(f"Stopped following {clean_text(matching_keyword['keyword'])}")


def handle_keywords_command(api_client, arguments):
    """Run follow or unfollow when given; plain "devfeed keywords" lists."""
    # The follow and unfollow parsers set keywords_handler; a separate name
    # from "handler" means argparse never has to choose between the two
    keywords_handler = getattr(arguments, "keywords_handler", None) or handle_keywords
    keywords_handler(api_client, arguments)
