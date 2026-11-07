"""The one place that talks to the DevFeed API.

Sends the stored token when there is one, and turns error responses into
DevfeedError messages that main() prints on one line.
"""

import requests

from .errors import ApiError, DevfeedError, SessionEndedError

REQUEST_TIMEOUT_SECONDS = 10


def normalize_api_url(raw_api_url):
    """Add http:// when no scheme is given and drop trailing slashes.

    "127.0.0.1:8000" and "http://127.0.0.1:8000/" both become
    "http://127.0.0.1:8000", so they share one stored session.
    """
    api_url = raw_api_url.strip().rstrip("/")
    if "://" not in api_url:
        api_url = "http://" + api_url
    return api_url


def describe_validation_errors(response_data):
    """Turn a DRF 400 body into one line, e.g. "note: Ensure this field ..."."""
    if not isinstance(response_data, dict):
        return "The API rejected the request."
    described_errors = []
    for field_name, field_messages in response_data.items():
        if not isinstance(field_messages, list):
            field_messages = [field_messages]
        joined_messages = " ".join(str(field_message) for field_message in field_messages)
        # Errors not tied to one field are shown without a field name
        if field_name in ("non_field_errors", "detail"):
            described_errors.append(joined_messages)
        else:
            described_errors.append(f"{field_name}: {joined_messages}")
    return "; ".join(described_errors) or "The API rejected the request."


class ApiClient:
    """Sends requests to one API address with that address's stored session."""

    def __init__(self, api_url, session_store):
        self.api_url = api_url
        self.session_store = session_store
        self.session = session_store.read(api_url)

    def request(self, method, path, json_body=None, needs_login=False, send_token=True):
        """Send one request and return the parsed JSON, or None for 204.

        needs_login: stop before sending if there is no stored session.
        send_token: False for log-in, since any invalid token gets 401.
        """
        if needs_login and self.session is None:
            raise DevfeedError("Not logged in. Run: devfeed login")

        request_headers = {"Accept": "application/json"}
        if send_token and self.session is not None:
            request_headers["Authorization"] = f"Token {self.session['token']}"

        try:
            response = requests.request(
                method,
                self.api_url + path,
                json=json_body,
                headers=request_headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise DevfeedError(f"Can't reach the DevFeed API at {self.api_url}")

        if response.status_code == 401:
            # The server no longer accepts the stored token: forget it
            self.session_store.delete(self.api_url)
            self.session = None
            raise SessionEndedError("Session ended. Run: devfeed login", 401)

        response_data = None
        if response.status_code != 204 and response.content:
            try:
                response_data = response.json()
            except ValueError:
                raise DevfeedError(
                    f"The API at {self.api_url} returned a response that isn't JSON "
                    f"(HTTP {response.status_code})."
                )

        if response.status_code == 400:
            raise ApiError(describe_validation_errors(response_data), 400, response_data)
        if response.status_code == 404:
            # Also what another user's bookmark or keyword returns
            raise ApiError("Not found.", 404, response_data)
        if response.status_code >= 400:
            raise ApiError(
                f"The API returned HTTP {response.status_code}.",
                response.status_code,
                response_data,
            )
        return response_data
