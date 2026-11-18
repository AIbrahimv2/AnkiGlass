# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""Glass behind the windows of AnkiGlass's sibling add-ons: Stepwise's,
Skim's and Exam Timeline's, and the shared kit's Settings, What's new and
About window (AnkiGlass's own Settings among them).

They ask for it through the kit: kit.glass(window), called while the window
is being made, lands in glass_window() here (AnkiGlass registers it with the
kit). It's the main window's glass, one per window: the window is made
see-through (a Qt surface with alpha, which only a window that hasn't been
shown yet can get) and painted with the tint, and a borderless child window
holding the glass view sits right behind it and follows it. Its page is
marked with the kit's glass class as it loads (page_head(), from the CSS
hook in __init__.py), and the kit's theme turns the page's background
see-through and its panels to glass. A page that draws cards in frames of
its own (Skim) has each card made see-through the way the reviewer's is
(window.kitGlassCard, below), while "Glass behind the card" is on.

The glass is taken away while the window is hidden, and while it's full
screen: there, nothing is behind the window to show, and macOS would put the
glass in front of it. "Glass on add-on windows" in Settings (glass_windows
in config.json) turns all of it off.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import os
import sys
import traceback

from aqt.qt import QColor, QEvent, QObject, Qt, QTimer, QWidget, sip

# __init__.py imports this module after defining these.
from . import (
    CONFIG, GLASS_CONTENT_CSS, NSWindowBelow, NSWindowStyleMaskFullScreen, UNCOVER_FN, USER_DIR, log,
    make_glass_window, tint_nscolor,
)
from .kit.family import GLASS_CLASS

# Set on a window that has glass, so its page gets the kit's glass class.
PROPERTY = "anki_glass_window"
# Left behind if making a window's glass ever took Anki down. From then on
# add-on windows keep their own background, as the main window does after
# its own marker (__init__.py's MARKER_PATH).
MARKER_PATH = os.path.join(USER_DIR, "windows.marker")
# After full screen, the glass comes back once macOS's animation is over.
AFTER_FULL_SCREEN_MS = 800
# window.kitGlassCard(frameWindow), for a page that draws cards in frames of
# its own (Skim): call it once a card is in a frame. It makes the card
# see-through as the reviewer's is: the CSS that clears the card's canvas,
# then __init__.py's UNCOVER_FN, again a moment later for wrappers a note
# type's script adds. Only while "Glass behind the card" is on.
CARD_JS = """
window.kitGlassCard = function (w) {
  try {
    var d = w.document;
    if (!d.getElementById("kit-glass-card")) {
      var s = d.createElement("style");
      s.id = "kit-glass-card";
      s.textContent = %(css)s;
      (d.head || d.documentElement).appendChild(s);
    }
    var uncover = %(uncover)s;
    uncover(w);
    w.setTimeout(function () { try { uncover(w); } catch (e) {} }, 250);
  } catch (e) {}
};
"""

_enabled = False
_live: list = []  # each window's _Glass, for theme changes
_spare: list = []  # glass windows whose window has gone, for the next one


def setup(enabled: bool) -> None:
    """At load, with the glass_windows setting."""
    global _enabled
    _enabled = bool(enabled) and sys.platform == "darwin"
    if _enabled and os.path.exists(MARKER_PATH):
        log("window glass off: leftover marker -> a window's glass did not finish last time")
        _enabled = False
    if _enabled:
        from aqt import gui_hooks

        gui_hooks.theme_did_change.append(_on_theme_change)


def glass_window(window) -> bool:
    """Glass behind `window`, a top-level window of one of the add-ons, which
    kit.glass() hands over while the window is being made. False, with the
    window left as it is, when the setting is off, the window has already
    been shown (too late for a see-through surface) or something fails."""
    if not _enabled:
        return False
    try:
        if not window.isWindow() or window.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
            log(f"window glass: {_name(window)} was already made, too late for glass")
            return False
        window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        window.setProperty(PROPERTY, True)
        _live.append(_Glass(window))
        clear_pages(window)
        log(f"window glass: {_name(window)} asked for it")
        return True
    except Exception:
        log("window glass FAILED:\n" + traceback.format_exc())
        return False


def has_glass(context) -> bool:
    """A page is loading in a window with glass: `context` (what Anki's
    webview_will_set_content hook gives) is the window or a widget in it."""
    if not _enabled or not isinstance(context, QWidget):
        return False
    try:
        return bool(context.window().property(PROPERTY))
    except Exception:
        return False


def page_head() -> str:
    """What a page in a window with glass gets in its <head>: the kit's
    glass class on its root (the kit's theme draws the glass look), no
    background of its own whatever its stylesheet says, and, while the card
    has glass, window.kitGlassCard (CARD_JS).

    The page stays fully see-through, so Anki's web view draws no
    backdrop-filter on it: the kit's theme makes what sits over the page's
    content hide it without blur (kit/web/glass.css)."""
    script = f'document.documentElement.classList.add("{GLASS_CLASS}");'
    if CONFIG["content_glass"]:
        css = "html{background:transparent !important}\n" + GLASS_CONTENT_CSS
        script += CARD_JS % {"css": json.dumps(css), "uncover": UNCOVER_FN}
    return f"<script>{script}</script><style>html,body{{background:transparent !important}}</style>"


def clear_pages(window) -> None:
    """No background behind the pages of the window's web views, so the glass
    shows through them. Anki's web view paints one again when the theme
    changes, so this runs again then."""
    from aqt.webview import AnkiWebView

    for web in window.findChildren(AnkiWebView):
        try:
            web.page().setBackgroundColor(QColor(0, 0, 0, 0))
            web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        except Exception as e:
            log(f"window glass: page of {_name(window)} FAILED ({e})")


def _name(window) -> str:
    return type(window).__name__


def _ob():
    """The ObjC bridge (on sys.path from __init__.py's _install, on a Mac)."""
    import objc_bridge as ob

    return ob


class _Glass(QObject):
    """One window's glass: a child window right behind it while it shows,
    taken away while it's hidden or full screen."""

    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.name = _name(window)
        # The NSWindows: Anki's (`main`) and the glass behind it.
        self.main = None
        self.glass = None
        self.attached = False
        self.full_screen = False  # the glass went for full screen
        self.waiting = False  # for the full-screen animation to end
        self.failed = False
        window.installEventFilter(self)
        window.destroyed.connect(lambda *_: self._window_gone())

    # --- events --------------------------------------------------------------

    def eventFilter(self, obj, ev) -> bool:
        try:
            if obj is self.window and not self.failed:
                kind = ev.type()
                if kind == QEvent.Type.Hide:
                    self.detach()
                elif kind in (QEvent.Type.Show, QEvent.Type.Move, QEvent.Type.Resize,
                              QEvent.Type.WindowStateChange, QEvent.Type.WindowActivate):
                    # A Show comes before the window is on screen: attach once it is.
                    QTimer.singleShot(0, self.follow)
        except Exception:
            log(f"window glass: {self.name} event FAILED:\n" + traceback.format_exc())
        return False

    def follow(self) -> None:
        """Glass behind the window, on its frame, while it shows; none while
        it's hidden or full screen."""
        try:
            if self.failed or sip.isdeleted(self) or sip.isdeleted(self.window):
                return
            if not self.window.isVisible():
                self.detach()
                return
            main = self.ns_window()
            if not main:
                return
            if self.is_full_screen(main):
                if not self.full_screen:
                    self.full_screen = True
                    self.detach()
                    self.make_opaque(main)
                    log(f"window glass: {self.name} full screen, glass away")
                return
            if self.full_screen:
                if not self.waiting:
                    self.waiting = True
                    QTimer.singleShot(AFTER_FULL_SCREEN_MS, self._after_full_screen)
                return
            self.attach(main)
        except Exception:
            log(f"window glass: {self.name} FAILED:\n" + traceback.format_exc())
            self.give_up()

    def _after_full_screen(self) -> None:
        self.waiting = False
        if sip.isdeleted(self) or sip.isdeleted(self.window):
            return
        main = self.ns_window() if self.window.isVisible() else None
        if main and not self.is_full_screen(main):
            self.full_screen = False
            self.follow()

    def restyle(self) -> None:
        """The theme changed: the tint for it, and see-through pages again."""
        if self.failed or sip.isdeleted(self.window):
            return
        clear_pages(self.window)
        if self.attached and self.main:
            self.see_through(self.main)

    # --- the native windows --------------------------------------------------

    def ns_window(self):
        """The window's NSWindow, once it has one."""
        ob = _ob()
        view = ctypes.c_void_p(int(self.window.winId()))
        main = ob.msg(view, "window")
        if main != self.main:
            # A new NSWindow (Qt made the window again): the old one has
            # taken its child windows with it.
            self.main = main
            self.attached = False
        return main

    def is_full_screen(self, main) -> bool:
        mask = _ob().msg(main, "styleMask", restype=ctypes.c_ulong)
        return bool(mask & NSWindowStyleMaskFullScreen) or self.window.isFullScreen()

    def attach(self, main) -> None:
        """The glass behind the window on its frame: put there if it isn't
        yet, moved if it is."""
        ob = _ob()
        frame = ob.msg(main, "frame", restype=ob.CGRect)
        if not self.attached:
            with _marker():
                if self.glass is None:
                    self.glass = _spare.pop() if _spare else make_glass_window(ob, frame)[0]
                    if not self.glass:
                        raise RuntimeError("AppKit made no glass window")
                self.see_through(main)
                ob.msg(self.glass, "setFrame:display:", frame, True,
                       restype=None, argtypes=[ob.CGRect, ctypes.c_bool])
                ob.msg(main, "addChildWindow:ordered:", self.glass, NSWindowBelow,
                       restype=None, argtypes=[ctypes.c_void_p, ctypes.c_long])
            self.attached = True
            log(f"window glass: behind {self.name} {frame}")
            return
        ob.msg(self.glass, "setFrame:display:", frame, True,
               restype=None, argtypes=[ob.CGRect, ctypes.c_bool])

    def detach(self) -> None:
        if not (self.attached and self.main and self.glass):
            return
        ob = _ob()
        ob.msg(self.main, "removeChildWindow:", self.glass,
               restype=None, argtypes=[ctypes.c_void_p])
        ob.msg(self.glass, "orderOut:", None, restype=None, argtypes=[ctypes.c_void_p])
        self.attached = False

    def see_through(self, main) -> None:
        """The window shows what's behind it, under one layer of the tint;
        its title bar too, like the main window's."""
        ob = _ob()
        clear = ob.msg(ob.cls("NSColor"), "clearColor")
        ob.msg(main, "setOpaque:", False, restype=None, argtypes=[ctypes.c_bool])
        ob.msg(main, "setBackgroundColor:", tint_nscolor(ob) or clear,
               restype=None, argtypes=[ctypes.c_void_p])
        ob.msg(main, "setTitlebarAppearsTransparent:", True,
               restype=None, argtypes=[ctypes.c_bool])

    def make_opaque(self, main) -> None:
        ob = _ob()
        ob.msg(main, "setOpaque:", True, restype=None, argtypes=[ctypes.c_bool])
        ob.msg(main, "setBackgroundColor:", ob.msg(ob.cls("NSColor"), "windowBackgroundColor"),
               restype=None, argtypes=[ctypes.c_void_p])

    def give_up(self) -> None:
        """Something failed: the window as if it never had glass (opaque, its
        page with its own background), and no more tries."""
        if self.failed:
            return
        self.failed = True
        try:
            self.detach()
            if self.main:
                self.make_opaque(self.main)
            if sip.isdeleted(self.window):
                return
            self.window.setProperty(PROPERTY, False)
            from aqt import colors
            from aqt.theme import theme_manager
            from aqt.webview import AnkiWebView

            for web in self.window.findChildren(AnkiWebView):
                web.page().setBackgroundColor(theme_manager.qcolor(colors.CANVAS))
                web.eval(f'document.documentElement.classList.remove("{GLASS_CLASS}");')
        except Exception:
            log(f"window glass: {self.name} give up FAILED:\n" + traceback.format_exc())

    def _window_gone(self) -> None:
        """The window was deleted. Its glass window was taken off it when it
        hid, and waits for the next window; one still on it (deleted while
        it showed) is only put away, as AppKit may still count it as the
        old window's."""
        if self in _live:
            _live.remove(self)
        glass, self.glass = self.glass, None
        if glass:
            try:
                _ob().msg(glass, "orderOut:", None, restype=None, argtypes=[ctypes.c_void_p])
                if not self.attached:
                    _spare.append(glass)
            except Exception:
                log(f"window glass: {self.name} cleanup FAILED:\n" + traceback.format_exc())


@contextlib.contextmanager
def _marker():
    """Around the AppKit calls that put glass behind a window: if they ever
    take Anki down, the marker stays and window glass is off from then on."""
    try:
        with open(MARKER_PATH, "w") as f:
            f.write("in progress")
    except OSError:
        pass
    try:
        yield
    finally:
        try:
            os.remove(MARKER_PATH)
        except OSError:
            pass


def _on_theme_change() -> None:
    # After the web views have put their own backgrounds back.
    QTimer.singleShot(0, _restyle_all)


def _restyle_all() -> None:
    for g in list(_live):
        try:
            g.restyle()
        except Exception:
            log("window glass: restyle FAILED:\n" + traceback.format_exc())
