"""The pygame window and the main loop driving the current scene."""

from __future__ import annotations

import pygame

from pacman import theme
from pacman.config import GameConfig
from pacman.highscores import HighscoreTable
from pacman.macos import focus_window
from pacman.scenes import MainMenuScene, Scene

MAX_FRAME_TIME = 1 / 30


class App:
    """Owns the window, the highscores and the active scene."""

    def __init__(self, config: GameConfig) -> None:
        """Open the window and show the main menu.

        Raises:
            pygame.error: If no display is available.
        """
        self.config = config
        # Only video and fonts: the game has no sound, and skipping the
        # mixer avoids audio errors on machines without a sound card.
        pygame.display.init()
        pygame.font.init()
        self.size = (config.window_width, config.window_height)
        pygame.display.set_caption("Pac-Man of Arrakis")
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        theme.draw_player(icon, (16, 16), 14, 0.0, 35)
        pygame.display.set_icon(icon)
        self.screen = pygame.display.set_mode(self.size)
        focus_window()
        self.backdrop = theme.draw_backdrop(self.size)
        self.highscores = HighscoreTable(config.highscore_file)
        self.highscores.load()
        self.running = True
        self.scene: Scene = MainMenuScene(self)

    def switch(self, scene: Scene) -> None:
        """Make ``scene`` the active screen."""
        self.scene = scene

    def quit(self) -> None:
        """Stop the main loop at the end of the frame."""
        self.running = False

    def run(self) -> None:
        """Run until the player quits, then close the window."""
        clock = pygame.time.Clock()
        first_frame = True
        try:
            while self.running:
                dt = min(clock.tick(self.config.fps) / 1000, MAX_FRAME_TIME)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    else:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            focus_window()
                        self.scene.handle(event)
                if first_frame:
                    focus_window()
                    first_frame = False
                self.scene.update(dt)
                self.scene.draw(self.screen)
                pygame.display.flip()
        finally:
            pygame.quit()
