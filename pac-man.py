"""Launch Pac-Man of Arrakis: ``python3 pac-man.py config.json``."""

import sys

from pacman.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
