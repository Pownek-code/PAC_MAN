"""Draw a running ``GameSession``: the maze, the actors and the HUD."""

from __future__ import annotations

import math
import random

import pygame

from pacman import theme
from pacman.entities import Direction, GhostMode
from pacman.game import DYING_TIME, GameSession, Phase
from pacman.level import Level
from pacman.maze import BLOCK, FLOOR, TileMap

HUD_HEIGHT = 64
FOOTER_HEIGHT = 30
MARGIN = 12
FLASH_TIME = 2.0
FACING_ANGLE = {
    Direction.RIGHT: 0.0, Direction.UP: 90.0,
    Direction.LEFT: 180.0, Direction.DOWN: 270.0, Direction.NONE: 180.0,
}


class BoardRenderer:
    """Draws one level, with its static maze cached on a surface."""

    def __init__(self, level: Level, screen_size: tuple[int, int]) -> None:
        """Fit ``level`` into the screen area below the HUD."""
        self.level = level
        tilemap = level.tilemap
        width, height = screen_size
        avail_w = width - 2 * MARGIN
        avail_h = height - HUD_HEIGHT - FOOTER_HEIGHT - 2 * MARGIN
        self.tile = max(4, min(avail_w // tilemap.width,
                               avail_h // tilemap.height))
        board_w = tilemap.width * self.tile
        board_h = tilemap.height * self.tile
        self.origin = ((width - board_w) // 2,
                       HUD_HEIGHT + MARGIN + (avail_h - board_h) // 2)
        self.maze = paint_maze(tilemap, self.tile, level.seed)
        self.dot_glow = theme.glow(round(self.tile * 0.4), theme.SPICE, 70)
        self.super_glow = theme.glow(round(self.tile * 0.95), theme.MELANGE,
                                     110)

    def to_screen(self, pos: tuple[float, float]) -> tuple[float, float]:
        """Convert a tile position to the pixel centre of that tile."""
        return (self.origin[0] + (pos[0] + 0.5) * self.tile,
                self.origin[1] + (pos[1] + 0.5) * self.tile)

    def draw(self, surface: pygame.Surface, session: GameSession) -> None:
        """Draw the board and every actor."""
        board = self.maze.get_rect(topleft=self.origin)
        pygame.draw.rect(surface, theme.ROCK_SHADOW, board.inflate(8, 8),
                         border_radius=6)
        surface.blit(self.maze, board)
        self._draw_pacgums(surface, session.clock)
        self._draw_ghosts(surface, session)
        self._draw_player(surface, session)
        for popup in session.popups:
            x, y = self.to_screen(popup.position)
            rise = (1 - popup.ttl) * self.tile
            theme.text(surface, popup.text, max(14, round(self.tile * 1.2)),
                       theme.SPICE_CORE, center=(x, y - rise))
        self._draw_banner(surface, session)

    def _draw_pacgums(self, surface: pygame.Surface, clock: float) -> None:
        """Draw the spice grains and the pulsing melange orbs."""
        dot = max(1.5, self.tile * 0.12)
        half = self.dot_glow.get_width() / 2
        for pos in self.level.pacgums:
            x, y = self.to_screen(pos)
            surface.blit(self.dot_glow, (x - half, y - half))
            pygame.draw.circle(surface, theme.SPICE, (x, y), dot)
        pulse = 0.5 + 0.5 * math.sin(clock * 6)
        half = self.super_glow.get_width() / 2
        for pos in self.level.super_pacgums:
            x, y = self.to_screen(pos)
            surface.blit(self.super_glow, (x - half, y - half))
            radius = self.tile * (0.28 + 0.07 * pulse)
            pygame.draw.circle(surface, theme.MELANGE, (x, y), radius)
            pygame.draw.circle(surface, theme.SPICE_CORE, (x, y),
                               radius * 0.45)

    def _draw_ghosts(self, surface: pygame.Surface,
                     session: GameSession) -> None:
        """Draw the Harkonnen, or their worm sign once eaten."""
        radius = self.tile * 0.46
        flashing = (0 < session.frightened_left < FLASH_TIME
                    and int(session.clock * 6) % 2 == 0)
        for ghost in session.ghosts:
            if ghost.mode is GhostMode.EATEN:
                theme.draw_worm_sign(surface, self.to_screen(ghost.home),
                                     radius, session.clock)
                continue
            if session.phase is Phase.DYING:
                continue
            color = theme.GHOST_COLORS.get(ghost.name, theme.SAND)
            if ghost.edible:
                color = (theme.FRIGHTENED_FLASH if flashing
                         else theme.FRIGHTENED)
            look = ghost.direction.value if ghost.moving else (0, 0)
            theme.draw_ghost(surface, self.to_screen(ghost.position), radius,
                             color, look, session.clock, ghost.edible)

    def _draw_player(self, surface: pygame.Surface,
                     session: GameSession) -> None:
        """Draw Muad'Dib, chomping, or sinking into the sand when caught."""
        player = session.player
        center = self.to_screen(player.position)
        radius = self.tile * 0.46
        if session.phase is Phase.DYING:
            t = 1 - max(0.0, session.phase_timer) / DYING_TIME
            theme.draw_player(surface, center, radius,
                              90.0, 30 + 150 * min(1.0, t * 1.3))
            if t > 0.6:
                self._sand_burst(surface, center, radius, t)
            return
        chomp = abs(math.sin(session.clock * 14)) if player.moving else 0.3
        theme.draw_player(surface, center, radius,
                          FACING_ANGLE[player.facing], 4 + 40 * chomp)
        if session.cheats.invincible:
            shield = theme.glow(round(radius * 1.8), theme.FREMEN_BLUE, 90)
            half = shield.get_width() / 2
            surface.blit(shield, (center[0] - half, center[1] - half))

    def _sand_burst(self, surface: pygame.Surface,
                    center: tuple[float, float], radius: float,
                    t: float) -> None:
        """Scatter grains of sand outwards at the end of a death."""
        rng = random.Random(7)
        spread = (t - 0.6) / 0.4
        for _ in range(14):
            angle = rng.uniform(0, math.tau)
            dist = radius * (0.5 + 1.8 * spread * rng.uniform(0.6, 1.0))
            pygame.draw.circle(
                surface, theme.SAND_CREST,
                (center[0] + math.cos(angle) * dist,
                 center[1] + math.sin(angle) * dist),
                max(1.0, radius * 0.12 * (1 - spread)))

    def _draw_banner(self, surface: pygame.Surface,
                     session: GameSession) -> None:
        """Show READY / caught / cleared messages over the board."""
        rect = self.maze.get_rect(topleft=self.origin)
        message = ""
        if session.phase is Phase.READY:
            message = f"LEVEL {session.level.number} - GET READY"
        elif session.phase is Phase.DYING:
            message = ("THE SANDS RAN OUT!" if session.timed_out
                       else "CAUGHT BY THE HARKONNEN!")
        elif session.phase is Phase.CLEARED:
            message = "THE SPICE FLOWS - LEVEL CLEARED!"
        if message:
            size = max(26, min(54, rect.width // 18))
            band = pygame.Surface((rect.width, size * 2), pygame.SRCALPHA)
            band.fill((*theme.PANEL, 210))
            surface.blit(band, band.get_rect(center=rect.center))
            theme.text(surface, message, size, theme.SPICE_CORE,
                       center=rect.center)


def paint_maze(tilemap: TileMap, tile: int, seed: int) -> pygame.Surface:
    """Paint the static part of a maze: rippled sand floor and dune walls.

    Walls are drawn as rounded blobs joined to their wall neighbours, in
    three passes (shadow, body, crest) so they look like dune ridges.

    Args:
        tilemap: The maze.
        tile: Tile size in pixels.
        seed: Seed of the floor ripples.
    """
    width, height = tilemap.width * tile, tilemap.height * tile
    surface = pygame.Surface((width, height))
    surface.fill(theme.FLOOR)
    rng = random.Random(seed)
    spacing = max(4, tile // 2)
    for row in range(0, height + spacing, spacing):
        phase = rng.uniform(0, math.tau)
        points = [(x, row + math.sin(x / (tile * 1.7) + phase) * tile * 0.25)
                  for x in range(0, width + 6, 6)]
        pygame.draw.lines(surface, theme.FLOOR_RIPPLE, False, points, 1)

    passes = (
        (theme.ROCK_SHADOW, theme.ROCK_SHADOW, 0.46, (0.0, 0.12)),
        (theme.SAND, theme.SIETCH, 0.40, (0.0, 0.0)),
        (theme.SAND_CREST, theme.SIETCH_CREST, 0.13, (-0.04, -0.07)),
    )
    for wall_color, block_color, size, (ox, oy) in passes:
        radius = max(1.0, tile * size)
        for y in range(tilemap.height):
            for x in range(tilemap.width):
                kind = tilemap.tiles[y][x]
                if kind == FLOOR:
                    continue
                color = block_color if kind == BLOCK else wall_color
                cx = (x + 0.5 + ox) * tile
                cy = (y + 0.5 + oy) * tile
                if kind == BLOCK and color == theme.SIETCH:
                    # The generator's '42' is drawn as solid sietch rock.
                    pygame.draw.rect(surface, color,
                                     (x * tile, y * tile, tile, tile))
                    continue
                pygame.draw.circle(surface, color, (cx, cy), radius)
                for dx, dy in ((1, 0), (0, 1)):
                    other = tilemap.tile((x + dx, y + dy))
                    if other == FLOOR or not tilemap.in_bounds(
                            (x + dx, y + dy)):
                        continue
                    if (other == BLOCK) != (kind == BLOCK) and size < 0.3:
                        continue
                    if dx:
                        rect = pygame.Rect(0, 0, tile, radius * 2)
                        rect.midleft = (round(cx), round(cy))
                    else:
                        rect = pygame.Rect(0, 0, radius * 2, tile)
                        rect.midtop = (round(cx), round(cy))
                    pygame.draw.rect(surface, color, rect)
    return surface


def draw_hud(surface: pygame.Surface, session: GameSession) -> None:
    """Draw score, lives, level and time above the board."""
    width = surface.get_width()
    pygame.draw.rect(surface, theme.PANEL, (0, 0, width, HUD_HEIGHT))
    pygame.draw.line(surface, theme.SPICE, (0, HUD_HEIGHT - 2),
                     (width, HUD_HEIGHT - 2), 2)
    mid = HUD_HEIGHT // 2
    theme.text(surface, "SPICE", 22, theme.TEXT_DIM, topleft=(24, 8))
    theme.text(surface, f"{session.score:07d}", 40, theme.SPICE_CORE,
               topleft=(24, 26))

    theme.text(surface, "LIVES", 22, theme.TEXT_DIM,
               topleft=(width * 0.27, 8))
    for i in range(min(session.lives, 12)):
        theme.draw_player(surface, (width * 0.27 + 12 + i * 26, mid + 12),
                          10, 0.0, 35)
    if session.lives > 12:
        theme.text(surface, f"+{session.lives - 12}", 24, theme.TEXT,
                   topleft=(width * 0.27 + 12 * 26, mid + 2))

    theme.text(surface, "LEVEL", 22, theme.TEXT_DIM,
               topleft=(width * 0.55, 8))
    theme.text(surface, f"{session.level.number} / {session.level_count}",
               36, theme.TEXT, topleft=(width * 0.55, 28))

    seconds = math.ceil(session.time_left)
    low = seconds <= 10 and int(session.clock * 4) % 2 == 0
    theme.text(surface, "TIME", 22, theme.TEXT_DIM,
               topleft=(width * 0.75, 8))
    theme.text(surface, f"{seconds // 60}:{seconds % 60:02d}", 40,
               theme.TEXT_WARN if low else theme.TEXT,
               topleft=(width * 0.75, 26))

    footer_y = surface.get_height() - FOOTER_HEIGHT // 2
    cheats = session.cheats
    if cheats.enabled:
        flags = [name for name, on in (
            ("INVINCIBLE", cheats.invincible), ("FROZEN", cheats.freeze),
            ("FAST", cheats.fast)) if on]
        hint = ("CHEATS ON  [I] invincible  [F] freeze  [V] speed  "
                "[L] +life  [N] skip level  [T] time")
        if flags:
            hint += "   >> " + " ".join(flags)
        theme.text(surface, hint, 20, theme.TEXT_WARN,
                   center=(width / 2, footer_y))
    else:
        theme.text(surface, "Arrows / WASD to move   P or Esc to pause   "
                   "F1 cheat mode", 20, theme.TEXT_DIM,
                   center=(width / 2, footer_y))
