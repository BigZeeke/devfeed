"""Tests for login, logout and whoami with the API mocked (no server needed)."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import requests

from devfeed_cli.api_client import normalize_api_url
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


class NormalizeApiUrlTests(unittest.TestCase):
    def test_adds_http_and_removes_trailing_slash(self):
        self.assertEqual(normalize_api_url("127.0.0.1:8000/"), LOCAL_API_URL)

    def test_keeps_an_existing_scheme(self):
        self.assertEqual(normalize_api_url("https://example.com"), "https://example.com")


class ApiUrlChoiceTests(CommandTestCase):
    def test_environment_variable_is_used_without_the_option(self):
        with mock.patch.dict("os.environ", {"DEVFEED_API_URL": "44.248.236.123"}):
            exit_code, stdout_text, _ = self.run_command(["whoami"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Not logged in on http://44.248.236.123\n")

    def test_option_wins_over_the_environment_variable(self):
        with mock.patch.dict("os.environ", {"DEVFEED_API_URL": "44.248.236.123"}):
            _, stdout_text, _ = self.run_command(["--api-url", "127.0.0.1:8000", "whoami"])
        self.assertEqual(stdout_text, f"Not logged in on {LOCAL_API_URL}\n")


class LoginTests(CommandTestCase):
    @mock.patch("devfeed_cli.main.getpass.getpass", return_value="Correct-Horse-Battery-42")
    @mock.patch("builtins.input", return_value="curl_test_user")
    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_login_stores_the_token_and_never_prints_it(self, mock_request, mock_input, mock_getpass):
        mock_request.return_value = build_mock_response(200, {"token": TEST_TOKEN})
        exit_code, stdout_text, stderr_text = self.run_command(["login"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, f"Logged in as curl_test_user on {LOCAL_API_URL}\n")
        self.assertNotIn(TEST_TOKEN, stdout_text + stderr_text)
        self.assertEqual(
            self.session_store.read(LOCAL_API_URL),
            {"username": "curl_test_user", "token": TEST_TOKEN},
        )
        # The log-in request goes to the token endpoint without any token header
        method, url = mock_request.call_args.args
        self.assertEqual((method, url), ("POST", f"{LOCAL_API_URL}/api/auth/token/"))
        self.assertNotIn("Authorization", mock_request.call_args.kwargs["headers"])
        self.assertEqual(
            mock_request.call_args.kwargs["json"],
            {"username": "curl_test_user", "password": "Correct-Horse-Battery-42"},
        )

    @mock.patch("devfeed_cli.main.getpass.getpass", return_value="wrong-password")
    @mock.patch("builtins.input", return_value="curl_test_user")
    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_wrong_password_prints_the_api_message(self, mock_request, mock_input, mock_getpass):
        mock_request.return_value = build_mock_response(
            400, {"non_field_errors": ["Unable to log in with provided credentials."]}
        )
        exit_code, stdout_text, stderr_text = self.run_command(["login"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Unable to log in with provided credentials.\n")
        self.assertIsNone(self.session_store.read(LOCAL_API_URL))

    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_login_when_already_logged_in_stops_without_a_request(self, mock_request):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
        exit_code, _, stderr_text = self.run_command(["login"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Already logged in as curl_test_user", stderr_text)
        mock_request.assert_not_called()

    @mock.patch("devfeed_cli.main.getpass.getpass", return_value="any-password")
    @mock.patch("builtins.input", return_value="curl_test_user")
    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_unreachable_server_gives_one_line(self, mock_request, mock_input, mock_getpass):
        mock_request.side_effect = requests.exceptions.ConnectionError()
        exit_code, _, stderr_text = self.run_command(["login"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, f"Error: Can't reach the DevFeed API at {LOCAL_API_URL}\n")

    @mock.patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_ctrl_c_at_the_prompt_exits_1(self, mock_input):
        exit_code, _, stderr_text = self.run_command(["login"])
        self.assertEqual(exit_code, 1)
        self.assertIn("Cancelled.", stderr_text)


class LogoutTests(CommandTestCase):
    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_logout_sends_the_token_and_deletes_the_session(self, mock_request):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
        mock_request.return_value = build_mock_response(204)
        exit_code, stdout_text, _ = self.run_command(["logout"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, f"Logged out curl_test_user from {LOCAL_API_URL}\n")
        self.assertIsNone(self.session_store.read(LOCAL_API_URL))
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"], f"Token {TEST_TOKEN}"
        )

    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_logout_after_server_401_still_deletes_the_session(self, mock_request):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
        mock_request.return_value = build_mock_response(401, {"detail": "Invalid token."})
        exit_code, stdout_text, _ = self.run_command(["logout"])

        self.assertEqual(exit_code, 0)
        self.assertIn("the server had already ended the session", stdout_text)
        self.assertIsNone(self.session_store.read(LOCAL_API_URL))

    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_logout_keeps_the_session_when_the_server_is_unreachable(self, mock_request):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
        mock_request.side_effect = requests.exceptions.ConnectionError()
        exit_code, _, _ = self.run_command(["logout"])

        self.assertEqual(exit_code, 1)
        # The token is still valid on the server, so it isn't forgotten
        self.assertIsNotNone(self.session_store.read(LOCAL_API_URL))

    @mock.patch("devfeed_cli.api_client.requests.request")
    def test_logout_when_not_logged_in_sends_nothing(self, mock_request):
        exit_code, stdout_text, _ = self.run_command(["logout"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, f"Not logged in on {LOCAL_API_URL}\n")
        mock_request.assert_not_called()


class WhoamiTests(CommandTestCase):
    def test_whoami_shows_the_stored_username(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
        exit_code, stdout_text, _ = self.run_command(["whoami"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, f"Logged in as curl_test_user on {LOCAL_API_URL}\n")
        self.assertNotIn(TEST_TOKEN, stdout_text)

    def test_whoami_is_per_server(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", TEST_TOKEN)
        _, stdout_text, _ = self.run_command(["--api-url", "44.248.236.123", "whoami"])
        self.assertEqual(stdout_text, "Not logged in on http://44.248.236.123\n")


if __name__ == "__main__":
    unittest.main()
