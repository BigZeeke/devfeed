"""Tests for vote and unvote with the API mocked."""

import unittest
from unittest import mock

from command_test_helpers import (
    LOCAL_API_URL,
    CommandTestCase,
    build_mock_response,
)


def build_vote_response(article_id, direction, up_votes, down_votes):
    """The API's vote response: the caller's direction plus the totals."""
    return {
        "article": article_id,
        "direction": direction,
        "up_votes": up_votes,
        "down_votes": down_votes,
    }


@mock.patch("devfeed_cli.api_client.requests.request")
class VoteTests(CommandTestCase):
    def test_vote_and_unvote_stop_when_logged_out(self, mock_request):
        for argument_list in (["vote", "49", "up"], ["unvote", "49"]):
            with self.subTest(command=argument_list[0]):
                exit_code, _, stderr_text = self.run_command(argument_list)
                self.assertEqual(exit_code, 1)
                self.assertEqual(stderr_text, "Error: Not logged in. Run: devfeed login\n")
        mock_request.assert_not_called()

    def test_vote_up_posts_the_direction_and_prints_counts(self, mock_request):
        self.log_in_locally()
        mock_request.return_value = build_mock_response(200, build_vote_response(49, "up", 1, 0))
        exit_code, stdout_text, _ = self.run_command(["vote", "49", "up"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Voted up on article 49 (up 1, down 0)\n")
        method, url = mock_request.call_args.args
        self.assertEqual((method, url), ("POST", f"{LOCAL_API_URL}/api/articles/49/vote/"))
        self.assertEqual(mock_request.call_args.kwargs["json"], {"direction": "up"})

    def test_vote_down(self, mock_request):
        self.log_in_locally()
        mock_request.return_value = build_mock_response(200, build_vote_response(49, "down", 0, 1))
        _, stdout_text, _ = self.run_command(["vote", "49", "down"])
        self.assertEqual(stdout_text, "Voted down on article 49 (up 0, down 1)\n")
        self.assertEqual(mock_request.call_args.kwargs["json"], {"direction": "down"})

    @mock.patch("builtins.input", return_value="y")
    def test_unvote_asks_then_sends_null_not_delete(self, mock_input, mock_request):
        self.log_in_locally()
        mock_request.side_effect = [
            build_mock_response(200, {"id": 49, "title": "chenglou/handwired"}),
            build_mock_response(200, build_vote_response(49, None, 0, 0)),
        ]
        exit_code, stdout_text, _ = self.run_command(["unvote", "49"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Removed your vote on article 49 (up 0, down 0)\n")
        mock_input.assert_called_once_with("Remove your vote on article 49 (chenglou/handwired)? [y/N] ")
        requested_calls = [call.args for call in mock_request.call_args_list]
        self.assertEqual(
            requested_calls,
            [
                ("GET", f"{LOCAL_API_URL}/api/articles/49/"),
                ("POST", f"{LOCAL_API_URL}/api/articles/49/vote/"),
            ],
        )
        self.assertEqual(mock_request.call_args.kwargs["json"], {"direction": None})

    def test_unvote_keeps_the_vote_unless_the_answer_is_yes(self, mock_request):
        self.log_in_locally()
        for answer in ("", "n", "no"):
            with self.subTest(answer=answer):
                mock_request.reset_mock()
                mock_request.side_effect = [build_mock_response(200, {"id": 49, "title": "Title"})]
                with mock.patch("builtins.input", return_value=answer):
                    exit_code, stdout_text, _ = self.run_command(["unvote", "49"])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stdout_text, "Kept your vote on article 49\n")
                # Only the article GET was sent; no vote request
                self.assertEqual(mock_request.call_count, 1)
                self.assertEqual(mock_request.call_args.args[0], "GET")

    @mock.patch("builtins.input")
    def test_unvote_with_yes_option_skips_the_question(self, mock_input, mock_request):
        self.log_in_locally()
        mock_request.return_value = build_mock_response(200, build_vote_response(49, None, 0, 0))
        exit_code, _, _ = self.run_command(["unvote", "49", "--yes"])
        self.assertEqual(exit_code, 0)
        mock_input.assert_not_called()
        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(mock_request.call_args.kwargs["json"], {"direction": None})

    @mock.patch("builtins.input")
    def test_unvote_on_a_missing_article_fails_before_asking(self, mock_input, mock_request):
        self.log_in_locally()
        mock_request.return_value = build_mock_response(404, {"detail": "No Article matches the given query."})
        exit_code, _, stderr_text = self.run_command(["unvote", "9999"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Article 9999 not found.\n")
        mock_input.assert_not_called()

    def test_invalid_direction_is_rejected_before_any_request(self, mock_request):
        self.log_in_locally()
        with self.assertRaises(SystemExit) as raised:
            self.run_command(["vote", "49", "sideways"])
        self.assertEqual(raised.exception.code, 2)
        mock_request.assert_not_called()

    def test_vote_on_a_missing_article(self, mock_request):
        self.log_in_locally()
        mock_request.return_value = build_mock_response(404, {"detail": "No Article matches the given query."})
        exit_code, _, stderr_text = self.run_command(["vote", "9999", "up"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: Article 9999 not found.\n")


if __name__ == "__main__":
    unittest.main()
