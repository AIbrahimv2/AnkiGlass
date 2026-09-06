# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""Minimal Objective-C runtime bridge over ctypes.

Anki does not bundle PyObjC, so we talk to the ObjC runtime directly. This is
the same technique Anki itself uses for anki_mac_helper/libankihelper.dylib,
except we call AppKit classes instead of shipping our own Swift shims.

arm64 only: on Apple Silicon there is no objc_msgSend_stret, struct returns
(CGRect is a 4-double HFA) come back in v0-v3 like any other call.
"""

from __future__ import annotations

import ctypes
import ctypes.util

# --- structs -----------------------------------------------------------------


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]


class CGRect(ctypes.Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]

    def __repr__(self) -> str:
        return (
            f"CGRect({self.origin.x:.0f},{self.origin.y:.0f},"
            f"{self.size.width:.0f}x{self.size.height:.0f})"
        )


# --- runtime -----------------------------------------------------------------

libobjc = ctypes.CDLL(ctypes.util.find_library("objc"))

# Loading these registers their classes with the runtime so objc_getClass can
# find them. AppKit is already loaded inside Anki (Qt links it), but being
# explicit costs nothing and makes the failure mode obvious.
_appkit = ctypes.CDLL(ctypes.util.find_library("AppKit"))
_foundation = ctypes.CDLL(ctypes.util.find_library("Foundation"))

libobjc.objc_getClass.restype = ctypes.c_void_p
libobjc.objc_getClass.argtypes = [ctypes.c_char_p]
libobjc.sel_registerName.restype = ctypes.c_void_p
libobjc.sel_registerName.argtypes = [ctypes.c_char_p]
libobjc.class_getName.restype = ctypes.c_char_p
libobjc.class_getName.argtypes = [ctypes.c_void_p]
libobjc.object_getClass.restype = ctypes.c_void_p
libobjc.object_getClass.argtypes = [ctypes.c_void_p]

_msgsend_addr = ctypes.cast(libobjc.objc_msgSend, ctypes.c_void_p).value


def cls(name: str):
    """Look up an ObjC class by name. Returns None if it does not exist."""
    return libobjc.objc_getClass(name.encode())


def sel(name: str):
    return libobjc.sel_registerName(name.encode())


def msg(receiver, selector: str, *args, restype=ctypes.c_void_p, argtypes=()):
    """Send an ObjC message, building a correctly-typed objc_msgSend per call.

    argtypes must describe the *arguments only*; receiver and selector are
    prepended here. Getting this wrong is how you segfault the host app, so
    every call site passes them explicitly.
    """
    proto = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)
    fn = proto(_msgsend_addr)
    return fn(receiver, sel(selector), *args)


def class_name_of(obj) -> str:
    if not obj:
        return "<nil>"
    return libobjc.class_getName(libobjc.object_getClass(obj)).decode()


def has_selector(obj, selector: str) -> bool:
    if not obj:
        return False
    return bool(
        msg(obj, "respondsToSelector:", sel(selector),
            restype=ctypes.c_bool, argtypes=[ctypes.c_void_p])
    )