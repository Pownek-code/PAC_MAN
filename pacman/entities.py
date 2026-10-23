"""Moving actors: the player (Muad'Dib) and the Harkonnen ghosts.

Actors move from tile centre to tile centre.  ``tile`` is the tile being
left, ``target`` the tile being entered and ``progress`` how far along
that step they are (0..1), which gives smooth movement at any speed.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from pacman.maze import Pos, TileMap


class Direction(Enum):
    """The four movement directions, plus standing still."""

    NONE = (0, 0)
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)

    @property
    def dx(self) -> int:
        """Horizontal step."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Vertical step."""
        return self.value[1]

    @property
    def opposite(self) -> Direction:
        """The direction pointing the other way."""
        return Direction((-self.dx, -self.dy))

    def step(self, pos: Pos) -> Pos:
        """Return the tile next to ``pos`` in this direction."""
        return pos[0] + self.dx, pos[1] + self.dy


MOVES: tuple[Direction, ...] = (
    Direction.UP, Direction.LEFT, Direction.DOWN, Direction.RIGHT)


class Mover:
    """Something that walks along corridors one tile at a time."""

    def __init__(self, tile: Pos, speed: float) -> None:
        """Place the mover, standing still, at the centre of ``tile``."""
        self.speed = speed
        self.tile = tile
        self.target = tile
        self.progress = 0.0
        self.direction = Direction.NONE
        self.facing = Direction.LEFT

    def place(self, tile: Pos) -> None:
        """Teleport to ``tile`` and stop."""
        self.tile = tile
        self.target = tile
        self.progress = 0.0
        self.direction = Direction.NONE

    @property
    def moving(self) -> bool:
        """True while between two tiles."""
        return self.target != self.tile

    @property
    def position(self) -> tuple[float, float]:
        """Current position in tile units (tile centres are integers)."""
        return (self.tile[0] + (self.target[0] - self.tile[0])
                * self.progress,
                self.tile[1] + (self.target[1] - self.tile[1])
                * self.progress)

    @property
    def nearest_tile(self) -> Pos:
        """The tile the mover is mostly on."""
        return self.target if self.progress >= 0.5 else self.tile

    def reverse(self) -> None:
        """Turn around in the middle of a step."""
        if self.moving:
            self.tile, self.target = self.target, self.tile
            self.progress = 1.0 - self.progress
            self.direction = self.direction.opposite
            self.facing = self.direction

    def advance(self, dt: float, tilemap: TileMap,
                choose: Callable[[], Direction],
                speed_factor: float = 1.0) -> list[Pos]:
        """Move for ``dt`` seconds.

        Args:
            dt: Elapsed time in seconds.
            tilemap: The maze, to know which tiles are walkable.
            choose: Called on every tile centre to pick the next direction.
            speed_factor: Multiplier applied to ``speed``.

        Returns:
            The tiles whose centre was reached during this update.
        """
        reached: list[Pos] = []
        budget = self.speed * speed_factor * dt
        while budget > 1e-9:
            if not self.moving:
                direction = choose()
                nxt = direction.step(self.tile)
                if direction is Direction.NONE or not tilemap.is_floor(nxt):
                    self.direction = Direction.NONE
                    break
                self.direction = direction
                self.facing = direction
                self.target = nxt
                self.progress = 0.0
            step = min(budget, 1.0 - self.progress)
            self.progress += step
            budget -= step
            if self.progress >= 1.0 - 1e-9:
                self.tile = self.target
                self.progress = 0.0
                reached.append(self.tile)
        return reached


class Player(Mover):
    """Muad'Dib, steered by the keyboard."""

    def __init__(self, tile: Pos, speed: float) -> None:
        """Create the player at ``tile``."""
        super().__init__(tile, speed)
        self.wanted = Direction.NONE

    def steer(self, direction: Direction) -> None:
        """Remember the direction the player asked for.

        Reversing is applied at once; other turns wait for the next
        tile centre where they are possible.
        """
        self.wanted = direction
        if self.moving and direction is self.direction.opposite:
            self.reverse()

    def choose(self, tilemap: TileMap) -> Direction:
        """Pick the wanted direction if open, else keep going straight."""
        for direction in (self.wanted, self.direction):
            if (direction is not Direction.NONE
                    and tilemap.is_floor(direction.step(self.tile))):
                return direction
        return Direction.NONE


class GhostMode(Enum):
    """What a ghost is currently doing."""

    SCATTER = "scatter"
    CHASE = "chase"
    FRIGHTENED = "frightened"
    EATEN = "eaten"


class Ghost(Mover):
    """A Harkonnen hunter."""

    def __init__(self, name: str, personality: str, home: Pos,
                 speed: float) -> None:
        """Create a ghost waiting at its ``home`` corner.

        Args:
            name: Display name.
            personality: One of ``ai.PERSONALITIES``.
            home: Corner tile it spawns in and scatters to.
            speed: Normal speed in tiles per second.
        """
        super().__init__(home, speed)
        self.name = name
        self.personality = personality
        self.home = home
        self.mode = GhostMode.SCATTER
        self.respawn_timer = 0.0

    @property
    def edible(self) -> bool:
        """True while the player can eat this ghost."""
        return self.mode is GhostMode.FRIGHTENED

    @property
    def active(self) -> bool:
        """True while the ghost is on the board."""
        return self.mode is not GhostMode.EATEN

    def send_home(self, mode: GhostMode) -> None:
        """Put the ghost back in its corner."""
        self.place(self.home)
        self.mode = mode
        self.respawn_timer = 0.0
