"""The screens of the game and the transitions between them.

Main menu -> game -> victory / game over -> name entry -> main menu.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from pacman import theme
from pacman.entities import Direction
from pacman.game import GameSession, Phase
from pacman.highscores import MAX_NAME_LENGTH, clean_name, is_valid_name_char
from pacman.maze import MazeError
from pacman.render import BoardRenderer, draw_hud

if TYPE_CHECKING:
    from pacman.app import App

DIRECTION_KEYS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def is_back_event(event: pygame.event.Event) -> bool:
    """Return True for Enter, Space, Esc or a left click."""
    if event.type == pygame.KEYDOWN:
        return event.key in CONFIRM_KEYS or event.key == pygame.K_ESCAPE
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1


class Scene:
    """Base class of every screen."""

    def __init__(self, app: App) -> None:
        """Attach the scene to the application."""
        self.app = app

    def handle(self, event: pygame.event.Event) -> None:
        """React to one input event."""

    def update(self, dt: float) -> None:
        """Advance animations by ``dt`` seconds."""

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""


class Menu:
    """A vertical list of choices driven by the keyboard or the mouse."""

    def __init__(self, items: list[tuple[str, Callable[[], None]]]) -> None:
        """Create a menu of ``(label, action)`` pairs."""
        self.items = items
        self.selected = 0
        self.rects: list[pygame.Rect] = []

    def item_at(self, pos: tuple[int, int]) -> int | None:
        """Return the index of the item under ``pos``, if any."""
        for i, rect in enumerate(self.rects):
            if rect.collidepoint(pos):
                return i
        return None

    def handle(self, event: pygame.event.Event) -> None:
        """Move the selection or run the selected action."""
        if event.type == pygame.MOUSEMOTION:
            hovered = self.item_at(event.pos)
            if hovered is not None:
                self.selected = hovered
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.item_at(event.pos)
            if clicked is not None:
                self.selected = clicked
                self.items[clicked][1]()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.items)
        elif event.key in CONFIRM_KEYS:
            self.items[self.selected][1]()

    def draw(self, surface: pygame.Surface, top: float, clock: float,
             size: int = 46) -> None:
        """Draw the menu, centred horizontally, starting at ``top``."""
        cx = surface.get_width() / 2
        self.rects = []
        for i, (label, _) in enumerate(self.items):
            y = top + i * size * 1.25
            chosen = i == self.selected
            color = theme.SPICE_CORE if chosen else theme.TEXT_DIM
            rect = theme.text(surface, label, size, color, center=(cx, y))
            self.rects.append(rect.inflate(80, size * 0.25))
            if chosen:
                pulse = 1 + 0.15 * abs(math.sin(clock * 4))
                for side in (-1, 1):
                    x = rect.left - 28 if side < 0 else rect.right + 28
                    pygame.draw.circle(surface, theme.MELANGE, (x, y),
                                       7 * pulse)
                    pygame.draw.circle(surface, theme.SPICE_CORE, (x, y), 3)


class MainMenuScene(Scene):
    """Title screen with the main menu and a chase across the dunes."""

    def __init__(self, app: App, notice: str = "") -> None:
        """Create the main menu, optionally showing ``notice``."""
        super().__init__(app)
        self.clock = 0.0
        self.notice = notice
        self.menu = Menu([
            ("Start Game", self._start),
            ("Highscores", lambda: app.switch(HighscoreScene(app))),
            ("Instructions", lambda: app.switch(InstructionsScene(app))),
            ("Exit", app.quit),
        ])

    def _start(self) -> None:
        """Begin a new game."""
        self.app.switch(GameScene.start(self.app))

    def handle(self, event: pygame.event.Event) -> None:
        """Navigate the menu; Esc quits."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.quit()
            return
        self.menu.handle(event)

    def update(self, dt: float) -> None:
        """Animate the parade."""
        self.clock += dt

    def draw(self, surface: pygame.Surface) -> None:
        """Draw title, menu, parade and any warnings."""
        surface.blit(self.app.backdrop, (0, 0))
        width, height = surface.get_size()
        theme.text(surface, "PAC-MAN", 150, theme.SPICE,
                   center=(width / 2, height * 0.17))
        theme.text(surface, "OF  ARRAKIS", 48, theme.SAND_CREST,
                   center=(width / 2, height * 0.27))
        theme.text(surface, "\"The spice must flow.\"", 28, theme.TEXT_DIM,
                   center=(width / 2, height * 0.33))
        self.menu.draw(surface, height * 0.44, self.clock)
        draw_parade(surface, self.clock, height * 0.86)
        best = self.app.highscores.entries
        if best:
            theme.text(surface, f"Best: {best[0].name}  {best[0].score}", 26,
                       theme.TEXT, center=(width / 2, height * 0.75))
        notes = []
        if self.notice:
            notes.append(self.notice)
        if self.app.config.warnings:
            count = len(self.app.config.warnings)
            notes.append(f"{count} config warning(s), defaults used - "
                         f"details in the terminal")
        if self.app.highscores.last_error:
            notes.append("Highscore file problem - details in the terminal")
        for i, note in enumerate(notes):
            theme.text(surface, note, 22, theme.TEXT_WARN,
                       topleft=(12, height - 26 - 22 * i))


class HighscoreScene(Scene):
    """The top 10."""

    def handle(self, event: pygame.event.Event) -> None:
        """Enter, Esc or a click goes back."""
        if is_back_event(event):
            self.app.switch(MainMenuScene(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the highscore table."""
        surface.blit(self.app.backdrop, (0, 0))
        width, height = surface.get_size()
        theme.text(surface, "HALL OF THE FREMEN", 72, theme.SPICE,
                   center=(width / 2, height * 0.12))
        entries = self.app.highscores.entries
        if not entries:
            theme.text(surface, "No spice harvested yet. Be the first!", 34,
                       theme.TEXT, center=(width / 2, height * 0.4))
        for i, entry in enumerate(entries):
            y = height * 0.24 + i * 42
            color = theme.SPICE_CORE if i == 0 else theme.TEXT
            theme.text(surface, f"{i + 1:2d}.", 36, theme.TEXT_DIM,
                       topleft=(width * 0.3, y))
            theme.text(surface, entry.name, 36, color,
                       topleft=(width * 0.37, y))
            score = theme.font(36).render(str(entry.score), True, color)
            surface.blit(score, score.get_rect(topright=(width * 0.7, y)))
        theme.text(surface, "Press Enter, Esc or click to return", 26,
                   theme.TEXT_DIM, center=(width / 2, height * 0.93))


INSTRUCTIONS = (
    ("GOAL", "Harvest every grain of spice in the maze to clear the level."),
    ("", "Clear all the levels before your lives or the time run out."),
    ("MOVE", "Arrow keys or W A S D."),
    ("PAUSE", "P or Esc, then Resume or Main Menu (keys or mouse)."),
    ("SPICE", "Small grain: pacgum.  Glowing orb in a corner: melange."),
    ("MELANGE", "Eat it and the Harkonnen turn blue: eat them for points."),
    ("", "An eaten Harkonnen is swallowed by the sand and comes back"),
    ("", "to its corner a few seconds later."),
    ("TIME", "When the level timer runs out you lose a life and the"),
    ("", "timer starts again."),
    ("CHEATS", "F1 toggles cheat mode, then: I invincible, F freeze,"),
    ("", "V speed, L extra life, N skip level, T refill time."),
)


class InstructionsScene(Scene):
    """Controls and rules."""

    def handle(self, event: pygame.event.Event) -> None:
        """Enter, Esc or a click goes back."""
        if is_back_event(event):
            self.app.switch(MainMenuScene(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the instruction text."""
        surface.blit(self.app.backdrop, (0, 0))
        width, height = surface.get_size()
        theme.text(surface, "THE WAY OF THE DESERT", 64, theme.SPICE,
                   center=(width / 2, height * 0.1))
        panel = pygame.Surface((width * 0.8, height * 0.68), pygame.SRCALPHA)
        panel.fill((*theme.PANEL, 200))
        surface.blit(panel, (width * 0.1, height * 0.17))
        for i, (label, line) in enumerate(INSTRUCTIONS):
            y = height * 0.2 + i * height * 0.052
            theme.text(surface, label, 28, theme.SPICE_CORE,
                       topleft=(width * 0.13, y))
            theme.text(surface, line, 28, theme.TEXT,
                       topleft=(width * 0.29, y))
        theme.text(surface, "Press Enter, Esc or click to return", 26,
                   theme.TEXT_DIM, center=(width / 2, height * 0.93))


class GameScene(Scene):
    """A game in progress, with its pause menu."""

    def __init__(self, app: App, session: GameSession) -> None:
        """Wrap an already started ``session``."""
        super().__init__(app)
        self.session = session
        self.board = BoardRenderer(session.level, app.size)
        self.paused = False
        self.pause_menu = Menu([
            ("Resume", self._resume),
            ("Main Menu", lambda: app.switch(MainMenuScene(app))),
        ])

    @staticmethod
    def start(app: App) -> Scene:
        """Start a new game, or return an error screen if it cannot."""
        try:
            return GameScene(app, GameSession(app.config))
        except MazeError as exc:
            return ErrorScene(app, "The desert refused to form a maze.",
                              str(exc))

    def _resume(self) -> None:
        """Leave the pause menu."""
        self.paused = False

    def handle(self, event: pygame.event.Event) -> None:
        """Steering, pause and cheat keys."""
        if event.type == pygame.WINDOWFOCUSLOST:
            self.paused = True
            return
        if self.paused:
            if (event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_ESCAPE, pygame.K_p)):
                self.paused = False
            else:
                self.pause_menu.handle(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        session = self.session
        cheat_keys: dict[int, Callable[[], None]] = {
            pygame.K_F1: session.toggle_cheat_mode,
            pygame.K_i: session.cheat_invincible,
            pygame.K_f: session.cheat_freeze,
            pygame.K_v: session.cheat_fast,
            pygame.K_l: session.cheat_extra_life,
            pygame.K_n: session.cheat_skip_level,
            pygame.K_t: session.cheat_refill_time,
        }
        if event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.paused = True
            self.pause_menu.selected = 0
        elif event.key in DIRECTION_KEYS:
            session.steer(DIRECTION_KEYS[event.key])
        elif event.key in cheat_keys:
            cheat_keys[event.key]()

    def update(self, dt: float) -> None:
        """Run the game unless paused."""
        if self.paused:
            return
        try:
            self.session.update(dt)
        except MazeError as exc:
            self.app.switch(ErrorScene(
                self.app, "The desert refused to form the next maze.",
                str(exc)))
            return
        if self.session.level is not self.board.level:
            self.board = BoardRenderer(self.session.level, self.app.size)
        if self.session.finished:
            self.app.switch(EndScene(self.app, self.session))

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the board, the HUD and the pause menu."""
        surface.fill(theme.GAME_BACKGROUND)
        self.board.draw(surface, self.session)
        draw_hud(surface, self.session)
        if self.paused:
            shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            shade.fill((10, 6, 14, 190))
            surface.blit(shade, (0, 0))
            width, height = surface.get_size()
            theme.text(surface, "PAUSED", 96, theme.SPICE,
                       center=(width / 2, height * 0.35))
            self.pause_menu.draw(surface, height * 0.5, self.session.clock)


class EndScene(Scene):
    """Victory or game over: final score and name entry."""

    def __init__(self, app: App, session: GameSession) -> None:
        """Show the result of ``session``."""
        super().__init__(app)
        self.victory = session.phase is Phase.VICTORY
        self.score = session.score
        self.level_reached = session.level.number
        self.name = ""
        self.message = ""
        self.clock = 0.0
        pygame.key.start_text_input()

    def handle(self, event: pygame.event.Event) -> None:
        """Type the name; Enter saves, Esc skips."""
        if event.type == pygame.TEXTINPUT:
            for char in event.text:
                if (is_valid_name_char(char)
                        and len(self.name) < MAX_NAME_LENGTH):
                    self.name += char
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit()
        elif event.key == pygame.K_ESCAPE:
            self._leave("Score not saved.")

    def _submit(self) -> None:
        """Save the score under the typed name and go back to the menu."""
        name = clean_name(self.name)
        if name is None:
            self.message = "Type a name first (letters, digits, spaces)."
            return
        table = self.app.highscores
        rank = table.add(name, self.score)
        if rank is None:
            self._leave(f"{self.score} did not reach the top 10.")
        elif table.save():
            self._leave(f"{name} is now #{rank + 1} in the hall of fame.")
        else:
            self._leave("Could not write the highscore file.")

    def _leave(self, notice: str) -> None:
        """Return to the main menu."""
        pygame.key.stop_text_input()
        self.app.switch(MainMenuScene(self.app, notice))

    def update(self, dt: float) -> None:
        """Blink the cursor."""
        self.clock += dt

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the result and the name prompt."""
        surface.blit(self.app.backdrop, (0, 0))
        width, height = surface.get_size()
        if self.victory:
            title, color = "THE SPICE FLOWS!", theme.SPICE
            line = "You harvested Arrakis. Lisan al-Gaib!"
        else:
            title, color = "GAME OVER", theme.GHOST_COLORS["Baron"]
            line = (f"The Harkonnen got you on level "
                    f"{self.level_reached}.")
        theme.text(surface, title, 110, color,
                   center=(width / 2, height * 0.18))
        theme.text(surface, line, 34, theme.TEXT,
                   center=(width / 2, height * 0.3))
        theme.text(surface, "FINAL SCORE", 30, theme.TEXT_DIM,
                   center=(width / 2, height * 0.4))
        theme.text(surface, str(self.score), 84, theme.SPICE_CORE,
                   center=(width / 2, height * 0.48))
        theme.text(surface, "Enter your name for the highscores:", 32,
                   theme.TEXT, center=(width / 2, height * 0.6))
        box = pygame.Rect(0, 0, 420, 64)
        box.center = (round(width / 2), round(height * 0.69))
        pygame.draw.rect(surface, theme.PANEL, box, border_radius=8)
        pygame.draw.rect(surface, theme.SPICE, box, 2, border_radius=8)
        cursor = "_" if int(self.clock * 2) % 2 == 0 else " "
        theme.text(surface, self.name + cursor, 48, theme.SPICE_CORE,
                   center=box.center)
        theme.text(surface, f"max {MAX_NAME_LENGTH} letters, digits or "
                   f"spaces  -  Enter to save, Esc to skip", 24,
                   theme.TEXT_DIM, center=(width / 2, height * 0.77))
        if self.message:
            theme.text(surface, self.message, 26, theme.TEXT_WARN,
                       center=(width / 2, height * 0.82))


class ErrorScene(Scene):
    """A recoverable error, shown instead of crashing."""

    def __init__(self, app: App, title: str, detail: str) -> None:
        """Show ``title`` and ``detail``."""
        super().__init__(app)
        self.title = title
        self.detail = detail

    def handle(self, event: pygame.event.Event) -> None:
        """Any key or click returns to the main menu."""
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.app.switch(MainMenuScene(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the error message."""
        surface.blit(self.app.backdrop, (0, 0))
        width, height = surface.get_size()
        theme.text(surface, self.title, 48, theme.TEXT_WARN,
                   center=(width / 2, height * 0.35))
        theme.text(surface, self.detail, 28, theme.TEXT,
                   center=(width / 2, height * 0.45))
        theme.text(surface, "Press any key or click to return to the menu",
                   26, theme.TEXT_DIM, center=(width / 2, height * 0.6))


def draw_parade(surface: pygame.Surface, clock: float, y: float) -> None:
    """Draw Muad'Dib fleeing four Harkonnen along the dunes."""
    width = surface.get_width()
    span = width + 400
    lead = (clock * 180) % span - 120
    theme.draw_player(surface, (lead, y), 22, 0.0,
                      6 + 40 * abs(math.sin(clock * 12)))
    for i, name in enumerate(theme.GHOST_COLORS):
        x = lead - 80 - i * 56
        theme.draw_ghost(surface, (x, y), 22, theme.GHOST_COLORS[name],
                         (1, 0), clock)
