"""Load the game configuration: JSON with comments, validated and clamped.

Only an unreadable file or broken JSON is fatal.  Every missing, invalid or
out-of-range value falls back to (or is clamped to) a safe default, and a
warning explaining what happened is logged and kept in
``GameConfig.warnings`` so the main menu can show it too.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger("pacman.config")

MIN_LEVELS = 10
MIN_MAZE_WIDTH, MAX_MAZE_WIDTH = 5, 45
MIN_MAZE_HEIGHT, MAX_MAZE_HEIGHT = 5, 35

# (width, height) in maze cells of the default campaign.
DEFAULT_LEVEL_SIZES: tuple[tuple[int, int], ...] = (
    (15, 11), (17, 11), (17, 13), (19, 13), (19, 15),
    (21, 15), (21, 17), (23, 17), (25, 19), (27, 19),
)

KNOWN_KEYS = frozenset({
    "highscore_filename", "levels", "lives", "pacgum", "points_per_pacgum",
    "points_per_super_pacgum", "points_per_ghost", "seed", "level_max_time",
    "player_speed", "ghost_speed", "ghost_speed_step", "frightened_time",
    "ghost_respawn_time", "cheat_mode", "window_width", "window_height",
    "fps",
})
KNOWN_LEVEL_KEYS = frozenset(
    {"width", "height", "seed", "level_max_time", "pacgum"})


class ConfigError(Exception):
    """Raised when the configuration file cannot be used at all."""


@dataclass(frozen=True)
class LevelConfig:
    """Settings of a single level.

    Attributes:
        width: Maze width in cells.
        height: Maze height in cells.
        seed: Generator seed, or ``None`` for a random maze.
        max_time: Time limit in seconds.
        pacgum: Maximum number of pacgums, 0 meaning every free tile.
    """

    width: int
    height: int
    seed: int | None
    max_time: float
    pacgum: int


@dataclass(frozen=True)
class GameConfig:
    """Every tunable game parameter, already validated."""

    highscore_file: Path
    levels: tuple[LevelConfig, ...]
    lives: int = 3
    points_per_pacgum: int = 10
    points_per_super_pacgum: int = 50
    points_per_ghost: int = 200
    seed: int = 42
    level_max_time: float = 120.0
    pacgum: int = 0
    player_speed: float = 8.0
    ghost_speed: float = 5.5
    ghost_speed_step: float = 0.15
    frightened_time: float = 7.0
    ghost_respawn_time: float = 5.0
    cheat_mode: bool = False
    window_width: int = 1280
    window_height: int = 800
    fps: int = 60
    warnings: tuple[str, ...] = field(default=(), compare=False)


def strip_comments(text: str) -> str:
    """Remove ``#``, ``//`` and ``/* */`` comments outside JSON strings.

    Newlines are kept so JSON error line numbers still match the file.

    Args:
        text: Raw file content.

    Returns:
        The text with every comment removed.

    Raises:
        ConfigError: If a ``/*`` comment is never closed.
    """
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if char == '"':
                in_string = False
            i += 1
        elif char == '"':
            in_string = True
            out.append(char)
            i += 1
        elif char == "#" or text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end == -1 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end == -1:
                raise ConfigError("unterminated /* comment")
            out.append("\n" * text.count("\n", i, end))
            i = end + 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


class _Reader:
    """Read typed values out of a JSON object, collecting warnings."""

    def __init__(self, warnings: list[str]) -> None:
        """Create a reader that appends its messages to ``warnings``."""
        self.warnings = warnings

    def warn(self, message: str) -> None:
        """Log ``message`` and remember it for the UI."""
        LOG.warning(message)
        self.warnings.append(message)

    def integer(self, data: dict[str, Any], key: str, default: int,
                low: int, high: int, where: str = "") -> int:
        """Return ``data[key]`` as an int clamped to ``[low, high]``."""
        name = f"{where}{key}"
        if key not in data:
            self.warn(f"'{name}' is missing, using default {default}")
            return default
        value = data[key]
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, bool) or not isinstance(value, int):
            self.warn(f"'{name}' must be an integer, got {value!r}; "
                      f"using default {default}")
            return default
        return int(self._clamp(name, value, low, high))

    def number(self, data: dict[str, Any], key: str, default: float,
               low: float, high: float, where: str = "") -> float:
        """Return ``data[key]`` as a float clamped to ``[low, high]``."""
        name = f"{where}{key}"
        if key not in data:
            self.warn(f"'{name}' is missing, using default {default}")
            return default
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.warn(f"'{name}' must be a number, got {value!r}; "
                      f"using default {default}")
            return default
        if value != value:  # NaN
            self.warn(f"'{name}' is not a number; using default {default}")
            return default
        return float(self._clamp(name, value, low, high))

    def boolean(self, data: dict[str, Any], key: str, default: bool) -> bool:
        """Return ``data[key]`` as a bool."""
        if key not in data:
            self.warn(f"'{key}' is missing, using default "
                      f"{str(default).lower()}")
            return default
        value = data[key]
        if not isinstance(value, bool):
            self.warn(f"'{key}' must be true or false, got {value!r}; "
                      f"using default {str(default).lower()}")
            return default
        return value

    def _clamp(self, name: str, value: Any, low: Any, high: Any) -> Any:
        """Clamp ``value`` into ``[low, high]``, warning when it moves."""
        if value < low:
            self.warn(f"'{name}' = {value} is below {low}; clamped to {low}")
            return low
        if value > high:
            self.warn(f"'{name}' = {value} is above {high}; "
                      f"clamped to {high}")
            return high
        return value


def read_config_file(path: Path) -> dict[str, Any]:
    """Read ``path`` and parse it as JSON with comments.

    Args:
        path: The configuration file.

    Returns:
        The top-level JSON object.

    Raises:
        ConfigError: If the file cannot be read or is not a JSON object.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        raise ConfigError(f"config file '{path}' does not exist") from None
    except IsADirectoryError:
        raise ConfigError(f"'{path}' is a directory, not a file") from None
    except UnicodeDecodeError:
        raise ConfigError(f"'{path}' is not a UTF-8 text file") from None
    except OSError as exc:
        raise ConfigError(
            f"cannot read '{path}': {exc.strerror or exc}") from None
    try:
        data = json.loads(strip_comments(text))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"'{path}' is not valid JSON: {exc.msg} "
                          f"(line {exc.lineno}, column {exc.colno})") from None
    except RecursionError:
        raise ConfigError(f"'{path}' is nested too deeply") from None
    if not isinstance(data, dict):
        raise ConfigError(f"'{path}' must contain a JSON object "
                          f"({{ ... }}) at the top level")
    return data


def load_config(path: Path) -> GameConfig:
    """Load and validate the configuration file at ``path``.

    Args:
        path: The configuration file.

    Returns:
        A fully validated configuration.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    return parse_config(read_config_file(path), path.resolve().parent)


def parse_config(data: dict[str, Any], base_dir: Path) -> GameConfig:
    """Validate an already parsed configuration object.

    Args:
        data: The top-level JSON object.
        base_dir: Directory that relative paths are resolved against.

    Returns:
        A fully validated configuration.
    """
    warnings: list[str] = []
    read = _Reader(warnings)
    for key in sorted(set(data) - KNOWN_KEYS):
        read.warn(f"unknown key '{key}' ignored")

    seed = read.integer(data, "seed", 42, 1, 2**31 - 1)
    max_time = read.number(data, "level_max_time", 120.0, 10.0, 3600.0)
    pacgum = read.integer(data, "pacgum", 0, 0, 100_000)
    return GameConfig(
        highscore_file=_highscore_path(data, base_dir, read),
        levels=_levels(data.get("levels"), seed, max_time, pacgum, read),
        lives=read.integer(data, "lives", 3, 1, 99),
        points_per_pacgum=read.integer(
            data, "points_per_pacgum", 10, 0, 1_000_000),
        points_per_super_pacgum=read.integer(
            data, "points_per_super_pacgum", 50, 0, 1_000_000),
        points_per_ghost=read.integer(
            data, "points_per_ghost", 200, 0, 1_000_000),
        seed=seed,
        level_max_time=max_time,
        pacgum=pacgum,
        player_speed=read.number(data, "player_speed", 8.0, 1.0, 20.0),
        ghost_speed=read.number(data, "ghost_speed", 5.5, 1.0, 20.0),
        ghost_speed_step=read.number(
            data, "ghost_speed_step", 0.15, 0.0, 2.0),
        frightened_time=read.number(
            data, "frightened_time", 7.0, 1.0, 60.0),
        ghost_respawn_time=read.number(
            data, "ghost_respawn_time", 5.0, 0.5, 60.0),
        cheat_mode=read.boolean(data, "cheat_mode", False),
        window_width=read.integer(data, "window_width", 1280, 640, 3840),
        window_height=read.integer(data, "window_height", 800, 480, 2160),
        fps=read.integer(data, "fps", 60, 30, 240),
        warnings=tuple(warnings),
    )


def _highscore_path(data: dict[str, Any], base_dir: Path,
                    read: _Reader) -> Path:
    """Return the highscore file, relative paths resolved to ``base_dir``."""
    default = "highscores.json"
    value = data.get("highscore_filename")
    if value is None:
        read.warn(f"'highscore_filename' is missing, using '{default}'")
        value = default
    elif not isinstance(value, str) or not value.strip():
        read.warn(f"'highscore_filename' must be a non-empty string, "
                  f"got {value!r}; using '{default}'")
        value = default
    path = Path(value.strip()).expanduser()
    return path if path.is_absolute() else base_dir / path


def _levels(raw: Any, seed: int, max_time: float, pacgum: int,
            read: _Reader) -> tuple[LevelConfig, ...]:
    """Validate the ``levels`` array and pad it to ``MIN_LEVELS`` levels."""
    items: list[Any]
    if raw is None:
        read.warn("'levels' is missing, using the default campaign")
        items = []
    elif not isinstance(raw, list):
        read.warn(f"'levels' must be an array, got {type(raw).__name__}; "
                  f"using the default campaign")
        items = []
    else:
        items = raw

    levels: list[LevelConfig] = []
    for index, item in enumerate(items):
        where = f"levels[{index}]."
        if not isinstance(item, dict):
            read.warn(f"levels[{index}] must be an object; level skipped")
            continue
        for key in sorted(set(item) - KNOWN_LEVEL_KEYS):
            read.warn(f"unknown key '{where}{key}' ignored")
        number = len(levels)
        default_w, default_h = DEFAULT_LEVEL_SIZES[
            min(number, len(DEFAULT_LEVEL_SIZES) - 1)]
        level_seed: int | None = None
        if "seed" in item:
            level_seed = read.integer(item, "seed", 0, 0, 2**31 - 1, where)
            level_seed = level_seed or None
        levels.append(LevelConfig(
            width=read.integer(item, "width", default_w, MIN_MAZE_WIDTH,
                               MAX_MAZE_WIDTH, where),
            height=read.integer(item, "height", default_h, MIN_MAZE_HEIGHT,
                                MAX_MAZE_HEIGHT, where),
            seed=level_seed,
            max_time=(read.number(item, "level_max_time", max_time, 10.0,
                                  3600.0, where)
                      if "level_max_time" in item else max_time),
            pacgum=(read.integer(item, "pacgum", pacgum, 0, 100_000, where)
                    if "pacgum" in item else pacgum),
        ))

    if items and len(levels) < MIN_LEVELS:
        read.warn(f"only {len(levels)} valid level(s) given, at least "
                  f"{MIN_LEVELS} are required; adding default levels")
    while len(levels) < MIN_LEVELS:
        width, height = DEFAULT_LEVEL_SIZES[len(levels)]
        levels.append(LevelConfig(width, height, None, max_time, pacgum))

    # The first level always uses a fixed seed so it is reproducible.
    first = levels[0]
    if first.seed is None:
        levels[0] = LevelConfig(first.width, first.height, seed,
                                first.max_time, first.pacgum)
    return tuple(levels)
