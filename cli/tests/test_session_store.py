"""Tests for the session store: per-server sessions, file permissions, bad files."""

import json
import stat
import tempfile
import unittest
from pathlib import Path

from devfeed_cli.errors import DevfeedError
from devfeed_cli.session_store import SessionStore

LOCAL_API_URL = "http://127.0.0.1:8000"
LIVE_API_URL = "http://44.248.236.123"


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        # Each test gets its own folder, never the real ~/.config
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.sessions_file_path = Path(self.temporary_directory.name) / "devfeed" / "sessions.json"
        self.session_store = SessionStore(self.sessions_file_path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_read_returns_none_when_no_file_exists(self):
        self.assertIsNone(self.session_store.read(LOCAL_API_URL))

    def test_save_then_read_returns_the_session(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        self.assertEqual(
            self.session_store.read(LOCAL_API_URL),
            {"username": "curl_test_user", "token": "a" * 40},
        )

    def test_sessions_for_two_servers_are_kept_separately(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        self.session_store.save(LIVE_API_URL, "live_test_user", "b" * 40)
        self.assertEqual(self.session_store.read(LOCAL_API_URL)["username"], "curl_test_user")
        self.assertEqual(self.session_store.read(LIVE_API_URL)["username"], "live_test_user")

    def test_delete_removes_only_that_server(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        self.session_store.save(LIVE_API_URL, "live_test_user", "b" * 40)
        self.session_store.delete(LOCAL_API_URL)
        self.assertIsNone(self.session_store.read(LOCAL_API_URL))
        self.assertIsNotNone(self.session_store.read(LIVE_API_URL))

    def test_file_permissions_are_600_and_folder_700(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        file_mode = stat.S_IMODE(self.sessions_file_path.stat().st_mode)
        folder_mode = stat.S_IMODE(self.sessions_file_path.parent.stat().st_mode)
        self.assertEqual(file_mode, 0o600)
        self.assertEqual(folder_mode, 0o700)

    def test_permissions_are_tightened_when_rewriting_a_wider_file(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        self.sessions_file_path.chmod(0o644)
        self.session_store.save(LIVE_API_URL, "live_test_user", "b" * 40)
        self.assertEqual(stat.S_IMODE(self.sessions_file_path.stat().st_mode), 0o600)

    def test_no_temporary_file_is_left_behind(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        self.assertEqual(
            sorted(path.name for path in self.sessions_file_path.parent.iterdir()),
            ["sessions.json"],
        )

    def test_invalid_json_gives_a_clear_error(self):
        self.sessions_file_path.parent.mkdir(parents=True)
        self.sessions_file_path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(DevfeedError) as raised:
            self.session_store.read(LOCAL_API_URL)
        self.assertIn("not valid JSON", str(raised.exception))

    def test_file_contents_are_plain_json(self):
        self.session_store.save(LOCAL_API_URL, "curl_test_user", "a" * 40)
        stored_sessions = json.loads(self.sessions_file_path.read_text(encoding="utf-8"))
        self.assertEqual(list(stored_sessions), [LOCAL_API_URL])


if __name__ == "__main__":
    unittest.main()
