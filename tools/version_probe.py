"""Run AnkiGlass in a real Anki of another version, and check the glass.

    <python> tools/version_probe.py [src] [--fullscreen] [--shots=DIR]

<python> is a Python with that Anki version's aqt, such as an environment
AnkiExamTimeline's tests/run_on_anki.sh made (tests/fixture/anki/<version>),
or Anki's own Python for the installed app. docs/ankiweb-listing.md says
which versions were checked, and how.

It starts Anki on a new, empty profile in a temporary folder, with a copy of
the add-on (so the real add-on's log and settings are left alone) and a probe
add-on. The probe looks at the deck list, a deck's overview, a review and
AnkiGlass's Settings, checks the glass on each from inside Anki (the glass
window behind the main window, the transparent pages, the glass CSS), then
quits. The window shows on screen for about 25 seconds. --fullscreen also
takes it full screen and back, about 10 seconds more. --shots=DIR saves a
screenshot of each screen there.

It never touches an Anki that's already running: Anki's check for a second
instance, which hands over to the running one and can take over its socket,
is switched off.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/Applications/Anki.app/Contents/Resources/app_packages"

# Started in a new Python: argv[1] is the base folder.
LAUNCH = f"""
import importlib.util, os, sys
if importlib.util.find_spec("aqt") is None:
    sys.path.insert(0, {APP!r})
import aqt
from aqt import AnkiApp
from aqt.profiles import ProfileManager
AnkiApp.KEY = "anki-glass-probe-%d" % os.getpid()
AnkiApp.secondInstance = lambda self: False
# English, where a new base folder would ask for a language first.
ProfileManager.setDefaultLang = lambda self, idx: self.setLang("en_US")
# No "Anki has been updated" prompt in front of the screenshots.
import aqt.update
aqt.update.check_for_update = lambda *a, **k: None
sys.argv = ["anki", "-b", sys.argv[1]]
aqt.run()
"""

PROBE = r'''
import ctypes, json, os, platform, subprocess, sys, traceback

from aqt import gui_hooks, mw
from aqt.qt import QTimer, qVersion

OUT = os.environ["GLASS_PROBE_OUT"]
SHOTS = os.environ.get("GLASS_PROBE_SHOTS", "")
FULL = os.environ.get("GLASS_PROBE_FULLSCREEN") == "1"
R = {"checks": [], "info": {}}
STEPS = []
BODY = "getComputedStyle(document.body).backgroundColor"
CLEAR = "rgba(0, 0, 0, 0)"


def check(name, ok, detail=""):
    R["checks"].append([name, bool(ok), str(detail)[:300]])


def step(delay):
    def deco(fn):
        STEPS.append((delay, fn))
        return fn
    return deco


def run_steps(i=0):
    if i >= len(STEPS):
        return
    delay, fn = STEPS[i]

    def go():
        try:
            fn()
        except Exception:
            check(f"step {fn.__name__}", False, traceback.format_exc())
        run_steps(i + 1)

    QTimer.singleShot(delay, go)


def js(web, expr, name, test):
    def done(v):
        try:
            check(name, test(v), v)
        except Exception as e:
            check(name, False, f"{v!r}: {e}")

    web.evalWithCallback(expr, done)


def shot(name, widget=None):
    """The window as it shows on screen, glass and all. Qt's frameGeometry() can be
    wrong for the main window here, so ask AppKit, whose y counts from the bottom
    of the main screen."""
    if not SHOTS:
        return
    ob = sys.modules["objc_bridge"]
    win = ob.msg(ctypes.c_void_p(int((widget or mw).winId())), "window")
    f = ob.msg(win, "frame", restype=ob.CGRect)
    screen = ob.msg(ob.msg(ob.cls("NSScreen"), "screens"), "firstObject")
    top = ob.msg(screen, "frame", restype=ob.CGRect).size.height - f.origin.y - f.size.height
    subprocess.run(["screencapture", "-x",
                    f"-R{f.origin.x:.0f},{top:.0f},{f.size.width:.0f},{f.size.height:.0f}",
                    os.path.join(SHOTS, name + ".png")])


def glass():
    return sys.modules["anki_glass"], sys.modules["objc_bridge"]


def native(where):
    G, ob = glass()
    st = G._state
    main, win = st.get("main_win"), st.get("glass_win")
    check(f"{where}: glass window built", st.get("strategy") == "separate" and main and win,
          st.get("strategy"))
    check(f"{where}: main window see-through",
          not ob.msg(main, "isOpaque", restype=ctypes.c_bool))
    kids = ob.msg(main, "childWindows")
    check(f"{where}: glass window is the main window's child",
          ob.msg(kids, "containsObject:", win, restype=ctypes.c_bool, argtypes=[ctypes.c_void_p]))
    check(f"{where}: glass window on screen", ob.msg(win, "isVisible", restype=ctypes.c_bool))
    a = ob.msg(main, "frame", restype=ob.CGRect)
    b = ob.msg(win, "frame", restype=ob.CGRect)
    check(f"{where}: glass window has the main window's frame", repr(a) == repr(b), f"{a} {b}")


def pages(where):
    for name in ("toolbarWeb", "web", "bottomWeb"):
        c = getattr(mw, name).page().backgroundColor()
        check(f"{where}: {name} page background clear", c.alpha() == 0, c.alpha())
    js(mw.toolbarWeb, BODY, f"{where}: toolbar transparent", lambda v: v == CLEAR)
    js(mw.toolbarWeb, "getComputedStyle(document.querySelector('.toolbar')).backgroundColor",
       f"{where}: toolbar pill has the glass fill", lambda v: v.startswith("rgba(255, 255, 255, 0."))
    js(mw.web, BODY, f"{where}: page transparent", lambda v: v == CLEAR)
    js(mw.bottomWeb, BODY, f"{where}: bottom bar transparent", lambda v: v == CLEAR)
    js(mw.bottomWeb, "getComputedStyle(document.querySelector('button')).boxShadow",
       f"{where}: bottom buttons have the glass edge", lambda v: "inset" in v or "0px 0px 0px 1px" in v)


@step(4000)
def deck_list():
    import anki.buildinfo

    G, ob = glass()
    info = R["info"]
    info["anki"] = anki.buildinfo.version
    info["qt"] = qVersion()
    try:
        from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion
        info["chromium"] = qWebEngineChromiumVersion()
    except Exception:
        pass
    info["python"] = platform.python_version()
    info["macos"] = platform.mac_ver()[0]
    info["glass view"] = ob.class_name_of(G._state.get("glass"))
    info["kit"] = "anki_glass.kit" in sys.modules
    check("deck list: shown", mw.state == "deckBrowser", mw.state)
    native("deck list")
    pages("deck list")
    js(mw.web, "getComputedStyle(document.querySelector('table')).backgroundColor",
       "deck list: deck table has the glass fill", lambda v: v.startswith("rgba(255, 255, 255, 0."))
    shot("1-deck-list")


@step(500)
def to_overview():
    mw.moveToState("overview")


@step(3000)
def overview():
    check("overview: shown", mw.state == "overview", mw.state)
    native("overview")
    pages("overview")
    shot("2-overview")


@step(500)
def to_review():
    col = mw.col
    note = col.new_note(col.models.by_name("Basic"))
    note["Front"] = "The front of a card"
    note["Back"] = "The back"
    col.add_note(note, 1)
    mw.moveToState("review")


@step(3500)
def review():
    check("review: shown", mw.state == "review", mw.state)
    native("review")
    pages("review")
    js(mw.web, "getComputedStyle(document.getElementById('qa')).backgroundColor",
       "review: card area transparent", lambda v: v == CLEAR)
    js(mw.web, "document.getElementById('qa').innerText", "review: card shows",
       lambda v: "The front of a card" in v)
    shot("3-review")
    mw.reviewer._showAnswer()


@step(2500)
def answer():
    js(mw.web, "document.getElementById('qa').innerText", "review: answer shows",
       lambda v: "The back" in v)
    js(mw.bottomWeb, "document.querySelectorAll('button').length", "review: answer buttons show",
       lambda v: v >= 4)
    pages("answer")
    shot("4-answer")


@step(500)
def to_settings():
    if "anki_glass.kit" in sys.modules:
        mw.addonManager.configAction("anki_glass")()


@step(3500)
def settings():
    if "anki_glass.kit" not in sys.modules:
        return
    w = sys.modules["anki_glass.kit.page"]._window
    check("settings: window opens", w is not None and w.isVisible())
    js(w.web, "document.body.innerText", "settings: AnkiGlass's options show",
       lambda v: all(s in v for s in ("Glass on these screens", "Glass behind the card",
                                      "In dark mode", "In light mode", "Keep a log")))
    shot("5-settings", w)
    QTimer.singleShot(1500, w.close)


if FULL:
    @step(2500)
    def to_full_screen():
        mw.moveToState("deckBrowser")
        mw.showFullScreen()

    @step(4000)
    def full_screen():
        G, ob = glass()
        main = G._state["main_win"]
        check("full screen: glass taken away", G.glass_hidden())
        check("full screen: glass window off screen",
              not ob.msg(G._state["glass_win"], "isVisible", restype=ctypes.c_bool))
        # Anki's normal solid background. (Qt 6.6 marks the window see-through
        # again by itself, which doesn't show with a solid background.)
        bg = ob.msg(main, "backgroundColor")
        check("full screen: main window background solid",
              ob.msg(bg, "alphaComponent", restype=ctypes.c_double) == 1.0)
        R["info"]["opaque in full screen"] = ob.msg(main, "isOpaque", restype=ctypes.c_bool)
        shot("6-full-screen")
        mw.showNormal()

    @step(4000)
    def after_full_screen():
        G, ob = glass()
        check("after full screen: glass back", not G.glass_hidden())
        native("after full screen")


@step(1000)
def finish():
    log = os.path.join(mw.addonManager.addonsFolder("anki_glass"), "user_files", "anki_glass.log")
    try:
        text = open(log).read()
    except OSError as e:
        text = f"no log: {e}"
    check("log: glass applied", "RESULT: separate window applied without crashing" in text)
    check("log: nothing failed", "FAILED" not in text, text[-600:])
    with open(OUT, "w") as f:
        json.dump(R, f, indent=1)
    QTimer.singleShot(8000, lambda: os._exit(0))
    mw.unloadProfileAndExit()


gui_hooks.profile_did_open.append(lambda: run_steps())
'''


def main() -> int:
    args = sys.argv[1:]
    flags = [a for a in args if a.startswith("--")]
    rest = [a for a in args if not a.startswith("--")]
    src = os.path.abspath(rest[0] if rest else "src")
    shots = next((a.split("=", 1)[1] for a in flags if a.startswith("--shots=")), "")

    base = tempfile.mkdtemp(prefix="anki-glass-probe-")
    addons = os.path.join(base, "addons21")
    shutil.copytree(src, os.path.join(addons, "anki_glass"),
                    ignore=shutil.ignore_patterns("user_files", "__pycache__", "meta.json"))
    with open(os.path.join(addons, "anki_glass", "meta.json"), "w") as f:
        json.dump({"config": {"debug_log": True}}, f)
    os.makedirs(os.path.join(addons, "zz_glass_probe"))
    with open(os.path.join(addons, "zz_glass_probe", "__init__.py"), "w") as f:
        f.write(PROBE)

    out = os.path.join(base, "probe.json")
    env = dict(os.environ, GLASS_PROBE_OUT=out,
               GLASS_PROBE_FULLSCREEN="1" if "--fullscreen" in flags else "0")
    if shots:
        os.makedirs(shots, exist_ok=True)
        env["GLASS_PROBE_SHOTS"] = os.path.abspath(shots)
    try:
        subprocess.run([sys.executable, "-c", LAUNCH, base], env=env, timeout=240,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print("FAIL  Anki didn't finish in 4 minutes")
    try:
        with open(out) as f:
            r = json.load(f)
    except OSError:
        print(f"FAIL  no results (Anki's folder is kept: {base})")
        return 1
    shutil.rmtree(base, ignore_errors=True)

    print(", ".join(f"{k} {v}" for k, v in r["info"].items()))
    failed = 0
    for name, ok, detail in r["checks"]:
        print(f"{'ok  ' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({detail})"))
        failed += not ok
    print(f"\n{len(r['checks']) - failed} of {len(r['checks'])} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
