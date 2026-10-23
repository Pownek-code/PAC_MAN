"""The Arrakis look: palette, fonts and the hand-drawn sprites.

Everything is drawn procedurally with pygame primitives, so the game
ships without any image or font file to license or lose.
"""

from __future__ import annotations

import math
import random

import pygame

Color = tuple[int, int, int]

# Night over the deep desert.
SKY_TOP: Color = (14, 9, 26)
SKY_BOTTOM: Color = (92, 42, 30)
MOON: Color = (236, 226, 204)
MOON_SMALL: Color = (200, 186, 170)
DUNE_FAR: Color = (120, 62, 36)
DUNE_MID: Color = (158, 92, 46)
DUNE_NEAR: Color = (196, 128, 62)

# The maze.
GAME_BACKGROUND: Color = (18, 11, 14)
FLOOR: Color = (34, 21, 17)
FLOOR_RIPPLE: Color = (48, 30, 23)
ROCK_SHADOW: Color = (74, 40, 22)
SAND: Color = (201, 141, 70)
SAND_CREST: Color = (238, 192, 120)
SIETCH: Color = (122, 58, 34)
SIETCH_CREST: Color = (255, 130, 50)

# Spice and characters.
SPICE: Color = (255, 138, 38)
SPICE_CORE: Color = (255, 214, 150)
MELANGE: Color = (255, 92, 24)
FREMEN_BLUE: Color = (70, 150, 255)
PLAYER_BODY: Color = (255, 208, 92)
PLAYER_OUTLINE: Color = (120, 70, 20)
FRIGHTENED: Color = (38, 84, 214)
FRIGHTENED_FLASH: Color = (230, 232, 255)
GHOST_COLORS: dict[str, Color] = {
    "Baron": (206, 38, 38),
    "Rabban": (224, 92, 172),
    "Feyd": (96, 204, 226),
    "Sardaukar": (150, 176, 64),
}

# Text.
TEXT: Color = (246, 224, 182)
TEXT_DIM: Color = (176, 140, 100)
TEXT_WARN: Color = (255, 170, 90)
PANEL: Color = (24, 14, 12)

_FONTS: dict[int, pygame.font.Font] = {}


def font(size: int) -> pygame.font.Font:
    """Return the (cached) default font at ``size`` pixels."""
    if size not in _FONTS:
        _FONTS[size] = pygame.font.Font(None, size)
    return _FONTS[size]


def text(surface: pygame.Surface, message: str, size: int, color: Color,
         center: tuple[float, float] | None = None,
         topleft: tuple[float, float] | None = None,
         shadow: bool = True) -> pygame.Rect:
    """Draw ``message`` and return the rectangle it covers.

    Args:
        surface: Where to draw.
        message: Text to draw.
        size: Font size in pixels.
        color: Text color.
        center: Position of the text centre (default: surface centre).
        topleft: Position of the top-left corner, instead of ``center``.
        shadow: Draw a dark drop shadow for readability.
    """
    rendered = font(size).render(message, True, color)
    rect = rendered.get_rect()
    if topleft is not None:
        rect.topleft = (round(topleft[0]), round(topleft[1]))
    else:
        cx, cy = center if center is not None else surface.get_rect().center
        rect.center = (round(cx), round(cy))
    if shadow:
        offset = max(1, size // 18)
        dark = font(size).render(message, True, (0, 0, 0))
        surface.blit(dark, rect.move(offset, offset))
    surface.blit(rendered, rect)
    return rect


def lerp_color(a: Color, b: Color, t: float) -> Color:
    """Blend two colors, ``t`` = 0 giving ``a`` and 1 giving ``b``."""
    t = max(0.0, min(1.0, t))
    return (round(a[0] + (b[0] - a[0]) * t),
            round(a[1] + (b[1] - a[1]) * t),
            round(a[2] + (b[2] - a[2]) * t))


def glow(radius: int, color: Color, strength: int = 90) -> pygame.Surface:
    """Return a soft round halo of ``radius`` pixels."""
    radius = max(1, radius)
    halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for step in range(radius, 0, -1):
        alpha = round(strength * (1 - step / radius) ** 2)
        pygame.draw.circle(halo, (*color, alpha), (radius, radius), step)
    return halo


def draw_player(surface: pygame.Surface, center: tuple[float, float],
                radius: float, angle: float, mouth: float) -> None:
    """Draw Muad'Dib, a golden chomper with blue-within-blue eyes.

    Args:
        surface: Where to draw.
        center: Centre in pixels.
        radius: Body radius in pixels.
        angle: Facing angle in degrees (0 = right, 90 = up).
        mouth: Half-opening of the mouth in degrees (0..180).
    """
    if radius < 1:
        return
    cx, cy = center
    if mouth >= 179:
        return
    points = [(cx, cy)]
    steps = 28
    start, end = mouth, 360 - mouth
    for i in range(steps + 1):
        a = math.radians(angle + start + (end - start) * i / steps)
        points.append((cx + math.cos(a) * radius, cy - math.sin(a) * radius))
    pygame.draw.polygon(surface, PLAYER_OUTLINE,
                        [(x + 1, y + 1) for x, y in points])
    pygame.draw.polygon(surface, PLAYER_BODY, points)
    if mouth < 120:
        # The eye sits above the mouth, on the "forehead" side.
        eye_angle = math.radians(angle + (60 if -90 < angle <= 90 else -60))
        if angle in (90.0, 270.0):
            eye_angle = math.radians(angle + 50)
        ex = cx + math.cos(eye_angle) * radius * 0.5
        ey = cy - math.sin(eye_angle) * radius * 0.5
        pygame.draw.circle(surface, (16, 24, 60), (ex, ey),
                           max(1.5, radius * 0.2))
        pygame.draw.circle(surface, FREMEN_BLUE, (ex, ey),
                           max(1.0, radius * 0.13))


def draw_ghost(surface: pygame.Surface, center: tuple[float, float],
               radius: float, color: Color, look: tuple[int, int],
               clock: float, frightened: bool = False) -> None:
    """Draw a Harkonnen ghost.

    Args:
        surface: Where to draw.
        center: Centre in pixels.
        radius: Head radius in pixels.
        color: Body color.
        look: Direction the eyes look at, as a (dx, dy) step.
        clock: Animation time in seconds (makes the robe ripple).
        frightened: Draw the scared face instead of the hunting eyes.
    """
    if radius < 1:
        return
    cx, cy = center
    top = cy - radius * 0.15
    bottom = cy + radius * 0.95
    left, right = cx - radius, cx + radius
    body = [(left, top)]
    waves = 4
    phase = (clock * 8) % 2
    for i in range(waves * 2 + 1):
        x = left + (right - left) * i / (waves * 2)
        lift = radius * (0.28 if (i + int(phase)) % 2 else 0.0)
        body.append((x, bottom - lift))
    body.append((right, top))
    pygame.draw.circle(surface, color, (cx, top), radius)
    pygame.draw.polygon(surface, color, body)
    # A darker band, the Harkonnen sash.
    sash = lerp_color(color, (0, 0, 0), 0.45)
    pygame.draw.line(surface, sash, (left + 1, cy + radius * 0.3),
                     (right - 1, cy + radius * 0.3), max(1, round(radius / 6)))

    eye_y = top - radius * 0.05
    if frightened:
        for side in (-1, 1):
            pygame.draw.circle(surface, SPICE_CORE,
                               (cx + side * radius * 0.38, eye_y),
                               max(1.0, radius * 0.16))
        mouth = []
        for i in range(7):
            x = cx - radius * 0.6 + radius * 1.2 * i / 6
            y = cy + radius * (0.42 if i % 2 else 0.58)
            mouth.append((x, y))
        pygame.draw.lines(surface, SPICE_CORE, False, mouth,
                          max(1, round(radius / 8)))
        return
    lx, ly = look
    for side in (-1, 1):
        ex = cx + side * radius * 0.38
        pygame.draw.circle(surface, (250, 246, 236), (ex, eye_y),
                           max(1.5, radius * 0.3))
        pupil = (ex + lx * radius * 0.13, eye_y + ly * radius * 0.13)
        pygame.draw.circle(surface, (20, 10, 12), pupil,
                           max(1.0, radius * 0.15))


def draw_worm_sign(surface: pygame.Surface, center: tuple[float, float],
                   radius: float, clock: float) -> None:
    """Draw sand ripples where an eaten ghost was swallowed by the desert."""
    ring = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    mid = radius * 2
    for k in range(3):
        t = (clock * 0.8 + k / 3) % 1.0
        alpha = round(160 * (1 - t))
        pygame.draw.circle(ring, (*SAND_CREST, alpha), (mid, mid),
                           max(1.0, radius * (0.3 + 1.6 * t)),
                           max(1, round(radius / 6)))
    surface.blit(ring, (center[0] - mid, center[1] - mid))


def draw_backdrop(size: tuple[int, int], seed: int = 10191) -> pygame.Surface:
    """Paint the desert night used behind every menu.

    Args:
        size: Width and height in pixels.
        seed: Seed of the star field (10191: the year of Dune).
    """
    width, height = size
    sky = pygame.Surface(size)
    for y in range(height):
        sky.fill(lerp_color(SKY_TOP, SKY_BOTTOM, (y / height) ** 1.6),
                 (0, y, width, 1))
    rng = random.Random(seed)
    for _ in range(width * height // 3000):
        x, y = rng.randrange(width), rng.randrange(int(height * 0.6))
        shade = rng.randint(120, 255)
        sky.set_at((x, y), (shade, shade, round(shade * 0.9)))
    moon = (round(width * 0.78), round(height * 0.2))
    sky.blit(glow(round(height * 0.16), MOON, 60),
             (moon[0] - round(height * 0.16), moon[1] - round(height * 0.16)))
    pygame.draw.circle(sky, MOON, moon, round(height * 0.07))
    pygame.draw.circle(sky, MOON_SMALL,
                       (round(width * 0.68), round(height * 0.13)),
                       round(height * 0.025))
    for color, base, amp, freq, shift in (
            (DUNE_FAR, 0.66, 0.05, 2.3, 0.4),
            (DUNE_MID, 0.76, 0.06, 1.7, 1.9),
            (DUNE_NEAR, 0.88, 0.05, 1.2, 3.1)):
        points: list[tuple[float, float]] = [(0, height)]
        for x in range(0, width + 8, 8):
            u = x / width
            ridge = height * (base - amp * (
                math.sin(u * math.tau * freq + shift)
                + 0.4 * math.sin(u * 17 + shift)))
            points.append((x, ridge))
        points.append((width, height))
        pygame.draw.polygon(sky, color, points)
    return sky
