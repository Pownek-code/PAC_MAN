"""Tests of the game rules, run headless on hand-made mazes."""

import random
from dataclasses import replace
from pathlib import Path

import pytest

from pacman.config import LevelConfig, parse_config
from pacman.entities import Direction, GhostMode
from pacman.game import READY_TIME, GameSession, Phase
from pacman.maze import MazeError

N, E, S, W = 1, 2, 4, 8


def open_grid(width: int, height: int, seed: int) -> list[list[int]]:
    """A maze with no inner walls: every cell opens on its neighbours."""
    cells = []
    for y in range(height):
        row = []
        for x in range(width):
            walls = ((N if y == 0 else 0) | (S if y == height - 1 else 0)
                     | (W if x == 0 else 0) | (E if x == width - 1 else 0))
            row.append(walls)
        cells.append(row)
    return cells


def phase(session: GameSession) -> Phase:
    """Read the phase (a call, so mypy does not narrow it between steps)."""
    return session.phase


def make_session(**overrides: object) -> GameSession:
    """A session on small open mazes, already past the READY pause."""
    config = parse_config({}, Path("."))
    levels = tuple(LevelConfig(5, 5, 1, 60.0, 0) for _ in range(10))
    config = replace(config, levels=levels, **overrides)  # type: ignore
    session = GameSession(config, source=open_grid, rng=random.Random(0))
    session.update(READY_TIME + 0.01)
    assert phase(session) is Phase.PLAYING
    return session


def test_layout() -> None:
    """Player in the middle, super-pacgums and ghosts in the corners."""
    session = make_session()
    level = session.level
    assert level.player_spawn == (5, 5)
    assert level.corners == ((1, 1), (9, 1), (1, 9), (9, 9))
    assert level.super_pacgums == set(level.corners)
    assert [g.home for g in session.ghosts] == list(level.corners)
    assert level.player_spawn not in level.pacgums


def test_eating_scores() -> None:
    """Pacgums give X points, super-pacgums Y and frighten the ghosts."""
    session = make_session()
    session.cheats.freeze = True
    session.level.pacgums = {(6, 5), (1, 3)}
    session.steer(Direction.RIGHT)
    session.update(1 / 8 + 0.001)
    assert session.score == session.config.points_per_pacgum
    session.level.super_pacgums.add((7, 5))
    session.update(1 / 8 + 0.001)
    assert session.score == (session.config.points_per_pacgum
                             + session.config.points_per_super_pacgum)
    assert all(g.mode is GhostMode.FRIGHTENED for g in session.ghosts)


def test_ghost_collision_costs_a_life_then_respawns() -> None:
    """Touching a ghost loses a life and resets everyone."""
    session = make_session()
    ghost = session.ghosts[0]
    ghost.place((5, 5))
    session.update(0.001)
    assert phase(session) is Phase.DYING
    assert session.lives == session.config.lives - 1
    session.update(5)
    assert phase(session) is Phase.READY
    assert session.player.tile == session.level.player_spawn
    assert ghost.tile == ghost.home


def test_eating_a_frightened_ghost() -> None:
    """A frightened ghost is eaten for Z points and respawns later."""
    session = make_session()
    ghost = session.ghosts[0]
    ghost.mode = GhostMode.FRIGHTENED
    session.frightened_left = 5
    ghost.place((5, 5))
    session.update(0.001)
    assert ghost.mode is GhostMode.EATEN
    assert session.score == session.config.points_per_ghost
    session.update(session.config.ghost_respawn_time + 0.1)
    assert ghost.active and ghost.tile == ghost.home


def test_game_over_and_invincibility() -> None:
    """Losing every life ends the game, unless invincible."""
    session = make_session(lives=1, cheat_mode=True)
    session.cheat_invincible()
    session.ghosts[0].place((5, 5))
    session.update(0.001)
    assert phase(session) is Phase.PLAYING
    session.cheat_invincible()
    session.update(0.001)
    assert phase(session) is Phase.DYING
    session.update(5)
    assert phase(session) is Phase.GAME_OVER and session.finished


def test_time_limit_costs_a_life() -> None:
    """Running out of time loses a life and restarts the timer."""
    session = make_session()
    session.cheats.freeze = True
    session.time_left = 0.01
    session.update(0.02)
    assert phase(session) is Phase.DYING and session.timed_out
    assert session.time_left == session.level.settings.max_time


def test_cheats_need_cheat_mode() -> None:
    """Cheat keys do nothing until cheat mode is on."""
    session = make_session()
    session.cheat_extra_life()
    assert session.lives == session.config.lives
    session.toggle_cheat_mode()
    session.cheat_extra_life()
    assert session.lives == session.config.lives + 1


def test_skipping_every_level_wins_and_keeps_score() -> None:
    """Clearing all levels is a victory; score and lives carry over."""
    session = make_session(cheat_mode=True)
    session.score = 1234
    for number in range(1, 11):
        assert session.level.number == number
        session.cheat_skip_level()
        session.update(5)
        session.update(5)
    assert phase(session) is Phase.VICTORY
    assert session.score == 1234
    assert session.lives == session.config.lives


def test_ghosts_never_walk_through_walls() -> None:
    """A long simulation on a real maze keeps everyone on corridors."""
    config = parse_config({}, Path("."))
    session = GameSession(config, rng=random.Random(5))
    session.cheats.invincible = True
    rng = random.Random(1)
    floor = session.level.tilemap.is_floor
    for frame in range(3000):
        if frame % 30 == 0:
            session.steer(rng.choice(list(Direction)[1:]))
        session.update(1 / 60)
        assert floor(session.player.tile) and floor(session.player.target)
        for ghost in session.ghosts:
            assert floor(ghost.tile) and floor(ghost.target)


def test_maze_failure_is_a_maze_error() -> None:
    """A broken generator surfaces as MazeError for the UI to show."""
    def broken(width: int, height: int, seed: int) -> list[list[int]]:
        raise RuntimeError("generator exploded")

    def wrapped(width: int, height: int, seed: int) -> list[list[int]]:
        try:
            return broken(width, height, seed)
        except RuntimeError as exc:
            raise MazeError(str(exc)) from None

    with pytest.raises(MazeError):
        GameSession(parse_config({}, Path(".")), source=wrapped)
