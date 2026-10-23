"""Persistent top-10 highscore table stored as a JSON file.

The file is a plain JSON array of ``{"name": str, "score": int}`` objects.
A missing file means an empty table; a corrupted file or invalid entries
are reported and skipped, never fatal.  Saving writes a temporary file
first and then renames it, so a crash cannot leave a half-written table.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOG = logging.getLogger("pacman.highscores")

MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10
_NAME_RE = re.compile(r"^[A-Za-z0-9 ]+$")


@dataclass(frozen=True)
class HighscoreEntry:
    """One line of the highscore table."""

    name: str
    score: int


def is_valid_name_char(char: str) -> bool:
    """Return True if ``char`` may appear in a player name."""
    return len(char) == 1 and bool(_NAME_RE.match(char))


def clean_name(name: str) -> str | None:
    """Return ``name`` trimmed if it is a valid player name, else None.

    A valid name has 1 to 10 characters, only letters, digits and spaces.
    """
    name = " ".join(name.split())
    if not name or len(name) > MAX_NAME_LENGTH or not _NAME_RE.match(name):
        return None
    return name


class HighscoreTable:
    """The top ``MAX_ENTRIES`` scores, best first."""

    def __init__(self, path: Path) -> None:
        """Create an empty table backed by the file at ``path``."""
        self.path = path
        self.entries: list[HighscoreEntry] = []
        self.last_error: str | None = None

    def load(self) -> None:
        """Load the table from disk, keeping only valid entries."""
        self.entries = []
        self.last_error = None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._error(f"cannot read highscores '{self.path}': {exc}; "
                        f"starting with an empty table")
            return
        if not isinstance(data, list):
            self._error(f"highscores '{self.path}' must be a JSON array; "
                        f"starting with an empty table")
            return
        for item in data:
            entry = _entry_from_json(item)
            if entry is None:
                LOG.warning("ignoring invalid highscore entry %r", item)
            else:
                self.entries.append(entry)
        self._sort()

    def save(self) -> bool:
        """Write the table to disk atomically.

        Returns:
            True on success, False if the file could not be written.
        """
        data = [{"name": e.name, "score": e.score} for e in self.entries]
        tmp_name: str | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                prefix=".highscores-", suffix=".tmp", dir=self.path.parent)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
                handle.write("\n")
            os.replace(tmp_name, self.path)
            tmp_name = None
        except OSError as exc:
            self._error(f"cannot save highscores to '{self.path}': {exc}")
            return False
        finally:
            if tmp_name is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)
        self.last_error = None
        return True

    def qualifies(self, score: int) -> bool:
        """Return True if ``score`` would enter the table."""
        if score < 0:
            return False
        return (len(self.entries) < MAX_ENTRIES
                or score > self.entries[-1].score)

    def add(self, name: str, score: int) -> int | None:
        """Insert a score, keeping the table sorted and trimmed.

        Args:
            name: Player name; must pass ``clean_name``.
            score: Non-negative score.

        Returns:
            The 0-based rank of the new entry, or None if it did not
            qualify or was invalid.
        """
        cleaned = clean_name(name)
        if cleaned is None or not self.qualifies(score):
            return None
        entry = HighscoreEntry(cleaned, score)
        self.entries.append(entry)
        self._sort()
        rank = self.entries.index(entry)
        del self.entries[MAX_ENTRIES:]
        return rank if rank < MAX_ENTRIES else None

    def _sort(self) -> None:
        """Sort best first (stable, so ties keep their order) and trim."""
        self.entries.sort(key=lambda e: -e.score)
        del self.entries[MAX_ENTRIES:]

    def _error(self, message: str) -> None:
        """Log and remember an error for the UI."""
        LOG.warning(message)
        self.last_error = message


def _entry_from_json(item: Any) -> HighscoreEntry | None:
    """Build an entry from a JSON object, or None if it is invalid."""
    if not isinstance(item, dict):
        return None
    name, score = item.get("name"), item.get("score")
    if not isinstance(name, str) or isinstance(score, bool):
        return None
    if not isinstance(score, int) or score < 0:
        return None
    cleaned = clean_name(name)
    return HighscoreEntry(cleaned, score) if cleaned else None
