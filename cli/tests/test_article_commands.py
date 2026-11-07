"""Tests for feed, show and open with the API and the browser mocked."""

import os
import unittest
from unittest import mock

from command_test_helpers import (
    LOCAL_API_URL,
    TEST_TOKEN,
    CommandTestCase,
    build_mock_response,
)


def build_article(article_id, title, url="https://example.com/story", tags=None):
    """One article as the API returns it."""
    return {
        "id": article_id,
        "source": 1,
        "source_name": "Hacker News",
        "title": title,
        "url": url,
        "published_at": "2026-11-03T14:05:00Z",
        "raw_score": 120,
        "is_read": False,
        "created_at": "2026-11-03T15:00:00Z",
        "tags": tags or [],
    }


def build_feed_page(articles, count=None):
    """A paginated list response: {count, next, previous, results}."""
    return {
        "count": len(articles) if count is None else count,
        "next": None,
        "previous": None,
        "results": articles,
    }


# A fixed terminal width so table output is the same on every machine
FIXED_TERMINAL_SIZE = os.terminal_size((80, 24))


@mock.patch("devfeed_cli.output.shutil.get_terminal_size", return_value=FIXED_TERMINAL_SIZE)
@mock.patch("devfeed_cli.api_client.requests.request")
class FeedTests(CommandTestCase):
    def test_feed_prints_rows_and_page_footer(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200, build_feed_page([build_article(49, "First story"), build_article(50, "Second story")], count=45)
        )
        exit_code, stdout_text, _ = self.run_command(["feed"])

        self.assertEqual(exit_code, 0)
        output_lines = stdout_text.splitlines()
        self.assertEqual(output_lines[0].split(), ["ID", "SOURCE", "DATE", "SCORE", "TITLE"])
        self.assertIn("49  Hacker News  2026-11-03  120    First story", output_lines[1])
        # 45 articles at 20 per page is 3 pages
        self.assertEqual(output_lines[-1], "Page 1 of 3 (45 articles)")
        method, url = mock_request.call_args.args
        self.assertEqual((method, url), ("GET", f"{LOCAL_API_URL}/api/articles/?page=1"))

    def test_page_option_is_sent(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200, build_feed_page([build_article(1, "Old story")], count=45)
        )
        _, stdout_text, _ = self.run_command(["feed", "--page", "3"])
        self.assertTrue(mock_request.call_args.args[1].endswith("/api/articles/?page=3"))
        self.assertTrue(stdout_text.endswith("Page 3 of 3 (45 articles)\n"))

    def test_page_past_the_end_gives_a_clear_message(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(404, {"detail": "Invalid page."})
        exit_code, _, stderr_text = self.run_command(["feed", "--page", "9"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Page 9 doesn't exist.\n")

    def test_page_zero_is_rejected_before_any_request(self, mock_request, mock_terminal_size):
        with self.assertRaises(SystemExit) as raised:
            self.run_command(["feed", "--page", "0"])
        # argparse exits with 2 for invalid arguments
        self.assertEqual(raised.exception.code, 2)
        mock_request.assert_not_called()

    def test_empty_feed(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(200, build_feed_page([]))
        _, stdout_text, _ = self.run_command(["feed"])
        self.assertEqual(stdout_text, "No articles yet.\n")

    def test_long_titles_are_shortened_to_the_terminal_width(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200, build_feed_page([build_article(7, "A" * 200)])
        )
        _, stdout_text, _ = self.run_command(["feed"])
        article_line = stdout_text.splitlines()[1]
        self.assertEqual(len(article_line), 80)
        self.assertTrue(article_line.endswith("…"))

    def test_control_characters_in_titles_are_not_printed(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200, build_feed_page([build_article(7, "Safe\x1b[2Jtitle\nnext")])
        )
        _, stdout_text, _ = self.run_command(["feed"])
        self.assertNotIn("\x1b", stdout_text)
        self.assertIn("Safe [2Jtitle next", stdout_text)

    def test_feed_without_login_sends_no_token(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(200, build_feed_page([]))
        self.run_command(["feed"])
        self.assertNotIn("Authorization", mock_request.call_args.kwargs["headers"])

    def test_a_401_on_any_command_deletes_the_stored_session(self, mock_request, mock_terminal_size):
        self.log_in_locally()
        mock_request.return_value = build_mock_response(401, {"detail": "Invalid token."})
        exit_code, _, stderr_text = self.run_command(["feed"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Session ended. Run: devfeed login\n")
        self.assertIsNone(self.session_store.read(LOCAL_API_URL))
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"], f"Token {TEST_TOKEN}"
        )


@mock.patch("devfeed_cli.article_commands.webbrowser.open", return_value=True)
@mock.patch("devfeed_cli.api_client.requests.request")
class ShowAndOpenTests(CommandTestCase):
    def test_show_prints_the_details(self, mock_request, mock_browser_open):
        mock_request.return_value = build_mock_response(
            200, build_article(49, "First story", tags=[{"id": 1, "label": "django"}, {"id": 2, "label": "python"}])
        )
        exit_code, stdout_text, _ = self.run_command(["show", "49"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout_text,
            "ID:         49\n"
            "Title:      First story\n"
            "Source:     Hacker News\n"
            "Published:  2026-11-03\n"
            "Score:      120\n"
            "Tags:       django, python\n"
            "URL:        https://example.com/story\n",
        )
        self.assertTrue(mock_request.call_args.args[1].endswith("/api/articles/49/"))
        mock_browser_open.assert_not_called()

    def test_show_without_tags_says_none(self, mock_request, mock_browser_open):
        mock_request.return_value = build_mock_response(200, build_article(49, "First story"))
        _, stdout_text, _ = self.run_command(["show", "49"])
        self.assertIn("Tags:       none\n", stdout_text)

    def test_show_with_open_opens_the_link(self, mock_request, mock_browser_open):
        mock_request.return_value = build_mock_response(200, build_article(49, "First story"))
        exit_code, _, _ = self.run_command(["show", "49", "--open"])
        self.assertEqual(exit_code, 0)
        mock_browser_open.assert_called_once_with("https://example.com/story")

    def test_open_opens_the_link_without_details(self, mock_request, mock_browser_open):
        mock_request.return_value = build_mock_response(200, build_article(49, "First story"))
        exit_code, stdout_text, _ = self.run_command(["open", "49"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Opened article 49 in the browser\n")
        mock_browser_open.assert_called_once_with("https://example.com/story")

    def test_non_http_links_are_never_opened(self, mock_request, mock_browser_open):
        mock_request.return_value = build_mock_response(
            200, build_article(49, "Bad link", url="javascript:alert(1)")
        )
        exit_code, _, stderr_text = self.run_command(["open", "49"])
        self.assertEqual(exit_code, 1)
        self.assertIn("only http and https links are opened", stderr_text)
        mock_browser_open.assert_not_called()

    def test_browser_that_fails_to_start_is_reported(self, mock_request, mock_browser_open):
        mock_browser_open.return_value = False
        mock_request.return_value = build_mock_response(200, build_article(49, "First story"))
        exit_code, _, stderr_text = self.run_command(["open", "49"])
        self.assertEqual(exit_code, 1)
        self.assertIn("Couldn't open a browser", stderr_text)

    def test_missing_article_gives_a_clear_message(self, mock_request, mock_browser_open):
        mock_request.return_value = build_mock_response(404, {"detail": "No Article matches the given query."})
        exit_code, _, stderr_text = self.run_command(["show", "9999"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Article 9999 not found.\n")


if __name__ == "__main__":
    unittest.main()
