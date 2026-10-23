"""Turn a generated maze into a playable level layout."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pacman.config import LevelConfig
from pacman.maze import CellSource, Pos, TileMap, amazeing_cells, load_maze


@dataclass
class Level:
    """Everything that describes one level at its start.

    Attributes:
        number: 1-based level number.
        settings: The level's configuration.
        seed: The seed that generated the maze.
        tilemap: The maze tiles.
        player_spawn: Middle of the maze, where the player (re)spawns.
        corners: The four corner tiles (ghost homes, super-pacgums).
        pacgums: Tiles still holding a pacgum.
        super_pacgums: Tiles still holding a super-pacgum.
    """

    number: int
    settings: LevelConfig
    seed: int
    tilemap: TileMap
    player_spawn: Pos
    corners: tuple[Pos, Pos, Pos, Pos]
    pacgums: set[Pos]
    super_pacgums: set[Pos]

    @property
    def remaining(self) -> int:
        """How many pacgums (of both kinds) are left."""
        return len(self.pacgums) + len(self.super_pacgums)


def build_level(number: int, settings: LevelConfig, seed: int,
                source: CellSource = amazeing_cells) -> Level:
    """Generate the maze of a level and place spawns and pacgums.

    Args:
        number: 1-based level number.
        settings: The level's configuration.
        seed: Seed passed to the maze generator.
        source: Function producing the generator's cell grid.

    Returns:
        A ready to play level.

    Raises:
        MazeError: If no maze could be generated.
    """
    tilemap, seed = load_maze(settings.width, settings.height, seed, source)
    centre = (tilemap.width // 2, tilemap.height // 2)
    spawn = tilemap.nearest_floor(centre)
    assert spawn is not None  # load_maze guarantees at least one corridor
    reachable = set(tilemap.distances_from(spawn))

    right, bottom = tilemap.width - 2, tilemap.height - 2
    corners: list[Pos] = []
    for corner in ((1, 1), (right, 1), (1, bottom), (right, bottom)):
        tile = tilemap.nearest_floor(corner, reachable)
        corners.append(tile if tile is not None else spawn)

    supers = set(corners) - {spawn}
    candidates = sorted(reachable - supers - {spawn},
                        key=lambda p: (p[1], p[0]))
    if 0 < settings.pacgum < len(candidates):
        rng = random.Random(seed)
        candidates = rng.sample(candidates, settings.pacgum)
    return Level(
        number=number,
        settings=settings,
        seed=seed,
        tilemap=tilemap,
        player_spawn=spawn,
        corners=(corners[0], corners[1], corners[2], corners[3]),
        pacgums=set(candidates),
        super_pacgums=supers,
    )
