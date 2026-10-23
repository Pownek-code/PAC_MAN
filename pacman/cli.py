"""Command line entry point: ``python3 pac-man.py config.json``."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from pacman.config import ConfigError, load_config

USAGE = "usage: python3 pac-man.py <config.json>"


def main(argv: list[str]) -> int:
    """Validate the arguments, load the config and run the game.

    Args:
        argv: The full ``sys.argv``.

    Returns:
        The process exit status.
    """
    logging.basicConfig(level=logging.WARNING,
                        format="pac-man: %(levelname)s: %(message)s")
    if len(argv) != 2:
        print(f"pac-man: error: expected exactly one argument, the "
              f"configuration file\n{USAGE}", file=sys.stderr)
        return 2
    try:
        config = load_config(Path(argv[1]))
    except ConfigError as exc:
        print(f"pac-man: error: {exc}", file=sys.stderr)
        return 1

    # Hide pygame's greeting; import it only once the config is fine.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame
        from pacman.app import App
    except ImportError as exc:
        print(f"pac-man: error: missing dependency ({exc.name}); "
              f"run 'make install'", file=sys.stderr)
        return 1
    try:
        App(config).run()
    except KeyboardInterrupt:
        return 130
    except pygame.error as exc:
        print(f"pac-man: error: graphics failure: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if os.environ.get("PACMAN_DEBUG"):
            raise
        print(f"pac-man: error: unexpected failure: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0
