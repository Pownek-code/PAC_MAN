# Subject analysis and technical choices

## Requirement checklist

| Requirement (subject chapter) | Where it is met |
| --- | --- |
| Python ≥ 3.10, flake8, mypy, type hints, docstrings (III.1) | whole code base, `make lint`, `make lint-strict` |
| Exceptions handled, context managers (III.1) | `cli.py`, `config.py`, `highscores.py`, `maze.py` |
| Makefile: install, run, debug, clean, lint, lint-strict (III.2) | `Makefile` |
| `.gitignore`, tests (III.3) | `.gitignore`, `tests/` |
| `python3 pac-man.py config.json`, exactly one argument (V.1) | `pac-man.py`, `cli.py` |
| JSON with `#` comments, documented keys, defaults (V.2) | `config.py`, README "Configuration" |
| Faulty values clamped, logged, unknown keys ignored (V.3) | `config.py` `_Reader` |
| Use the assigned package as-is, `PERFECT=False`, handle failures (V.4) | `maze.py` |
| Highscores: robust, names ≤ 10 alnum + spaces, top 10 (V.5) | `highscores.py`, `EndScene` |
| Level layout: corners, centre, pacgums, 1st level fixed seed (VI.1) | `level.py`, `config.py` |
| Player: arrows/WASD, lives, respawn, win/lose (VI.2) | `entities.py`, `game.py` |
| Ghosts: chase, flee, respawn in corner (VI.3) | `ai.py`, `game.py` |
| Cheat mode (VI.5) | `game.py`, `scenes.py`, HUD footer |
| Scoring never decreases (VI.6) | `game.py` |
| ≥ 10 levels, time limit, pause, keep score/lives (VI.7) | `config.py`, `game.py`, `GameScene` |
| Menu, HUD, pause menu, game over & victory screens (VI.8) | `scenes.py`, `render.py` |
| Packaged build + script/spec at root (VII) | `pac-man.spec`, `packaging/` |
| Project management folder (VIII) | this folder |
| README sections (IX) | `README.md` |

## Decisions

| Topic | Choice | Why |
| --- | --- | --- |
| Graphics library | pygame-ce | "MLX or similar". Mature, typed, installs from pip on every OS, works with PyInstaller. |
| Art | Procedural drawing only | No asset licensing, nothing to lose when packaging, easy to re-theme. |
| Theme | *Dune*: dunes as walls, spice as pacgums, Harkonnen ghosts | The player asked for a Dune theme; the sand/spice palette also keeps the maze readable. |
| Maze representation | Generator cells → 2× tile grid | Pac-Man needs thick walls and 1-tile corridors; the conversion is simple and keeps the generator untouched. |
| "42" of the generator | Kept as solid rock (`BLOCK` tiles) | It is part of the package output; hiding it would mean altering its maze. |
| Movement | Tile-to-tile interpolation | Exact wall collisions, smooth display, frame-rate independent. |
| Ghost pathing | BFS walking distance to the target | Straight-line distance gets stuck behind walls in generated mazes. |
| Logic / UI split | Logic modules never import pygame | Unit tests run headless; renderer can change freely. |
| Time-out rule | Lose a life, timer restarts, pacgums stay eaten | Fair, easy to explain, keeps progress. |
| Highscore storage | JSON file next to the config, atomic replace | Human-readable for reviewers, safe against crashes. |
| Config errors | Fatal only for unreadable file / broken JSON | Matches "clamp to safe defaults, log, continue"; a broken file has no values to clamp. |
| Packaging | PyInstaller one-folder + zip + `.itch.toml` | The itch app passes `config.json` as the required argument; players can edit the config. |
