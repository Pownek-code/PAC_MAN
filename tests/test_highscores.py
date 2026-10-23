"""Tests of the highscore table."""

import json
from pathlib import Path

from pacman.highscores import HighscoreTable, clean_name


def test_clean_name() -> None:
    """Names are 1-10 letters, digits or spaces."""
    assert clean_name("  Paul   A ") == "Paul A"
    assert clean_name("Chani2") == "Chani2"
    assert clean_name("") is None
    assert clean_name("Muad'Dib") is None
    assert clean_name("Abcdefghijk") is None


def test_missing_and_corrupt_files(tmp_path: Path) -> None:
    """Missing or invalid files give an empty table, never a crash."""
    table = HighscoreTable(tmp_path / "none.json")
    table.load()
    assert table.entries == [] and table.last_error is None
    bad = tmp_path / "bad.json"
    for content in ("{not json", '{"a": 1}', "\xff"):
        bad.write_text(content, encoding="latin-1")
        table = HighscoreTable(bad)
        table.load()
        assert table.entries == []


def test_invalid_entries_are_skipped(tmp_path: Path) -> None:
    """Only well formed entries are kept, sorted best first."""
    path = tmp_path / "hs.json"
    path.write_text(json.dumps([
        {"name": "Stilgar", "score": 50}, {"name": "x!", "score": 5},
        {"name": "Leto", "score": -1}, {"name": "Jessica", "score": 90},
        {"name": "Gurney", "score": True}, "junk",
    ]))
    table = HighscoreTable(path)
    table.load()
    assert [(e.name, e.score) for e in table.entries] == [
        ("Jessica", 90), ("Stilgar", 50)]


def test_top_ten_and_round_trip(tmp_path: Path) -> None:
    """Only ten scores are kept and they survive a save/load."""
    path = tmp_path / "sub" / "hs.json"
    table = HighscoreTable(path)
    for score in range(15):
        table.add(f"P{score}", score * 10)
    assert len(table.entries) == 10
    assert table.entries[0].score == 140
    assert not table.qualifies(50)
    assert table.add("Late", 0) is None
    assert table.save()
    again = HighscoreTable(path)
    again.load()
    assert again.entries == table.entries


def test_save_failure_is_reported(tmp_path: Path) -> None:
    """An unwritable location returns False instead of raising."""
    blocker = tmp_path / "file"
    blocker.write_text("x")
    table = HighscoreTable(blocker / "hs.json")
    table.add("Paul", 10)
    assert table.save() is False
    assert table.last_error
