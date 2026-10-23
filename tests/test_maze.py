"""Tests of the A-Maze-ing adapter."""

import pytest

from pacman.maze import (BLOCK, FLOOR, WALL, MazeError, amazeing_cells,
                         cells_to_tilemap, load_maze)


def test_two_open_cells() -> None:
    """Two cells with no wall between them form a 3-tile corridor."""
    tilemap = cells_to_tilemap([[1 | 4 | 8, 1 | 2 | 4]])
    assert (tilemap.width, tilemap.height) == (5, 3)
    assert tilemap.tiles[1] == [WALL, FLOOR, FLOOR, FLOOR, WALL]
    assert all(t == WALL for t in tilemap.tiles[0] + tilemap.tiles[2])


def test_closed_cells_become_blocks() -> None:
    """Fully walled cells (the '42') become BLOCK tiles."""
    tilemap = cells_to_tilemap([[15, 15], [15, 15]])
    assert tilemap.tiles[1][1] == BLOCK
    assert tilemap.tiles[1][2] == BLOCK
    assert tilemap.tiles[2][2] == BLOCK
    assert tilemap.floor_tiles() == []


@pytest.mark.parametrize("cells", [[], [[]], [[1, 2], [3]], [["x"]]])
def test_bad_grids(cells: list[list[int]]) -> None:
    """Malformed generator output is a MazeError."""
    with pytest.raises(MazeError):
        cells_to_tilemap(cells)


def test_real_generator_is_connected() -> None:
    """Every corridor of a real maze is reachable from any other."""
    tilemap, seed = load_maze(15, 11, 42)
    assert seed == 42
    floors = tilemap.floor_tiles()
    reach = tilemap.distances_from(floors[0])
    assert set(reach) == set(floors)
    assert any(BLOCK in row for row in tilemap.tiles)


def test_same_seed_same_maze() -> None:
    """The first level is reproducible."""
    assert amazeing_cells(17, 13, 42) == amazeing_cells(17, 13, 42)


def test_big_maze_does_not_hit_recursion_limit() -> None:
    """The adapter raises the recursion limit the generator needs."""
    tilemap, _ = load_maze(45, 35, 3)
    assert tilemap.width == 91


def test_failing_generator_is_retried_then_reported() -> None:
    """A generator that keeps failing gives a MazeError, not a crash."""
    calls: list[int] = []

    def broken(width: int, height: int, seed: int) -> list[list[int]]:
        calls.append(seed)
        raise MazeError("boom")

    with pytest.raises(MazeError, match="boom"):
        load_maze(10, 10, 1, source=broken)
    assert len(calls) == 3
