"""Shared test helpers: a fake API response and a base class for command tests.

The file name doesn't start with "test", so unittest discovery doesn't load
it on its own; the test modules import from it.
"""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from devfeed_cli.main import main
from devfeed_cli.session_store import SessionStore

LOCAL_API_URL = "http://127.0.0.1:8000"
TEST_TOKEN = "f" * 40


def build_mock_response(status_code, json_data=None):
    """A stand-in for requests.Response with the parts api_client reads."""
    mock_response = mock.Mock()
    mock_response.status_code = status_code
    mock_response.content = b"" if json_data is None else b"{}"
    mock_response.json.return_value = json_data
    return mock_response


class CommandTestCase(unittest.TestCase):
    """Gives each test a private session file and captured output."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.session_store = SessionStore(Path(self.temporary_directory.name) / "sessions.json")
        # Keep a DEVFEED_API_URL from the real shell out of the tests
        environment_patcher = mock.patch.dict("os.environ", {}, clear=True)
        environment_patcher.start()
        self.addCleanup(environment_patcher.stop)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def run_command(self, argument_list):
        """Run main() and return (exit code, stdout text, stderr text)."""
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
            exit_code = main(argument_list, session_store=self.session_store)
        return exit_code, captured_stdout.getvalue(), captured_stderr.getvalue()

    def log_in_locally(self):
        """Store a session for the local API, as a real login would."""
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
