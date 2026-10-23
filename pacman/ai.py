"""Ghost decision making.

At every tile centre a ghost picks one of the open directions, avoiding a
U-turn unless it is in a dead end.  In chase or scatter mode it takes the
direction that brings it closest (by walking distance) to its *target*
tile; when frightened it takes the one that gets it furthest from the
player.  The four personalities only differ in how they pick the target:

* ``hunter`` (the Baron): the player's tile.
* ``ambusher`` (Rabban): four tiles ahead of the player.
* ``trickster`` (Feyd-Rautha): sometimes hunts, sometimes wanders.
* ``coward`` (the Sardaukar): hunts from afar, retreats home up close.
"""

from __future__ import annotations

import math
import random

from pacman.entities import MOVES, Direction, Ghost, GhostMode, Player
from pacman.maze import Pos, TileMap

PERSONALITIES = ("hunter", "ambusher", "trickster", "coward")
AMBUSH_LOOKAHEAD = 4
COWARD_RADIUS = 8
TRICKSTER_RANDOMNESS = 0.35
FRIGHTENED_RANDOMNESS = 0.2


def chase_target(ghost: Ghost, player: Player, tilemap: TileMap,
                 rng: random.Random) -> Pos:
    """Return the tile ``ghost`` aims for while chasing ``player``."""
    if ghost.personality == "ambusher":
        facing = player.direction if player.moving else player.facing
        ahead = player.nearest_tile
        for _ in range(AMBUSH_LOOKAHEAD):
            nxt = facing.step(ahead)
            if not tilemap.is_floor(nxt):
                break
            ahead = nxt
        return ahead
    if ghost.personality == "coward":
        if _manhattan(ghost.tile, player.nearest_tile) <= COWARD_RADIUS:
            return ghost.home
    if ghost.personality == "trickster":
        if rng.random() < TRICKSTER_RANDOMNESS:
            return rng.choice(tilemap.floor_tiles())
    return player.nearest_tile


def choose_direction(ghost: Ghost, player: Player, tilemap: TileMap,
                     rng: random.Random) -> Direction:
    """Pick the next direction for ``ghost`` at a tile centre.

    Args:
        ghost: The ghost deciding.
        player: The player, used for targeting.
        tilemap: The maze.
        rng: Random source (seeded per level for reproducibility).

    Returns:
        An open direction, or ``Direction.NONE`` if boxed in.
    """
    options = [d for d in MOVES if tilemap.is_floor(d.step(ghost.tile))]
    if not options:
        return Direction.NONE
    if ghost.direction is not Direction.NONE and len(options) > 1:
        forward = [d for d in options if d is not ghost.direction.opposite]
        options = forward or options
    if len(options) == 1:
        return options[0]

    if ghost.mode is GhostMode.FRIGHTENED:
        if rng.random() < FRIGHTENED_RANDOMNESS:
            return rng.choice(options)
        away = tilemap.distances_from(player.nearest_tile)
        return max(options, key=lambda d: (
            away.get(d.step(ghost.tile), 0), rng.random()))

    if ghost.mode is GhostMode.SCATTER:
        target = ghost.home
    else:
        target = chase_target(ghost, player, tilemap, rng)
    toward = tilemap.distances_from(target)

    def cost(direction: Direction) -> tuple[float, float]:
        nxt = direction.step(ghost.tile)
        if nxt in toward:
            return float(toward[nxt]), rng.random()
        return math.dist(nxt, target) + tilemap.width, rng.random()

    return min(options, key=cost)


def _manhattan(a: Pos, b: Pos) -> int:
    """Return the Manhattan distance between two tiles."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
