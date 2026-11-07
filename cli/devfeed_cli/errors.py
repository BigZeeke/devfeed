"""Exceptions that main() turns into a one-line message and exit code 1."""


class DevfeedError(Exception):
    """Any failure the user should see as a single line."""


class ApiError(DevfeedError):
    """The API answered with an error status; keeps the status and body."""

    def __init__(self, message, status_code, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class SessionEndedError(ApiError):
    """The API rejected the stored token (401); the session was deleted."""
