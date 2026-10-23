# Acceptance test plan

Automated: `make lint`, `make lint-strict` and `make test` (36 tests).
Manual: run `make run` and go through the scenarios below.

## Results of the first full run (2026-10-23)

| # | Feature | Scenario | Expected | Result |
| --- | --- | --- | --- | --- |
| A1 | CLI | `python3 pac-man.py` / two arguments | usage message, exit 2, no traceback | Pass |
| A2 | CLI | missing file / directory / broken JSON | clear `pac-man: error:` line, exit 1 | Pass |
| A3 | Config | `{}` | game starts with defaults, warnings printed and counted on menu | Pass |
| A4 | Config | wrong types, out of range, unknown keys, `levels` not an array | clamped / defaulted / ignored with warnings | Pass |
| A5 | Config | fewer than 10 levels | padded to 10 with a warning | Pass (unit test) |
| A6 | Maze | level 1 with seed 42 twice | identical maze | Pass (unit test) |
| A7 | Maze | 45×35 maze | generated (recursion limit handled) | Pass (unit test) |
| A8 | Maze | generator raising | retried, then error screen, back to menu | Pass (unit test + code path) |
| A9 | Layout | start of a level | player centre, ghosts and super-pacgums in the 4 corners | Pass |
| A10 | Rules | eat pacgum / super / edible ghost | +10 / +50 & ghosts blue / +200 & ghost respawns | Pass (unit tests) |
| A11 | Rules | ghost touches player | life lost, everyone back to spawn | Pass (unit test) |
| A12 | Rules | timer reaches 0 | life lost, timer restarts | Pass (unit test) |
| A13 | Rules | 3000 simulated frames on a real maze | nobody ever enters a wall | Pass (unit test) |
| A14 | Progression | skip all 10 levels | victory, score and lives kept | Pass |
| A15 | Cheats | F1 then I, F, V, L, N, T | each cheat works, footer lists them | Pass (unit tests + screenshots) |
| A16 | Pause | P / Esc in game | pause menu, Resume and Main Menu work | Pass (screenshot) |
| A17 | End | victory / game over | final score, name entry (≤ 10 alnum + spaces) | Pass |
| A18 | Highscores | save, reload, corrupt file, unwritable dir | top 10 kept, corruption ignored, failure reported | Pass (unit tests) |
| A19 | Packaging | `make package`, run `dist/pac-man/play.sh` | game window opens | Pass (Linux) |
| A20 | Packaging | itch.io install through the itch app | starts with config.json | To do |

## Bugs found and fixed

| Bug | Found by | Fix |
| --- | --- | --- |
| Generator raises `RecursionError` above ~40×30 cells | probing the package | adapter raises the recursion limit during generation; sizes clamped to 45×35 |
| ALSA errors printed at start on machines without sound | headless run | only the display and font modules of pygame are initialised |
| Level 10 (~1100 pacgums) impossible in 90 s | play-test estimate | default times scale from 120 s to 240 s, player 8 tiles/s |
| The generator's "42" drawn as hollow outlines, unreadable | screenshot review | closed cells and their joints drawn as solid rock |
| "GET READY" banner unreadable over the maze | screenshot review | translucent band behind banners |
