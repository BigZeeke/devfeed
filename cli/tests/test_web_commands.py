"""Tests for web: which address opens for each API address, with the browser mocked."""

import unittest
from unittest import mock

from command_test_helpers import CommandTestCase


@mock.patch("devfeed_cli.api_client.requests.request")
@mock.patch("devfeed_cli.web_commands.webbrowser.open", return_value=True)
class WebTests(CommandTestCase):
    def test_local_runserver_opens_the_vite_dev_server(self, mock_browser_open, mock_request):
        exit_code, stdout_text, _ = self.run_command(["web"])

        self.assertEqual(exit_code, 0)
        mock_browser_open.assert_called_once_with("http://localhost:5173/")
        self.assertEqual(stdout_text, "Opened http://localhost:5173/ (the browser has its own login)\n")
        # No API call, and no login needed
        mock_request.assert_not_called()

    def test_each_page_has_its_own_path(self, mock_browser_open, mock_request):
        for page_name, expected_url in (
            ("feed", "http://localhost:5173/"),
            ("saved", "http://localhost:5173/saved"),
            ("keywords", "http://localhost:5173/keywords"),
        ):
            with self.subTest(page=page_name):
                mock_browser_open.reset_mock()
                self.run_command(["web", page_name])
                mock_browser_open.assert_called_once_with(expected_url)

    def test_live_site_opens_the_same_origin(self, mock_browser_open, mock_request):
        self.run_command(["--api-url", "44.248.236.123", "web", "saved"])
        mock_browser_open.assert_called_once_with("http://44.248.236.123/saved")

    def test_docker_nginx_address_opens_the_same_origin(self, mock_browser_open, mock_request):
        self.run_command(["--api-url", "127.0.0.1:8080", "web", "keywords"])
        mock_browser_open.assert_called_once_with("http://127.0.0.1:8080/keywords")

    def test_web_url_option_wins(self, mock_browser_open, mock_request):
        self.run_command(["web", "saved", "--web-url", "127.0.0.1:9999/"])
        mock_browser_open.assert_called_once_with("http://127.0.0.1:9999/saved")

    def test_non_http_web_url_is_never_opened(self, mock_browser_open, mock_request):
        exit_code, _, stderr_text = self.run_command(["web", "--web-url", "file:///etc"])
        self.assertEqual(exit_code, 1)
        self.assertIn("only http and https links are opened", stderr_text)
        mock_browser_open.assert_not_called()

    def test_browser_that_fails_to_start_is_reported(self, mock_browser_open, mock_request):
        mock_browser_open.return_value = False
        exit_code, _, stderr_text = self.run_command(["web"])
        self.assertEqual(exit_code, 1)
        self.assertIn("Couldn't open a browser", stderr_text)

    def test_unknown_page_is_rejected(self, mock_browser_open, mock_request):
        with self.assertRaises(SystemExit) as raised:
            self.run_command(["web", "settings"])
        self.assertEqual(raised.exception.code, 2)
        mock_browser_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
