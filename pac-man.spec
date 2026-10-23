# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec of Pac-Man of Arrakis.  Build with `make package`
# (or `pyinstaller --noconfirm --clean pac-man.spec`).
#
# Output: dist/pac-man/ (the game folder) and dist/pac-man-<os>.zip, ready
# to upload to itch.io (e.g. `butler push dist/pac-man-linux.zip
# <user>/pac-man-of-arrakis:linux`).  PyInstaller does not cross-compile:
# build on each OS you want to ship.
import shutil
import sys
from pathlib import Path

ROOT = Path(SPECPATH)
NAME = "pac-man"
PLATFORM = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")

a = Analysis(
    [str(ROOT / "pac-man.py")],
    pathex=[str(ROOT)],
    hiddenimports=["mazegenerator"],
    excludes=["tkinter", "pytest", "mypy", "flake8"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME)

# Files players need next to the executable.
game_dir = Path(DISTPATH) / NAME
for name in ("config.json",):
    shutil.copy2(ROOT / name, game_dir / name)
for name in ("HOW_TO_PLAY.txt", ".itch.toml", "play.sh", "play.bat"):
    shutil.copy2(ROOT / "packaging" / name, game_dir / name)
archive = shutil.make_archive(str(Path(DISTPATH) / f"{NAME}-{PLATFORM}"),
                              "zip", root_dir=game_dir)
print(f"Packaged game: {archive}")
