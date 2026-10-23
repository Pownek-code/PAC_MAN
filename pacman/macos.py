"""Give the game window keyboard focus on macOS.

When Python is not a framework build (pyenv, uv, conda...), macOS opens
the pygame window but never makes the process the active application:
mouse clicks reach the window while every key press stays in the
terminal.  This module talks to AppKit through the Objective-C runtime
(with ``ctypes`` only, no extra dependency) to turn the process into a
regular foreground application and give its window the keyboard.

Every function is a silent no-op on other systems or if anything fails.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import sys
from typing import Any

LOG = logging.getLogger("pacman.macos")

_REGULAR_POLICY = 0  # NSApplicationActivationPolicyRegular


class _ObjC:
    """Minimal bridge to send Objective-C messages with ``ctypes``."""

    def __init__(self) -> None:
        """Load the Objective-C runtime and AppKit.

        Raises:
            OSError: If a library cannot be loaded.
        """
        objc_path = ctypes.util.find_library("objc")
        appkit_path = ctypes.util.find_library("AppKit")
        if not objc_path or not appkit_path:
            raise OSError("Objective-C runtime or AppKit not found")
        self.lib = ctypes.cdll.LoadLibrary(objc_path)
        ctypes.cdll.LoadLibrary(appkit_path)
        self.lib.objc_getClass.restype = ctypes.c_void_p
        self.lib.objc_getClass.argtypes = [ctypes.c_char_p]
        self.lib.sel_registerName.restype = ctypes.c_void_p
        self.lib.sel_registerName.argtypes = [ctypes.c_char_p]
        address = ctypes.cast(self.lib.objc_msgSend, ctypes.c_void_p).value
        if address is None:
            raise OSError("objc_msgSend not found")
        self.msg_send = address

    def cls(self, name: str) -> Any:
        """Return the Objective-C class called ``name``."""
        return self.lib.objc_getClass(name.encode())

    def selector(self, name: str) -> Any:
        """Return the selector called ``name``."""
        return self.lib.sel_registerName(name.encode())

    def send(self, receiver: Any, selector: str, restype: Any = None,
             argtypes: tuple[Any, ...] = (), *args: Any) -> Any:
        """Send ``selector`` to ``receiver`` with exactly typed arguments.

        The prototype is declared for every call because ``objc_msgSend``
        must not be called as a variadic function on Apple Silicon.
        """
        prototype = ctypes.CFUNCTYPE(restype, ctypes.c_void_p,
                                     ctypes.c_void_p, *argtypes)
        function = prototype(self.msg_send)
        return function(receiver, self.selector(selector), *args)


_BRIDGE: _ObjC | None = None


def focus_window() -> None:
    """Make the game the active macOS application and focus its window."""
    global _BRIDGE
    if sys.platform != "darwin":
        return
    try:
        if _BRIDGE is None:
            _BRIDGE = _ObjC()
        objc = _BRIDGE
        app = objc.send(objc.cls("NSApplication"), "sharedApplication",
                        ctypes.c_void_p)
        if not app:
            return
        objc.send(app, "setActivationPolicy:", ctypes.c_bool,
                  (ctypes.c_long,), _REGULAR_POLICY)
        # macOS 14+ ignores activateIgnoringOtherApps: and wants activate.
        if objc.send(app, "respondsToSelector:", ctypes.c_bool,
                     (ctypes.c_void_p,), objc.selector("activate")):
            objc.send(app, "activate")
        else:
            objc.send(app, "activateIgnoringOtherApps:", None,
                      (ctypes.c_bool,), True)
        windows = objc.send(app, "windows", ctypes.c_void_p)
        window = (objc.send(windows, "firstObject", ctypes.c_void_p)
                  if windows else None)
        if window:
            objc.send(window, "makeKeyAndOrderFront:", None,
                      (ctypes.c_void_p,), None)
    except Exception as exc:  # never let a focus helper crash the game
        LOG.info("could not focus the window on macOS: %s", exc)
