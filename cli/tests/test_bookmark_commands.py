"""Tests for save, saved, note and unsave with the API mocked."""

import os
import unittest
from unittest import mock

from command_test_helpers import (
    LOCAL_API_URL,
    TEST_TOKEN,
    CommandTestCase,
    build_mock_response,
)

# A fixed terminal width so table output is the same on every machine
FIXED_TERMINAL_SIZE = os.terminal_size((100, 24))


def build_bookmark(bookmark_id, article_id, title, note="", is_read=False):
    """One bookmark as the API returns it."""
    return {
        "id": bookmark_id,
        "article": article_id,
        "article_title": title,
        "note": note,
        "is_read": is_read,
        "created_at": "2026-11-05T18:00:00Z",
        "updated_at": "2026-11-05T18:00:00Z",
    }


@mock.patch("devfeed_cli.api_client.requests.request")
class LoginRequiredTests(CommandTestCase):
    def test_every_bookmark_command_stops_when_logged_out(self, mock_request):
        for argument_list in (["save", "49"], ["saved"], ["note", "3", "text"], ["unsave", "3"]):
            with self.subTest(command=argument_list[0]):
                exit_code, _, stderr_text = self.run_command(argument_list)
                self.assertEqual(exit_code, 1)
                self.assertEqual(stderr_text, "Error: Not logged in. Run: devfeed login\n")
        mock_request.assert_not_called()


@mock.patch("devfeed_cli.api_client.requests.request")
class SaveTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.log_in_locally()

    def test_save_with_note_posts_article_and_note(self, mock_request):
        mock_request.return_value = build_mock_response(
            201, build_bookmark(6, 49, "chenglou/handwired", note="Read later")
        )
        exit_code, stdout_text, _ = self.run_command(["save", "49", "--note", "Read later"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Saved article 49 as bookmark 6: chenglou/handwired\n")
        method, url = mock_request.call_args.args
        self.assertEqual((method, url), ("POST", f"{LOCAL_API_URL}/api/bookmarks/"))
        self.assertEqual(mock_request.call_args.kwargs["json"], {"article": 49, "note": "Read later"})
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"], f"Token {TEST_TOKEN}"
        )

    def test_save_without_note_sends_an_empty_note(self, mock_request):
        mock_request.return_value = build_mock_response(201, build_bookmark(6, 49, "Title"))
        self.run_command(["save", "49"])
        self.assertEqual(mock_request.call_args.kwargs["json"], {"article": 49, "note": ""})

    def test_duplicate_save_gives_the_friendly_message(self, mock_request):
        mock_request.return_value = build_mock_response(
            400, {"non_field_errors": ["The fields user, article must make a unique set."]}
        )
        exit_code, _, stderr_text = self.run_command(["save", "49"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: You already saved this article.\n")

    def test_unknown_article_gives_a_clear_message(self, mock_request):
        mock_request.return_value = build_mock_response(
            400, {"article": ['Invalid pk "9999" - object does not exist.']}
        )
        _, _, stderr_text = self.run_command(["save", "9999"])
        self.assertEqual(stderr_text, "Error: Article 9999 not found.\n")

    def test_note_too_long_shows_the_api_field_message(self, mock_request):
        mock_request.return_value = build_mock_response(
            400, {"note": ["Ensure this field has no more than 500 characters."]}
        )
        _, _, stderr_text = self.run_command(["save", "49", "--note", "x" * 501])
        self.assertEqual(stderr_text, "Error: note: Ensure this field has no more than 500 characters.\n")


@mock.patch("devfeed_cli.output.shutil.get_terminal_size", return_value=FIXED_TERMINAL_SIZE)
@mock.patch("devfeed_cli.api_client.requests.request")
class SavedTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.log_in_locally()

    def test_saved_lists_bookmarks_with_read_flag_and_footer(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200,
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    build_bookmark(5, 49, "Saved from the feed"),
                    build_bookmark(4, 47, "Test note title", note="Test note for article 47", is_read=True),
                ],
            },
        )
        exit_code, stdout_text, _ = self.run_command(["saved"])

        self.assertEqual(exit_code, 0)
        output_lines = stdout_text.splitlines()
        self.assertEqual(output_lines[0].split(), ["ID", "ARTICLE", "READ", "TITLE", "NOTE"])
        self.assertEqual(output_lines[1].split()[:3], ["5", "49", "no"])
        self.assertEqual(output_lines[2].split()[:3], ["4", "47", "yes"])
        self.assertTrue(output_lines[2].endswith("Test note for article 47"))
        self.assertEqual(output_lines[-1], "Page 1 of 1 (2 saved)")
        self.assertTrue(mock_request.call_args.args[1].endswith("/api/bookmarks/?page=1"))

    def test_long_titles_are_cut_so_the_note_stays_visible(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200,
            {"count": 1, "next": None, "previous": None,
             "results": [build_bookmark(5, 49, "T" * 120, note="Visible note")]},
        )
        _, stdout_text, _ = self.run_command(["saved"])
        bookmark_line = stdout_text.splitlines()[1]
        self.assertIn("T" * 39 + "…", bookmark_line)
        self.assertTrue(bookmark_line.endswith("Visible note"))

    def test_no_bookmarks(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(
            200, {"count": 0, "next": None, "previous": None, "results": []}
        )
        _, stdout_text, _ = self.run_command(["saved"])
        self.assertEqual(stdout_text, "No saved articles yet. Save one with: devfeed save <article-id>\n")

    def test_page_past_the_end(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(404, {"detail": "Invalid page."})
        exit_code, _, stderr_text = self.run_command(["saved", "--page", "4"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Page 4 doesn't exist.\n")


@mock.patch("devfeed_cli.api_client.requests.request")
class NoteAndUnsaveTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.log_in_locally()

    def test_note_patches_only_the_note(self, mock_request):
        mock_request.return_value = build_mock_response(
            200, build_bookmark(3, 50, "Some title", note="New text")
        )
        exit_code, stdout_text, _ = self.run_command(["note", "3", "New text"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Updated the note on bookmark 3: Some title\n")
        method, url = mock_request.call_args.args
        self.assertEqual((method, url), ("PATCH", f"{LOCAL_API_URL}/api/bookmarks/3/"))
        self.assertEqual(mock_request.call_args.kwargs["json"], {"note": "New text"})

    def test_empty_note_clears_it(self, mock_request):
        mock_request.return_value = build_mock_response(200, build_bookmark(3, 50, "Some title"))
        self.run_command(["note", "3", ""])
        self.assertEqual(mock_request.call_args.kwargs["json"], {"note": ""})

    def test_note_on_a_missing_or_other_users_bookmark(self, mock_request):
        mock_request.return_value = build_mock_response(404, {"detail": "No Bookmark matches the given query."})
        exit_code, _, stderr_text = self.run_command(["note", "1", "text"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Bookmark 1 not found.\n")

    @mock.patch("builtins.input", return_value="y")
    def test_unsave_asks_then_deletes_by_bookmark_id(self, mock_input, mock_request):
        mock_request.side_effect = [
            build_mock_response(200, build_bookmark(3, 50, "Some title")),
            build_mock_response(204),
        ]
        exit_code, stdout_text, _ = self.run_command(["unsave", "3"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Removed bookmark 3\n")
        mock_input.assert_called_once_with("Remove bookmark 3 (Some title)? [y/N] ")
        requested_calls = [call.args for call in mock_request.call_args_list]
        self.assertEqual(
            requested_calls,
            [
                ("GET", f"{LOCAL_API_URL}/api/bookmarks/3/"),
                ("DELETE", f"{LOCAL_API_URL}/api/bookmarks/3/"),
            ],
        )

    def test_unsave_keeps_the_bookmark_unless_the_answer_is_yes(self, mock_request):
        for answer in ("", "n", "no", "maybe"):
            with self.subTest(answer=answer):
                mock_request.reset_mock()
                mock_request.side_effect = [build_mock_response(200, build_bookmark(3, 50, "Some title"))]
                with mock.patch("builtins.input", return_value=answer):
                    exit_code, stdout_text, _ = self.run_command(["unsave", "3"])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stdout_text, "Kept bookmark 3\n")
                # Only the GET was sent; no DELETE
                self.assertEqual(mock_request.call_count, 1)
                self.assertEqual(mock_request.call_args.args[0], "GET")

    @mock.patch("builtins.input")
    def test_unsave_with_yes_option_skips_the_question(self, mock_input, mock_request):
        mock_request.side_effect = [
            build_mock_response(200, build_bookmark(3, 50, "Some title")),
            build_mock_response(204),
        ]
        exit_code, stdout_text, _ = self.run_command(["unsave", "3", "--yes"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Removed bookmark 3\n")
        mock_input.assert_not_called()

    @mock.patch("builtins.input")
    def test_unsave_missing_bookmark_fails_before_asking(self, mock_input, mock_request):
        mock_request.return_value = build_mock_response(404, {"detail": "No Bookmark matches the given query."})
        exit_code, _, stderr_text = self.run_command(["unsave", "99"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Bookmark 99 not found.\n")
        mock_input.assert_not_called()
        self.assertEqual(mock_request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
