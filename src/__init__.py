# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""AnkiGlass -- native macOS Liquid Glass for Anki.

Gives Anki's main window a real AppKit NSGlassEffectView (macOS 26 "Tahoe"),
falling back to NSVisualEffectView vibrancy on older macOS. The glass lives in a
borderless child window pinned behind a transparent main window, so Qt keeps
ownership of its own view and mouse/hover behaviour is unaffected.

macOS only; on other platforms the add-on loads and does nothing. Toggle at
runtime from Tools -> AnkiGlass. Tint, which screens, and card glass are set in
the add-on's config (Anki -> Tools -> Add-ons -> AnkiGlass -> Config).
"""

from __future__ import annotations

import ctypes
import os
import sys
import traceback

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DIR = os.path.join(ADDON_DIR, "user_files")
try:
    os.makedirs(USER_DIR, exist_ok=True)
except Exception:
    USER_DIR = ADDON_DIR
LOG_PATH = os.path.join(USER_DIR, "anki_glass.log")
MARKER_PATH = os.path.join(USER_DIR, "apply.marker")
DISABLE_PATH = os.path.join(USER_DIR, "disabled")


# --- config ------------------------------------------------------------------

_DEFAULTS = {
    "glass_screens": ["deckBrowser", "overview", "review"],
    "glass_card": True,
    "tint_dark": "rgba(0,0,0,0.28)",
    "tint_light": "rgba(255,255,255,0.35)",
    "debug_log": False,
}


def _load_user_config() -> dict:
    cfg = dict(_DEFAULTS)
    try:
        from aqt import mw

        user = mw.addonManager.getConfig(__name__)
        if isinstance(user, dict):
            cfg.update({k: user[k] for k in _DEFAULTS if k in user})
    except Exception:
        pass
    return cfg


_ucfg = _load_user_config()
DEBUG = bool(_ucfg["debug_log"])

# request_alpha_format and the toolbar redraw are implementation requirements
# (see build_separate_glass_window / on_state_did_change), not user options.
CONFIG = {
    "glass_states": tuple(_ucfg["glass_screens"]),
    "strips": ("toolbarWeb", "bottomWeb"),
    "content_glass": bool(_ucfg["glass_card"]),
    "glass_tint": {"night": _ucfg["tint_dark"], "light": _ucfg["tint_light"]},
    "request_alpha_format": True,
    "redraw_toolbar_on_state_change": True,
}

_state: dict = {}
_orig_bg: dict = {}


def log(msg: str) -> None:
    if not DEBUG:
        return
    try:
        with open(LOG_PATH, "a") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def flush_log() -> None:  # log() writes eagerly; kept so copied helpers can call it
    pass


# --- AppKit constants --------------------------------------------------------

NSViewWidthSizable = 2
NSViewHeightSizable = 16
NSViewBothSizable = NSViewWidthSizable | NSViewHeightSizable
NSWindowAbove = 1
NSWindowBelow = -1
NSBackingStoreBuffered = 2
NSWindowStyleMaskBorderless = 0
NSVisualEffectBlendingModeBehindWindow = 0
NSVisualEffectStateActive = 1
NSVisualEffectMaterialUnderWindowBackground = 21


# --- Qt-side helpers ---------------------------------------------------------

def native_window_created() -> bool:
    from aqt import mw
    from aqt.qt import Qt

    flag = getattr(Qt.WidgetAttribute, "WA_WState_Created", None)
    if flag is not None:
        return bool(mw.testAttribute(flag))
    return mw.windowHandle() is not None


def surface_alpha() -> str:
    """Alpha buffer size of the main window's surface format; 8 means Qt will
    clear translucent regions before painting, anything else means it won't."""
    from aqt import mw

    wh = mw.windowHandle()
    return str(wh.format().alphaBufferSize()) if wh is not None else "n/a"


def request_alpha_format(stage: str) -> None:
    from aqt import mw
    from aqt.qt import QSurfaceFormat

    wh = mw.windowHandle()
    if wh is None:
        log(f"[{stage}] no QWindow yet; cannot request alpha format")
        return
    before = surface_alpha()
    fmt = QSurfaceFormat(wh.format())
    fmt.setAlphaBufferSize(8)
    wh.setFormat(fmt)
    log(f"[{stage}] requested alpha format: {before} -> {surface_alpha()}")


def in_glass_state() -> bool:
    from aqt import mw

    return getattr(mw, "state", None) in CONFIG["glass_states"]


def strip_widgets():
    from aqt import mw

    return [(n, w) for n in CONFIG["strips"] if (w := getattr(mw, n, None)) is not None]


def glass_widgets():
    """Strips plus, when enabled, the card area (mw.web)."""
    from aqt import mw

    out = strip_widgets()
    if CONFIG["content_glass"] and getattr(mw, "web", None) is not None:
        out.append(("web", mw.web))
    return out


def apply_window_qt_attrs() -> None:
    """Idempotent. Keeps Qt from painting an opaque window background over the
    strips. (Cannot fix the surface format once the window exists.)"""
    from aqt import mw
    from aqt.qt import Qt

    mw.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    cw = mw.centralWidget()
    if cw is not None:
        cw.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        cw.setAutoFillBackground(False)


def body_background_js(on: bool) -> str:
    if on:
        return (
            "document.documentElement.style.setProperty('background','transparent','important');"
            "document.body&&document.body.style.setProperty('background','transparent','important');"
        )
    return (
        "document.documentElement.style.removeProperty('background');"
        "document.body&&document.body.style.removeProperty('background');"
    )


def set_strips_glass(on: bool, why: str) -> None:
    """Flip the strips between transparent (glass) and their stock look."""
    from aqt.qt import Qt, QColor

    for name, w in glass_widgets():
        try:
            if on:
                w.page().setBackgroundColor(QColor(0, 0, 0, 0))
                w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            else:
                orig = _orig_bg.get(name)
                if orig is not None:
                    w.page().setBackgroundColor(orig)
                # Turning WA_TranslucentBackground off does not undo the
                # WA_NoSystemBackground it implied; do that explicitly.
                w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                w.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
            w.update()
        except Exception as e:
            log(f"strip {name}: FAILED ({e})")
    log(f"strips {'GLASS' if on else 'stock'} ({why})")


def set_strips_body_js(on: bool) -> None:
    for name, w in strip_widgets():
        try:
            w.eval(body_background_js(on))
        except Exception as e:
            log(f"body js {name}: FAILED ({e})")


def on_state_will_change(new_state: str, old_state: str) -> None:
    # Before the new state draws its bars, so the first paint already has the
    # right page background (transparent entering review, stock leaving it).
    set_strips_glass(new_state in CONFIG["glass_states"], f"{old_state} -> {new_state}")


# --- glass CSS ---------------------------------------------------------------

# Tokens: a light translucent fill and 1px highlight read as glass over the
# NSGlassEffectView in dark mode; light mode inverts to a dark edge on a pale
# fill. Anki puts `night-mode` on :root, so these follow the theme.
GLASS_COMMON_CSS = """
body{background:transparent !important}
:root{--lg-fill:rgba(255,255,255,.38);--lg-hover:rgba(255,255,255,.55);
      --lg-hi:rgba(0,0,0,.12);--lg-shadow:rgba(0,0,0,.18)}
:root.night-mode{--lg-fill:rgba(255,255,255,.08);--lg-hover:rgba(255,255,255,.15);
      --lg-hi:rgba(255,255,255,.18);--lg-shadow:rgba(0,0,0,.35)}
"""

# Top bar: the Decks/Add/Browse pill and its items.
GLASS_TOP_CSS = """
body.fancy .toolbar,body.fancy:not(.flat) .toolbar{
  background:var(--lg-fill) !important;
  box-shadow:inset 0 0 0 1px var(--lg-hi) !important}
body.fancy .hitem,body.fancy:not(.flat) .hitem{
  background:transparent !important;border-color:transparent !important}
body.fancy .hitem:hover{background:var(--lg-hover) !important;border-color:transparent !important}
body.fancy .hitem:active{background:var(--lg-fill) !important}
body:not(.fancy) .header{border-bottom:none !important}
"""

# Bottom bar: every button gets the glass edge; ease buttons keep whatever
# background they have (add-ons colour them), the rest get the glass fill.
GLASS_BOTTOM_CSS = """
#outer{border-top:none !important}
button{border:1px solid transparent !important;color:var(--fg) !important;
  border-radius:var(--border-radius-large,15px) !important;
  box-shadow:inset 0 0 0 1px var(--lg-hi),0 4px 12px var(--lg-shadow) !important}
button:not([id^=ease]):not(#defease):not([data-ease]){background:var(--lg-fill) !important}
button:not([id^=ease]):not(#defease):not([data-ease]):hover{background:var(--lg-hover) !important}
button:focus{box-shadow:inset 0 0 0 1px var(--border-focus),0 4px 12px var(--lg-shadow) !important}
"""


# Card area: tint on the root (which paints the whole viewport), everything
# that normally paints an opaque canvas -- body, Anki's #qa, the note type's
# .card -- made transparent so the glass reads through the tint.
GLASS_CONTENT_CSS = """
body,#qa,.card,#qa>*{background:transparent !important;background-color:transparent !important}
html body[class][class][class][class]{background:transparent !important;
  background-color:transparent !important;background-image:none !important}
"""

CONTENT_UNCOVER_JS = r"""
(function(){
  var vw=window.innerWidth, vh=window.innerHeight, area=vw*vh, hits=[];
  var els=[document.body].concat(
      Array.prototype.slice.call(document.querySelectorAll('body *')));
  for (var i=0;i<els.length;i++){
    var el=els[i], cs=getComputedStyle(el), bg=cs.backgroundColor;
    var m=bg.match(/rgba?\(([^)]+)\)/), a=0;
    if(m){ var p=m[1].split(',').map(parseFloat); a=p.length>3?p[3]:1; }
    var hasImg=cs.backgroundImage!=='none';
    if(a<0.95 && !hasImg) continue;
    var r=el.getBoundingClientRect();
    if(el!==document.body && r.width*r.height<area*0.4) continue;
    if(a>=0.95) el.style.setProperty('background-color','transparent','important');
    if(hasImg) el.style.setProperty('background-image','none','important');
    var cls=(typeof el.className==='string'&&el.className.trim())?'.'+el.className.trim().split(/\s+/).join('.'):'';
    hits.push(el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+cls+' '+Math.round(r.width)+'x'+Math.round(r.height)+' '+bg);
  }
  return hits.join(' | ');
})()
"""


_uncover_seen: set = set()



def uncover_card_canvas(*_) -> None:
    """Run on every question/answer render, twice (note-type scripts can add
    wrappers a moment after Anki's own render)."""
    from aqt import mw
    from aqt.qt import QTimer

    if not (CONFIG["content_glass"] and in_glass_state()):
        return
    w = getattr(mw, "web", None)
    if w is None:
        return

    def done(result):
        if result and result not in _uncover_seen:
            _uncover_seen.add(result)
            log(f"card canvas uncovered: {result}")
            flush_log()

    def run():
        try:
            w.evalWithCallback(CONTENT_UNCOVER_JS, done)
        except Exception as e:
            log(f"uncover FAILED ({e})")

    run()
    QTimer.singleShot(250, run)


# webview_will_set_content context class names for the main window's pages.
CONTENT_CONTEXTS = ("Reviewer", "DeckBrowser", "Overview")


def tint_css() -> str:
    """Resolve the tint in Python. The `night-mode` class is added to the page
    root by JS after load, so a CSS variable keyed on it can resolve to the
    light value on some pages; the literal colour cannot."""
    t = CONFIG["glass_tint"]
    try:
        from aqt.theme import theme_manager

        value = t["night"] if theme_manager.night_mode else t["light"]
    except Exception:
        value = t["night"]
    return f":root{{--lg-tint:{value}}}\n"


def glass_css_for(ctx: str) -> str:
    if ctx in CONTENT_CONTEXTS:
        return tint_css() + GLASS_CONTENT_CSS
    is_bottom = "BottomBar" in ctx or "BottomToolbar" in ctx
    return tint_css() + GLASS_COMMON_CSS + (GLASS_BOTTOM_CSS if is_bottom else GLASS_TOP_CSS)


def on_state_did_change(new_state: str, old_state: str) -> None:
    # Both bars get a fresh document on state change (Anki redraws the bottom
    # bar; we redraw the top) so the CSS hook re-applies the glass at load.
    from aqt import mw
    from aqt.qt import QTimer

    if CONFIG["redraw_toolbar_on_state_change"]:
        draw = getattr(getattr(mw, "toolbar", None), "draw", None)
        if draw is not None:
            draw()
    QTimer.singleShot(
        200, lambda: getattr(mw, "toolbarWeb", None) and mw.toolbarWeb.update()
    )


# --- AppKit glass ------------------------------------------------------------

def _parse_rgba(s: str):
    """'rgba(0,0,0,0.28)' -> (r, g, b, a) as 0-1 floats."""
    import re

    m = re.match(r"\s*rgba?\(([^)]+)\)", s or "")
    if not m:
        return (0.0, 0.0, 0.0, 0.28)
    vals = [float(x) for x in m.group(1).split(",")]
    r, g, b = vals[0] / 255.0, vals[1] / 255.0, vals[2] / 255.0
    a = vals[3] if len(vals) > 3 else 1.0
    return (r, g, b, a)


def tint_nscolor(ob):
    """The theme tint as a semi-transparent NSColor, used for the main window's
    background so the titlebar and the transparent webviews are tinted by ONE
    uniform layer over untinted glass (tinting the glass material itself draws
    a dark rim around every glass shape, which we don't want)."""
    try:
        from aqt.theme import theme_manager

        night = theme_manager.night_mode
    except Exception:
        night = True
    t = CONFIG["glass_tint"]
    r, g, b, a = _parse_rgba(t["night"] if night else t["light"])
    return ob.msg(
        ob.cls("NSColor"), "colorWithSRGBRed:green:blue:alpha:", r, g, b, a,
        argtypes=[ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double],
    )


def build_glass(ob, bounds):
    glass_cls = ob.cls("NSGlassEffectView")
    if glass_cls:
        v = ob.msg(ob.msg(glass_cls, "alloc"), "init")
        kind = "NSGlassEffectView"
    else:
        v = ob.msg(ob.msg(ob.cls("NSVisualEffectView"), "alloc"), "init")
        for setter, val in (
            ("setMaterial:", NSVisualEffectMaterialUnderWindowBackground),
            ("setBlendingMode:", NSVisualEffectBlendingModeBehindWindow),
            ("setState:", NSVisualEffectStateActive),
        ):
            ob.msg(v, setter, val, restype=None, argtypes=[ctypes.c_long])
        kind = "NSVisualEffectView (fallback)"
    ob.msg(v, "setFrame:", bounds, restype=None, argtypes=[ob.CGRect])
    ob.msg(v, "setAutoresizingMask:", NSViewBothSizable,
           restype=None, argtypes=[ctypes.c_ulong])
    log(f"built {kind} -> {hex(v or 0)} frame {bounds}")
    return v


# --- separate glass window (no re-parent; hover-safe) ------------------------

def sync_glass_frame(*_) -> None:
    import objc_bridge as ob

    main_win = _state.get("main_win")
    glass_win = _state.get("glass_win")
    if not (main_win and glass_win):
        return
    frame = ob.msg(main_win, "frame", restype=ob.CGRect)
    ob.msg(glass_win, "setFrame:display:", frame, True,
           restype=None, argtypes=[ob.CGRect, ctypes.c_bool])


def install_frame_sync() -> None:
    """Keep the glass window matched to the main window. A child window follows
    the parent's moves on its own, but not its resizes, so sync on both."""
    from aqt import mw
    from aqt.qt import QObject, QEvent, QTimer

    class _Sync(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() in (QEvent.Type.Move, QEvent.Type.Resize,
                             QEvent.Type.Show, QEvent.Type.WindowActivate,
                             QEvent.Type.WindowStateChange):
                QTimer.singleShot(0, sync_glass_frame)
            return False

    f = _Sync(mw)
    mw.installEventFilter(f)
    _state["frame_sync"] = f
    sync_glass_frame()


def build_separate_glass_window() -> None:
    """Full glass look WITHOUT re-parenting Qt's view. Qt keeps ownership of its
    contentView (so mouse-move / hover work); the main window is made
    transparent, and the glass lives in a borderless child window pinned
    directly behind it."""
    import objc_bridge as ob
    from aqt import mw
    from aqt.qt import QApplication

    log("=== separate glass window ===")
    apply_window_qt_attrs()
    if CONFIG["request_alpha_format"]:
        request_alpha_format("separate")
    QApplication.processEvents()

    view = ctypes.c_void_p(int(mw.winId()))
    main_win = ob.msg(view, "window")
    if not main_win:
        log("ABORT: no NSWindow")
        return
    frame = ob.msg(main_win, "frame", restype=ob.CGRect)
    log(f"main NSWindow {hex(main_win)} frame {frame}")

    glass_win = ob.msg(
        ob.msg(ob.cls("NSWindow"), "alloc"),
        "initWithContentRect:styleMask:backing:defer:",
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
        argtypes=[ob.CGRect, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_bool],
    )
    if not glass_win:
        log("ABORT: could not create glass window")
        return
    clear = ob.msg(ob.cls("NSColor"), "clearColor")
    for sel, val in (("setOpaque:", False), ("setIgnoresMouseEvents:", True),
                     ("setHasShadow:", False)):
        ob.msg(glass_win, sel, val, restype=None, argtypes=[ctypes.c_bool])
    ob.msg(glass_win, "setBackgroundColor:", clear,
           restype=None, argtypes=[ctypes.c_void_p])

    glass = build_glass(ob, ob.CGRect(ob.CGPoint(0, 0),
                                      ob.CGSize(frame.size.width, frame.size.height)))
    ob.msg(glass_win, "setContentView:", glass,
           restype=None, argtypes=[ctypes.c_void_p])

    # Child window: tracks the parent's position and stays directly behind it.
    ob.msg(main_win, "addChildWindow:ordered:", glass_win, NSWindowBelow,
           restype=None, argtypes=[ctypes.c_void_p, ctypes.c_long])

    # Main window see-through so the glass behind shows; alpha surface (above)
    # keeps clears working so nothing ghosts.
    ob.msg(main_win, "setOpaque:", False, restype=None, argtypes=[ctypes.c_bool])
    tint_col = tint_nscolor(ob) or clear
    ob.msg(main_win, "setBackgroundColor:", tint_col,
           restype=None, argtypes=[ctypes.c_void_p])
    ob.msg(main_win, "setTitlebarAppearsTransparent:", True,
           restype=None, argtypes=[ctypes.c_bool])

    _state.update(main_win=main_win, glass_win=glass_win, glass=glass,
                  strategy="separate")
    set_strips_glass(in_glass_state(), "initial")
    install_frame_sync()
    log("separate glass window installed + frame sync active")
    log("RESULT: separate window applied without crashing")


# --- recovery / wiring -------------------------------------------------------


def revert() -> None:
    """Remove the glass and restore the normal opaque window, live."""
    import objc_bridge as ob

    set_strips_glass(False, "revert")
    set_strips_body_js(False)
    if _state.get("strategy") == "separate":
        from aqt import mw

        main_win = _state.get("main_win")
        glass_win = _state.get("glass_win")
        fs = _state.pop("frame_sync", None)
        if fs is not None:
            mw.removeEventFilter(fs)
        if main_win and glass_win:
            ob.msg(main_win, "removeChildWindow:", glass_win,
                   restype=None, argtypes=[ctypes.c_void_p])
            ob.msg(glass_win, "orderOut:", None,
                   restype=None, argtypes=[ctypes.c_void_p])
            ob.msg(main_win, "setOpaque:", True,
                   restype=None, argtypes=[ctypes.c_bool])
    _state.clear()
    log("reverted")


def disable_permanently() -> None:
    try:
        with open(DISABLE_PATH, "w") as f:
            f.write("delete this file, or toggle in the add-on config, to re-enable")
    except Exception:
        pass
    from aqt.utils import showInfo

    showInfo("AnkiGlass disabled. Restart Anki to get the normal interface.")


def _show_log() -> None:
    from aqt.utils import showText

    try:
        body = open(LOG_PATH).read()
    except Exception as e:
        body = f"no log ({e}). Enable 'debug_log' in the add-on config."
    showText(body, title="AnkiGlass log", minWidth=760)


def add_menu() -> None:
    from aqt import mw
    from aqt.qt import QAction

    items = [
        ("AnkiGlass: turn off (this session)", revert),
        ("AnkiGlass: disable until re-enabled", disable_permanently),
    ]
    if DEBUG:
        items.append(("AnkiGlass: show log", _show_log))
    mw.form.menuTools.addSeparator()
    for label, fn in items:
        act = QAction(label, mw)
        act.triggered.connect(fn)
        mw.form.menuTools.addAction(act)


def on_main_window_did_init() -> None:
    if sys.platform != "darwin":
        return
    if ADDON_DIR not in sys.path:
        sys.path.insert(0, ADDON_DIR)
    if os.path.exists(DISABLE_PATH):
        add_menu()
        return
    # Crash guard: if a previous apply killed the process, the marker survives
    # and we skip this launch so the user isn't locked into a broken state.
    if os.path.exists(MARKER_PATH):
        log("skipping apply: leftover marker -> previous attempt did not finish")
        add_menu()
        return
    try:
        with open(MARKER_PATH, "w") as f:
            f.write("in progress")
        build_separate_glass_window()
    except Exception:
        log("apply FAILED:\n" + traceback.format_exc())
    finally:
        try:
            os.remove(MARKER_PATH)
        except OSError:
            pass
    add_menu()


def _install() -> None:
    from aqt import gui_hooks, mw
    from aqt.qt import QColor

    gui_hooks.main_window_did_init.append(on_main_window_did_init)
    if sys.platform != "darwin" or os.path.exists(DISABLE_PATH):
        return
    if ADDON_DIR not in sys.path:
        sys.path.insert(0, ADDON_DIR)

    def css_hook(web_content, context):
        ctx = type(context).__name__
        is_bar = any(s in ctx for s in ("Toolbar", "BottomBar"))
        is_content = ctx in CONTENT_CONTEXTS and CONFIG["content_glass"]
        if (is_bar or is_content) and in_glass_state():
            web_content.head += f"<style>{glass_css_for(ctx)}</style>"

    gui_hooks.webview_will_set_content.append(css_hook)

    for hook_name in ("reviewer_did_show_question", "reviewer_did_show_answer",
                      "deck_browser_did_render", "overview_did_refresh"):
        hook = getattr(gui_hooks, hook_name, None)
        if hook is not None:
            hook.append(uncover_card_canvas)

    for hook_name, fn in (("state_will_change", on_state_will_change),
                          ("state_did_change", on_state_did_change)):
        hook = getattr(gui_hooks, hook_name, None)
        if hook is not None:
            hook.append(fn)

    # Capture stock page backgrounds (to restore on revert) and pre-arm the
    # alpha surface format before the window is shown.
    try:
        for name, w in glass_widgets():
            _orig_bg[name] = QColor(w.page().backgroundColor())
        apply_window_qt_attrs()
        if CONFIG["request_alpha_format"]:
            request_alpha_format("early")
    except Exception:
        log("early setup FAILED:\n" + traceback.format_exc())


_install()