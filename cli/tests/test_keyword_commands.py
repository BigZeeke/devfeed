"""Tests for keywords, keywords follow and keywords unfollow with the API mocked."""

import os
import unittest
from unittest import mock

from command_test_helpers import (
    LOCAL_API_URL,
    CommandTestCase,
    build_mock_response,
)

# A fixed terminal width so table output is the same on every machine
FIXED_TERMINAL_SIZE = os.terminal_size((80, 24))


def build_keywords_page(keywords, has_next_page=False):
    """A paginated keyword list; "next" only matters as set or null."""
    return {
        "count": len(keywords),
        "next": "next-page" if has_next_page else None,
        "previous": None,
        "results": keywords,
    }


def build_keyword(keyword_id, keyword, weight=1):
    """One keyword as the API returns it."""
    return {"id": keyword_id, "keyword": keyword, "weight": weight}


@mock.patch("devfeed_cli.api_client.requests.request")
class KeywordsLoginTests(CommandTestCase):
    def test_every_keyword_command_stops_when_logged_out(self, mock_request):
        for argument_list in (
            ["keywords"],
            ["keywords", "follow", "django"],
            ["keywords", "unfollow", "django"],
        ):
            with self.subTest(command=" ".join(argument_list)):
                exit_code, _, stderr_text = self.run_command(argument_list)
                self.assertEqual(exit_code, 1)
                self.assertEqual(stderr_text, "Error: Not logged in. Run: devfeed login\n")
        mock_request.assert_not_called()


@mock.patch("devfeed_cli.output.shutil.get_terminal_size", return_value=FIXED_TERMINAL_SIZE)
@mock.patch("devfeed_cli.api_client.requests.request")
class KeywordsListTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.log_in_locally()

    def test_list_reads_every_page(self, mock_request, mock_terminal_size):
        mock_request.side_effect = [
            build_mock_response(200, build_keywords_page([build_keyword(1, "docker", 2)], has_next_page=True)),
            build_mock_response(200, build_keywords_page([build_keyword(2, "python", 3)])),
        ]
        exit_code, stdout_text, _ = self.run_command(["keywords"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout_text,
            "WEIGHT  KEYWORD\n"
            "2       docker\n"
            "3       python\n"
            "\n"
            "2 followed\n",
        )
        requested_urls = [call.args[1] for call in mock_request.call_args_list]
        self.assertEqual(
            requested_urls,
            [f"{LOCAL_API_URL}/api/keywords/?page=1", f"{LOCAL_API_URL}/api/keywords/?page=2"],
        )

    def test_no_keywords(self, mock_request, mock_terminal_size):
        mock_request.return_value = build_mock_response(200, build_keywords_page([]))
        _, stdout_text, _ = self.run_command(["keywords"])
        self.assertEqual(
            stdout_text,
            "You're not following any keywords. Follow one with: devfeed keywords follow <word>\n",
        )


@mock.patch("devfeed_cli.api_client.requests.request")
class KeywordsFollowTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.log_in_locally()

    def test_follow_without_weight_lets_the_api_default_apply(self, mock_request):
        mock_request.return_value = build_mock_response(201, build_keyword(7, "django", 1))
        exit_code, stdout_text, _ = self.run_command(["keywords", "follow", "Django"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Following django (weight 1)\n")
        method, url = mock_request.call_args.args
        self.assertEqual((method, url), ("POST", f"{LOCAL_API_URL}/api/keywords/"))
        # No "weight" key at all, so the API's default is used
        self.assertEqual(mock_request.call_args.kwargs["json"], {"keyword": "Django"})

    def test_follow_with_weight_sends_it(self, mock_request):
        mock_request.return_value = build_mock_response(201, build_keyword(7, "django", 4))
        self.run_command(["keywords", "follow", "django", "--weight", "4"])
        self.assertEqual(mock_request.call_args.kwargs["json"], {"keyword": "django", "weight": 4})

    def test_negative_weight_is_passed_to_the_api(self, mock_request):
        # The API accepts any integer; the CLI doesn't add its own rule
        mock_request.return_value = build_mock_response(201, build_keyword(7, "django", -1))
        exit_code, _, _ = self.run_command(["keywords", "follow", "django", "--weight", "-1"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_request.call_args.kwargs["json"]["weight"], -1)

    def test_duplicate_follow_gives_the_friendly_message(self, mock_request):
        mock_request.return_value = build_mock_response(
            400, {"non_field_errors": ["The fields user, keyword must make a unique set."]}
        )
        exit_code, _, stderr_text = self.run_command(["keywords", "follow", "Docker"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: You're already following that keyword.\n")

    def test_too_long_keyword_shows_the_api_field_message(self, mock_request):
        mock_request.return_value = build_mock_response(
            400, {"keyword": ["Ensure this field has no more than 100 characters."]}
        )
        _, _, stderr_text = self.run_command(["keywords", "follow", "k" * 101])
        self.assertEqual(stderr_text, "Error: keyword: Ensure this field has no more than 100 characters.\n")


@mock.patch("devfeed_cli.api_client.requests.request")
class KeywordsUnfollowTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.log_in_locally()

    def keyword_list_response(self):
        return build_mock_response(
            200, build_keywords_page([build_keyword(1, "docker", 2), build_keyword(2, "python", 3)])
        )

    @mock.patch("builtins.input", return_value="y")
    def test_unfollow_finds_the_id_asks_then_deletes(self, mock_input, mock_request):
        mock_request.side_effect = [self.keyword_list_response(), build_mock_response(204)]
        exit_code, stdout_text, _ = self.run_command(["keywords", "unfollow", "Python"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_text, "Stopped following python\n")
        mock_input.assert_called_once_with("Stop following python (weight 3)? [y/N] ")
        self.assertEqual(
            mock_request.call_args.args, ("DELETE", f"{LOCAL_API_URL}/api/keywords/2/")
        )

    def test_unfollow_keeps_the_keyword_unless_the_answer_is_yes(self, mock_request):
        for answer in ("", "n", "no"):
            with self.subTest(answer=answer):
                mock_request.reset_mock()
                mock_request.side_effect = [self.keyword_list_response()]
                with mock.patch("builtins.input", return_value=answer):
                    exit_code, stdout_text, _ = self.run_command(["keywords", "unfollow", "python"])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stdout_text, "Still following python\n")
                # Only the list was requested; no DELETE
                self.assertEqual(mock_request.call_count, 1)

    @mock.patch("builtins.input")
    def test_unfollow_with_yes_option_skips_the_question(self, mock_input, mock_request):
        mock_request.side_effect = [self.keyword_list_response(), build_mock_response(204)]
        exit_code, _, _ = self.run_command(["keywords", "unfollow", "docker", "--yes"])
        self.assertEqual(exit_code, 0)
        mock_input.assert_not_called()
        self.assertEqual(mock_request.call_args.args[0], "DELETE")

    @mock.patch("builtins.input")
    def test_unfollow_a_keyword_not_followed(self, mock_input, mock_request):
        mock_request.side_effect = [self.keyword_list_response()]
        exit_code, _, stderr_text = self.run_command(["keywords", "unfollow", "rust"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_text, "Error: You're not following rust.\n")
        mock_input.assert_not_called()


if __name__ == "__main__":
    unittest.main()
