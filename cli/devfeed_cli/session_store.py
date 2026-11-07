"""Saves and reads login sessions: one {username, token} per API address.

Sessions live in ~/.config/devfeed/sessions.json with permissions 600, so a
local login and a live-site login can exist at the same time. Nothing in this
module prints a token.
"""

import json
import os
from pathlib import Path

from .errors import DevfeedError

DEFAULT_SESSIONS_FILE_PATH = Path.home() / ".config" / "devfeed" / "sessions.json"


class SessionStore:
    """Reads and writes the sessions file; the path is a parameter for tests."""

    def __init__(self, sessions_file_path=DEFAULT_SESSIONS_FILE_PATH):
        self.sessions_file_path = Path(sessions_file_path)

    def _read_all_sessions(self):
        # A missing file just means nobody has logged in yet
        if not self.sessions_file_path.exists():
            return {}
        try:
            all_sessions = json.loads(self.sessions_file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise DevfeedError(
                f"The session file {self.sessions_file_path} is not valid JSON. "
                "Delete it and run: devfeed login"
            )
        if not isinstance(all_sessions, dict):
            raise DevfeedError(
                f"The session file {self.sessions_file_path} has an unexpected format. "
                "Delete it and run: devfeed login"
            )
        return all_sessions

    def _write_all_sessions(self, all_sessions):
        # Folder readable only by the owner, created on first login
        self.sessions_file_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary_file_path = self.sessions_file_path.with_suffix(".json.tmp")
        # Create the temporary file with mode 600 from the start, so the token
        # is never readable by other users, even for a moment
        file_descriptor = os.open(
            temporary_file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump(all_sessions, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
        # Covers a leftover temporary file that had wider permissions
        os.chmod(temporary_file_path, 0o600)
        # Replace in one step so a crash never leaves a half-written file
        os.replace(temporary_file_path, self.sessions_file_path)

    def read(self, api_url):
        """Return {"username", "token"} for this API address, or None."""
        session = self._read_all_sessions().get(api_url)
        if not isinstance(session, dict) or not session.get("token"):
            return None
        return session

    def save(self, api_url, username, token):
        """Store the session for this API address, keeping the others."""
        all_sessions = self._read_all_sessions()
        all_sessions[api_url] = {"username": username, "token": token}
        self._write_all_sessions(all_sessions)

    def delete(self, api_url):
        """Remove the session for this API address; other servers are kept."""
        all_sessions = self._read_all_sessions()
        if api_url in all_sessions:
            del all_sessions[api_url]
            self._write_all_sessions(all_sessions)
