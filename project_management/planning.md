# Planning and progress

## Milestones

| # | Milestone | Content | Status |
| --- | --- | --- | --- |
| M1 | Analysis | Read subject + maze package, requirement checklist, architecture | Done |
| M2 | Logic core | `config`, `maze`, `level`, `entities`, `ai`, `game`, `highscores` + tests | Done |
| M3 | UI | Window, scenes, HUD, pause menu, name entry | Done |
| M4 | Theme | Dune palette, procedural sprites, backdrop, balancing | Done (first pass) |
| M5 | Packaging | `pac-man.spec`, zip, `.itch.toml`, itch.io upload | Spec done; upload to do |
| M6 | Docs & review | README, project management, peer review, defence prep | In progress |

Dates and actual time spent: fill in as the project progresses.

| # | Planned end | Actual end | Notes |
| --- | --- | --- | --- |
| M1 | | | |
| M2 | | | |
| M3 | | | |
| M4 | | | |
| M5 | | | |
| M6 | | | |

## Kanban

### Done
- Requirement checklist from the subject (see `analysis_and_choices.md`).
- JSON-with-comments config, clamping + warnings, 10-level padding.
- A-Maze-ing adapter (cells → tiles, recursion limit, retries, MazeError).
- Level layout: centre spawn, corner super-pacgums and ghosts, pacgums.
- Player movement with buffered turns; ghosts with 4 personalities.
- Scoring, lives, timer, frightened mode, ghost respawn, level progression.
- Cheat mode (invincible, freeze, speed, +life, skip, refill time).
- Highscores: validation, top 10, atomic save.
- Scenes: main menu, highscores, instructions, game, pause, game over /
  victory with name entry, error screen.
- Dune theme.
- flake8 + mypy (`--strict` too) clean; 36 unit tests.
- PyInstaller spec producing `dist/pac-man-<os>.zip`.

### To do
- Create the itch.io page (restricted/draft) and upload the builds.
- Build on Windows / macOS if those platforms are to be shipped.
- Play-test the balance (speeds, time limits) with peers.
- Fill in the 42 login in the README first line.
- Peer review and defence preparation (practise small live changes).

### Ideas (optional)
- Sound effects (the mixer is deliberately not initialised today).
- Fullscreen option in the config.
