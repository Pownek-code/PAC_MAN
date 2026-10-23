"""Adapter around the assigned A-Maze-ing package (``mazegenerator``).

The package produces a grid of *cells*, each cell an int whose four low
bits are its walls (N=1, E=2, S=4, W=8).  Pac-Man needs *tiles* instead:
corridors you walk along and walls you bump into.  Each cell becomes the
tile at ``(2x+1, 2y+1)``; the tile between two neighbouring cells is a
corridor when neither cell has a wall on that side, and every other tile
is a wall.  Fully closed cells (the '42' drawn by the generator) are
marked as ``BLOCK`` tiles so they can be drawn as a special rock.

The package itself is used as-is: only its public constructor and its
``maze`` property are touched.
"""

from __future__ import annotations

import contextlib
import io
import logging
import random
import sys
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

LOG = logging.getLogger("pacman.maze")

WALL, FLOOR, BLOCK = 0, 1, 2
NORTH, EAST, SOUTH, WEST = 1, 2, 4, 8
ALL_WALLS = NORTH | EAST | SOUTH | WEST

Pos = tuple[int, int]
CellGrid = list[list[int]]
CellSource = Callable[[int, int, int], CellGrid]

NEIGHBOUR_STEPS: tuple[Pos, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


class MazeError(Exception):
    """Raised when no usable maze could be produced."""


@dataclass
class TileMap:
    """A rectangular grid of ``WALL``, ``FLOOR`` and ``BLOCK`` tiles."""

    width: int
    height: int
    tiles: list[list[int]]

    def in_bounds(self, pos: Pos) -> bool:
        """Return True if ``pos`` lies inside the map."""
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_floor(self, pos: Pos) -> bool:
        """Return True if ``pos`` is a walkable corridor tile."""
        return self.in_bounds(pos) and self.tiles[pos[1]][pos[0]] == FLOOR

    def tile(self, pos: Pos) -> int:
        """Return the tile type at ``pos`` (``WALL`` outside the map)."""
        return self.tiles[pos[1]][pos[0]] if self.in_bounds(pos) else WALL

    def floor_neighbours(self, pos: Pos) -> Iterator[Pos]:
        """Yield the walkable tiles next to ``pos``."""
        for dx, dy in NEIGHBOUR_STEPS:
            nxt = (pos[0] + dx, pos[1] + dy)
            if self.is_floor(nxt):
                yield nxt

    def floor_tiles(self) -> list[Pos]:
        """Return every walkable tile, row by row."""
        return [(x, y) for y in range(self.height)
                for x in range(self.width) if self.tiles[y][x] == FLOOR]

    def distances_from(self, start: Pos) -> dict[Pos, int]:
        """Return the walking distance from ``start`` to every reachable tile.

        Args:
            start: Starting tile; an empty dict is returned if it is a wall.

        Returns:
            A mapping from tile to number of steps.
        """
        if not self.is_floor(start):
            return {}
        dist = {start: 0}
        queue: deque[Pos] = deque([start])
        while queue:
            current = queue.popleft()
            for nxt in self.floor_neighbours(current):
                if nxt not in dist:
                    dist[nxt] = dist[current] + 1
                    queue.append(nxt)
        return dist

    def nearest_floor(self, target: Pos,
                      allowed: set[Pos] | None = None) -> Pos | None:
        """Return the floor tile closest (Manhattan) to ``target``.

        Args:
            target: Any position, even outside the map.
            allowed: Optional subset of tiles to choose from.

        Returns:
            The closest tile, or None if there is no candidate.
        """
        candidates = allowed if allowed is not None else self.floor_tiles()
        best: Pos | None = None
        best_key = (sys.maxsize, sys.maxsize, sys.maxsize)
        for pos in candidates:
            key = (abs(pos[0] - target[0]) + abs(pos[1] - target[1]),
                   pos[1], pos[0])
            if key < best_key:
                best, best_key = pos, key
        return best


def cells_to_tilemap(cells: Sequence[Sequence[int]]) -> TileMap:
    """Convert the generator's wall-bit cells into a tile map.

    Args:
        cells: ``cells[y][x]`` wall bits as produced by ``mazegenerator``.

    Returns:
        A ``(2w+1) x (2h+1)`` tile map.

    Raises:
        MazeError: If ``cells`` is not a non-empty rectangular int grid.
    """
    height = len(cells)
    width = len(cells[0]) if height else 0
    if width == 0 or any(len(row) != width for row in cells):
        raise MazeError("the maze generator returned a non-rectangular grid")
    for row in cells:
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int):
                raise MazeError(
                    f"the maze generator returned a bad cell {value!r}")

    tiles = [[WALL] * (2 * width + 1) for _ in range(2 * height + 1)]
    for y in range(height):
        for x in range(width):
            walls = cells[y][x] & ALL_WALLS
            kind = BLOCK if walls == ALL_WALLS else FLOOR
            tiles[2 * y + 1][2 * x + 1] = kind
            if x + 1 < width:
                right = cells[y][x + 1] & ALL_WALLS
                if kind == BLOCK and right == ALL_WALLS:
                    tiles[2 * y + 1][2 * x + 2] = BLOCK
                elif not walls & EAST and not right & WEST:
                    tiles[2 * y + 1][2 * x + 2] = FLOOR
            if y + 1 < height:
                below = cells[y + 1][x] & ALL_WALLS
                if kind == BLOCK and below == ALL_WALLS:
                    tiles[2 * y + 2][2 * x + 1] = BLOCK
                elif not walls & SOUTH and not below & NORTH:
                    tiles[2 * y + 2][2 * x + 1] = FLOOR
            if x + 1 < width and y + 1 < height and all(
                    cells[y + dy][x + dx] & ALL_WALLS == ALL_WALLS
                    for dx in (0, 1) for dy in (0, 1)):
                tiles[2 * y + 2][2 * x + 2] = BLOCK
    return TileMap(2 * width + 1, 2 * height + 1, tiles)


def amazeing_cells(width: int, height: int, seed: int) -> CellGrid:
    """Generate a maze with the assigned ``mazegenerator`` package.

    Args:
        width: Width in cells.
        height: Height in cells.
        seed: Positive seed (the package treats 0 as "random").

    Returns:
        The package's ``maze`` grid.

    Raises:
        MazeError: If the package is missing or fails in any way.
    """
    try:
        from mazegenerator import MazeGenerator
    except ImportError:
        raise MazeError("the 'mazegenerator' package is not installed "
                        "(run 'make install')") from None

    # The package carves the maze recursively (one frame per cell), so
    # big mazes need more than Python's default limit of 1000 frames.
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, width * height * 4 + 1000))
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            generator = MazeGenerator(size=(width, height), perfect=False,
                                      seed=seed)
            cells = generator.maze
    except RecursionError:
        raise MazeError(f"maze {width}x{height} is too big for the "
                        f"generator") from None
    except Exception as exc:
        raise MazeError(f"the maze generator failed: {exc}") from None
    finally:
        sys.setrecursionlimit(old_limit)
        for line in printed.getvalue().splitlines():
            if line.strip():
                LOG.info("mazegenerator: %s", line.strip())
    if not isinstance(cells, list) or not all(
            isinstance(row, list) for row in cells):
        raise MazeError("the maze generator returned no grid")
    if len(cells) != height or any(len(row) != width for row in cells):
        raise MazeError(f"the maze generator returned a grid of the wrong "
                        f"size (expected {width}x{height})")
    return cells


def load_maze(width: int, height: int, seed: int,
              source: CellSource = amazeing_cells,
              attempts: int = 3) -> tuple[TileMap, int]:
    """Generate a maze and convert it to tiles, retrying on failure.

    Args:
        width: Width in cells.
        height: Height in cells.
        seed: Seed of the first attempt.
        source: Function producing the cell grid.
        attempts: How many seeds to try before giving up.

    Returns:
        The tile map and the seed that actually produced it.

    Raises:
        MazeError: If every attempt failed.
    """
    rng = random.Random(seed)
    error: MazeError | None = None
    for attempt in range(attempts):
        try:
            tilemap = cells_to_tilemap(source(width, height, seed))
            if not tilemap.floor_tiles():
                raise MazeError("the maze has no corridor")
            return tilemap, seed
        except MazeError as exc:
            error = exc
            LOG.warning("maze attempt %d (seed %d) failed: %s",
                        attempt + 1, seed, exc)
            seed = rng.randint(1, 2**31 - 1)
    assert error is not None
    raise error
