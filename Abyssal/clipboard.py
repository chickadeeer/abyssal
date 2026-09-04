
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def copy(text: str) -> bool:
    
    if os.name == "nt":
        return _win_copy(text)
    for cmd in (
        ("pbcopy",),
        ("wl-copy",),
        ("xclip", "-selection", "clipboard"),
        ("xsel", "--clipboard", "--input"),
    ):
        if shutil.which(cmd[0]):
            try:
                p = subprocess.Popen(list(cmd), stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"), timeout=5)
                return p.returncode == 0
            except Exception:
                continue
    return False


def paste() -> str:
    
    if os.name == "nt":
        return _win_paste()
    for cmd in (
        ("pbpaste",),
        ("wl-paste", "--no-newline"),
        ("xclip", "-selection", "clipboard", "-o"),
    ):
        if shutil.which(cmd[0]):
            try:
                out = subprocess.run(list(cmd), capture_output=True, timeout=5)
                if out.returncode == 0:
                    return out.stdout.decode("utf-8", "replace")
            except Exception:
                continue
    return ""


def _win_copy(text: str) -> bool:
    try:
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        if not u32.OpenClipboard(0):
            return False
        try:
            u32.EmptyClipboard()
            data = text.encode("utf-16-le") + b"\x00\x00"
            h = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h:
                return False
            ptr = k32.GlobalLock(h)
            if not ptr:
                return False
            ctypes.memmove(ptr, data, len(data))
            k32.GlobalUnlock(h)
            u32.SetClipboardData(CF_UNICODETEXT, h)
            return True
        finally:
            u32.CloseClipboard()
    except Exception:
        return False


def _win_paste() -> str:
    try:
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        if not u32.OpenClipboard(0):
            return ""
        try:
            h = u32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return ""
            ptr = k32.GlobalLock(h)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                k32.GlobalUnlock(h)
        finally:
            u32.CloseClipboard()
    except Exception:
        return ""