"""Tests of the configuration loader."""

import json
from pathlib import Path

import pytest

from pacman.config import (MIN_LEVELS, ConfigError, load_config,
                           strip_comments)


def write(tmp_path: Path, text: str) -> Path:
    """Write ``text`` to a config file and return its path."""
    path = tmp_path / "config.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_strip_comments_keeps_strings() -> None:
    """Comment markers inside strings are not comments."""
    text = '# top\n{"a": "x # y // z", // trailing\n /* block\n */ "b": 1}'
    assert strip_comments(text).count("\n") == text.count("\n")
    assert json.loads(strip_comments(text)) == {"a": "x # y // z", "b": 1}


def test_sample_config_loads_without_warnings() -> None:
    """The shipped config.json is complete and valid."""
    root = Path(__file__).resolve().parent.parent
    cfg = load_config(root / "config.json")
    assert cfg.warnings == ()
    assert len(cfg.levels) >= MIN_LEVELS
    assert cfg.levels[0].seed == 42
    assert all(level.seed is None for level in cfg.levels[1:])


def test_missing_file(tmp_path: Path) -> None:
    """A missing file is a clean ConfigError."""
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(tmp_path / "nope.json")


def test_directory(tmp_path: Path) -> None:
    """A directory is a clean ConfigError."""
    with pytest.raises(ConfigError):
        load_config(tmp_path)


@pytest.mark.parametrize("text", ["{", "[1, 2]", "not json", "/* open"])
def test_invalid_json(tmp_path: Path, text: str) -> None:
    """Broken JSON or a non-object is a clean ConfigError."""
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, text))


def test_empty_object_uses_defaults(tmp_path: Path) -> None:
    """Every key falls back to its default with a warning."""
    cfg = load_config(write(tmp_path, "{}"))
    assert cfg.lives == 3
    assert cfg.points_per_pacgum == 10
    assert len(cfg.levels) == MIN_LEVELS
    assert cfg.levels[0].seed == 42
    assert cfg.highscore_file == tmp_path / "highscores.json"
    assert cfg.warnings


def test_invalid_values_are_clamped_or_defaulted(tmp_path: Path) -> None:
    """Out of range values are clamped, wrong types use the default."""
    cfg = load_config(write(tmp_path, """
        {"lives": -5, "points_per_ghost": "lots", "fps": 10000,
         "cheat_mode": "yes", "seed": true, "player_speed": 3.5,
         "unknown": 1, "highscore_filename": ""}
    """))
    assert cfg.lives == 1
    assert cfg.points_per_ghost == 200
    assert cfg.fps == 240
    assert cfg.cheat_mode is False
    assert cfg.seed == 42
    assert cfg.player_speed == 3.5
    assert cfg.highscore_file.name == "highscores.json"
    text = "\n".join(cfg.warnings)
    assert "unknown key 'unknown'" in text
    assert "'lives'" in text


def test_levels_are_validated_and_padded(tmp_path: Path) -> None:
    """Bad level entries are skipped and the campaign padded to 10."""
    cfg = load_config(write(tmp_path, """
        {"seed": 7, "levels": [
            {"width": 1000, "height": 2},
            "oops",
            {"width": 20, "height": 12, "seed": 99, "pacgum": 5}
        ]}
    """))
    assert len(cfg.levels) == MIN_LEVELS
    first, second = cfg.levels[0], cfg.levels[1]
    assert (first.width, first.height, first.seed) == (45, 5, 7)
    assert (second.width, second.seed, second.pacgum) == (20, 99, 5)
    assert any("levels[1]" in w for w in cfg.warnings)
