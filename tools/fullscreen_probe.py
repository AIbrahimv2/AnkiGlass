"""Check AnkiGlass in full screen, with a stand-in main window.

Loads the add-on's real code against a plain Qt main window, puts it full
screen, and asks the window server for the on-screen order of this process's
windows (front to back): is the glass window in front of the main window?
Then leaves full screen and checks again. Before the fix, the glass window
went in front in full screen and blurred all of Anki.

It shows a window and takes the screen full screen for about 5 seconds, so
run it when that's fine. Use Anki's own Python (it has Qt):

    PY=~/Library/Application\\ Support/AnkiProgramFiles/python/*/bin/python3
    $PY tools/fullscreen_probe.py src
"""
import ctypes
import ctypes.util
import importlib.util
import sys
import time
import types

SRC = sys.argv[1] if len(sys.argv) > 1 else "src"
sys.path.insert(0, "/Applications/Anki.app/Contents/Resources/app_packages")
sys.path.insert(0, SRC)

from aqt.qt import QApplication, QLabel, QMainWindow, QMenu  # noqa: E402

app = QApplication.instance() or QApplication(["probe"])
mw = QMainWindow()
mw.setCentralWidget(QLabel("AnkiGlass full-screen probe"))
mw.addonManager = types.SimpleNamespace(getConfig=lambda name: {"debug_log": False})
mw.form = types.SimpleNamespace(menuTools=QMenu())
mw.state = "deckBrowser"
import aqt  # noqa: E402

aqt.mw = mw

spec = importlib.util.spec_from_file_location("anki_glass", f"{SRC}/__init__.py")
glass = importlib.util.module_from_spec(spec)
sys.modules["anki_glass"] = glass
spec.loader.exec_module(glass)

# --- the window server's view -------------------------------------------------
cg = ctypes.CDLL(ctypes.util.find_library("CoreGraphics"))
cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
cf.CFArrayGetCount.restype = ctypes.c_long
cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
cf.CFDictionaryGetValue.restype = ctypes.c_void_p
cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
cf.CFStringCreateWithCString.restype = ctypes.c_void_p
cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
cf.CFNumberGetValue.restype = ctypes.c_bool
cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
cf.CFRelease.argtypes = [ctypes.c_void_p]


def key(s):
    return cf.CFStringCreateWithCString(None, s.encode(), 0x08000100)


K_PID, K_NUM = key("kCGWindowOwnerPID"), key("kCGWindowNumber")


def num(d, k):
    v = cf.CFDictionaryGetValue(d, k)
    out = ctypes.c_long(0)
    if v:
        cf.CFNumberGetValue(v, 4, ctypes.byref(out))
    return out.value


def onscreen_order():
    """This process's on-screen window numbers, front to back."""
    arr = cg.CGWindowListCopyWindowInfo(1, 0)  # kCGWindowListOptionOnScreenOnly
    me = __import__("os").getpid()
    out = []
    for i in range(cf.CFArrayGetCount(arr)):
        d = cf.CFArrayGetValueAtIndex(arr, i)
        if num(d, K_PID) == me:
            out.append(num(d, K_NUM))
    cf.CFRelease(arr)
    return out


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


import objc_bridge as ob  # noqa: E402


def number(win):
    return ob.msg(win, "windowNumber", restype=ctypes.c_long)


def report(stage):
    order = onscreen_order()
    m, g = number(glass._state["main_win"]), number(glass._state["glass_win"])
    where = ("not on screen" if g not in order else
             "IN FRONT of the main window" if order.index(g) < order.index(m) else "behind the main window")
    print(f"{stage:18} full screen={mw.isFullScreen()!s:5}  glass window {where}", flush=True)
    return where


mw.resize(900, 600)
mw.show()
pump(1.0)
glass.build_separate_glass_window()
pump(0.5)
results = [report("windowed")]
mw.showFullScreen()
pump(2.5)
results.append(report("full screen"))
mw.showNormal()
pump(2.5)
results.append(report("left full screen"))
mw.close()
pump(0.3)
ok = results == ["behind the main window", "not on screen", "behind the main window"]
print("PROBE", "PASSED" if ok else "FAILED", results, flush=True)
