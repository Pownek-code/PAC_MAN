"""Game rules: one play-through from level 1 to victory or game over.

This module has no pygame dependency, so the whole game logic can be
tested headless.  The UI calls ``update`` every frame and reads the public
attributes to draw the board.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

from pacman.ai import PERSONALITIES, choose_direction
from pacman.config import GameConfig
from pacman.entities import Direction, Ghost, GhostMode, Player
from pacman.level import Level, build_level
from pacman.maze import CellSource, Pos, amazeing_cells

GHOST_NAMES = ("Baron", "Rabban", "Feyd", "Sardaukar")
# Ghosts alternate between scattering to their corner and hunting.
MODE_SCHEDULE: tuple[tuple[GhostMode, float], ...] = (
    (GhostMode.SCATTER, 5.0), (GhostMode.CHASE, 20.0))
READY_TIME = 2.0
DYING_TIME = 1.6
CLEARED_TIME = 2.0
POPUP_TIME = 1.0
COLLISION_DISTANCE = 0.6
FRIGHTENED_SPEED = 0.55
CHEAT_SPEED = 1.7
MAX_LIVES = 99


class Phase(Enum):
    """Where the session is in its life cycle."""

    READY = "ready"
    PLAYING = "playing"
    DYING = "dying"
    CLEARED = "cleared"
    GAME_OVER = "game over"
    VICTORY = "victory"


@dataclass
class Cheats:
    """Reviewer helpers; the toggles only work while ``enabled``."""

    enabled: bool = False
    invincible: bool = False
    freeze: bool = False
    fast: bool = False


@dataclass
class Popup:
    """A short-lived score label shown on the board."""

    position: tuple[float, float]
    text: str
    ttl: float = POPUP_TIME


class GameSession:
    """The state of one game, from the first level to the end."""

    def __init__(self, config: GameConfig,
                 source: CellSource = amazeing_cells,
                 rng: random.Random | None = None) -> None:
        """Start a new game on level 1.

        Args:
            config: Validated game configuration.
            source: Maze cell generator (the A-Maze-ing package).
            rng: Random source for the seeds of levels 2 and up.

        Raises:
            MazeError: If the first maze cannot be generated.
        """
        self.config = config
        self.source = source
        self.rng = rng if rng is not None else random.Random()
        self.score = 0
        self.lives = config.lives
        self.cheats = Cheats(enabled=config.cheat_mode)
        self.clock = 0.0
        self.popups: list[Popup] = []
        self.timed_out = False
        self.start_level(0)

    # -- level life cycle -------------------------------------------------

    @property
    def level_count(self) -> int:
        """Number of levels in the campaign."""
        return len(self.config.levels)

    @property
    def finished(self) -> bool:
        """True once the game is won or lost."""
        return self.phase in (Phase.GAME_OVER, Phase.VICTORY)

    def start_level(self, index: int) -> None:
        """Generate and enter level ``index`` (0-based).

        Raises:
            MazeError: If its maze cannot be generated.
        """
        settings = self.config.levels[index]
        seed = (settings.seed if settings.seed is not None
                else self.rng.randint(1, 2**31 - 1))
        level = build_level(index + 1, settings, seed, self.source)
        self.level_index = index
        self.level: Level = level
        self.player = Player(level.player_spawn, self.config.player_speed)
        speed = (self.config.ghost_speed
                 + self.config.ghost_speed_step * index)
        self.ghosts = [Ghost(name, personality, home, speed)
                       for name, personality, home
                       in zip(GHOST_NAMES, PERSONALITIES, level.corners)]
        self.ghost_rng = random.Random(level.seed)
        self.time_left = settings.max_time
        self.frightened_left = 0.0
        self.mode_clock = 0.0
        self.popups.clear()
        self._enter(Phase.READY, READY_TIME)

    def _enter(self, phase: Phase, duration: float = 0.0) -> None:
        """Switch to ``phase`` for ``duration`` seconds."""
        self.phase = phase
        self.phase_timer = duration

    def _reset_positions(self) -> None:
        """Put everybody back on their spawn tile after a lost life."""
        self.player.place(self.level.player_spawn)
        self.player.wanted = Direction.NONE
        for ghost in self.ghosts:
            ghost.send_home(self.scheduled_mode)
        self.frightened_left = 0.0
        self.mode_clock = 0.0

    # -- input ------------------------------------------------------------

    def steer(self, direction: Direction) -> None:
        """Forward a direction key press to the player."""
        if self.phase in (Phase.READY, Phase.PLAYING):
            self.player.steer(direction)

    def toggle_cheat_mode(self) -> None:
        """Enable or disable cheat mode (disabling clears every cheat)."""
        self.cheats = Cheats(enabled=not self.cheats.enabled)

    def cheat_invincible(self) -> None:
        """Toggle invincibility."""
        if self.cheats.enabled:
            self.cheats.invincible = not self.cheats.invincible

    def cheat_freeze(self) -> None:
        """Toggle ghost freeze."""
        if self.cheats.enabled:
            self.cheats.freeze = not self.cheats.freeze

    def cheat_fast(self) -> None:
        """Toggle the player speed boost."""
        if self.cheats.enabled:
            self.cheats.fast = not self.cheats.fast

    def cheat_extra_life(self) -> None:
        """Add a life."""
        if self.cheats.enabled:
            self.lives = min(MAX_LIVES, self.lives + 1)

    def cheat_refill_time(self) -> None:
        """Reset the level timer."""
        if self.cheats.enabled:
            self.time_left = self.level.settings.max_time

    def cheat_skip_level(self) -> None:
        """Win the current level immediately."""
        if self.cheats.enabled and self.phase in (Phase.READY,
                                                  Phase.PLAYING):
            self.level.pacgums.clear()
            self.level.super_pacgums.clear()
            self._enter(Phase.CLEARED, CLEARED_TIME)

    # -- simulation -------------------------------------------------------

    @property
    def scheduled_mode(self) -> GhostMode:
        """The scatter/chase mode the schedule asks for right now."""
        cycle = sum(duration for _, duration in MODE_SCHEDULE)
        moment = self.mode_clock % cycle
        for mode, duration in MODE_SCHEDULE:
            if moment < duration:
                return mode
            moment -= duration
        return GhostMode.CHASE

    def update(self, dt: float) -> None:
        """Advance the game by ``dt`` seconds.

        Raises:
            MazeError: If the next level's maze cannot be generated.
        """
        self.clock += dt
        for popup in self.popups:
            popup.ttl -= dt
        self.popups = [p for p in self.popups if p.ttl > 0]
        self.phase_timer -= dt
        if self.phase is Phase.READY:
            if self.phase_timer <= 0:
                self._enter(Phase.PLAYING)
        elif self.phase is Phase.DYING:
            if self.phase_timer <= 0:
                self.timed_out = False
                if self.lives <= 0:
                    self._enter(Phase.GAME_OVER)
                else:
                    self._reset_positions()
                    self._enter(Phase.READY, READY_TIME)
        elif self.phase is Phase.CLEARED:
            if self.phase_timer <= 0:
                if self.level_index + 1 >= self.level_count:
                    self._enter(Phase.VICTORY)
                else:
                    self.start_level(self.level_index + 1)
        elif self.phase is Phase.PLAYING:
            self._play(dt)

    def _play(self, dt: float) -> None:
        """Run one frame of actual gameplay."""
        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0:
            self.timed_out = True
            self.time_left = self.level.settings.max_time
            self._lose_life()
            return

        self.mode_clock += dt
        if self.frightened_left > 0:
            self.frightened_left = max(0.0, self.frightened_left - dt)
            if self.frightened_left == 0:
                for ghost in self.ghosts:
                    if ghost.mode is GhostMode.FRIGHTENED:
                        ghost.mode = self.scheduled_mode
        for ghost in self.ghosts:
            if ghost.mode in (GhostMode.SCATTER, GhostMode.CHASE):
                if ghost.mode is not self.scheduled_mode:
                    ghost.mode = self.scheduled_mode
                    ghost.reverse()

        tilemap = self.level.tilemap
        factor = CHEAT_SPEED if self.cheats.fast else 1.0
        for tile in self.player.advance(
                dt, tilemap, lambda: self.player.choose(tilemap), factor):
            self._eat(tile)
        if self.level.remaining == 0:
            self._enter(Phase.CLEARED, CLEARED_TIME)
            return

        for ghost in self.ghosts:
            self._move_ghost(ghost, dt)
        self._check_collisions()

    def _move_ghost(self, ghost: Ghost, dt: float) -> None:
        """Move one ghost, or count down its respawn if it was eaten."""
        if ghost.mode is GhostMode.EATEN:
            ghost.respawn_timer -= dt
            if ghost.respawn_timer <= 0:
                ghost.send_home(self.scheduled_mode)
            return
        if self.cheats.freeze:
            return
        factor = FRIGHTENED_SPEED if ghost.edible else 1.0
        ghost.advance(dt, self.level.tilemap,
                      lambda: choose_direction(ghost, self.player,
                                               self.level.tilemap,
                                               self.ghost_rng),
                      factor)

    def _eat(self, tile: Pos) -> None:
        """Eat whatever lies on ``tile``."""
        if tile in self.level.pacgums:
            self.level.pacgums.discard(tile)
            self.score += self.config.points_per_pacgum
        elif tile in self.level.super_pacgums:
            self.level.super_pacgums.discard(tile)
            self.score += self.config.points_per_super_pacgum
            self.frightened_left = self.config.frightened_time
            for ghost in self.ghosts:
                if ghost.active:
                    if not ghost.edible:
                        ghost.reverse()
                    ghost.mode = GhostMode.FRIGHTENED

    def _check_collisions(self) -> None:
        """Resolve contacts between the player and the ghosts."""
        player = self.player
        for ghost in self.ghosts:
            if not ghost.active:
                continue
            crossed = (player.moving and ghost.moving
                       and ghost.tile == player.target
                       and ghost.target == player.tile)
            close = math.dist(ghost.position,
                              player.position) < COLLISION_DISTANCE
            if not (close or crossed):
                continue
            if ghost.edible:
                ghost.mode = GhostMode.EATEN
                ghost.respawn_timer = self.config.ghost_respawn_time
                self.score += self.config.points_per_ghost
                self.popups.append(Popup(ghost.position,
                                         str(self.config.points_per_ghost)))
            elif not self.cheats.invincible:
                self._lose_life()
                return

    def _lose_life(self) -> None:
        """Take a life away (unless invincible) and play the death."""
        if self.cheats.invincible:
            return
        self.lives -= 1
        self._enter(Phase.DYING, DYING_TIME)
