
from __future__ import annotations

import os
import re
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from . import clipboard

FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
RESET_SECONDS = 10.0


class CodeBlockRegistry:
    def __init__(self) -> None:
        self._blocks: Dict[int, str] = {}
        self._counts: Dict[int, int] = {}
        self._last_copy: Dict[int, float] = {}
        self._next = 1
        
        self._spans: List[Tuple[int, int, int]] = []  
        self._total = 0

    def reset(self) -> None:
        self._blocks.clear()
        self._counts.clear()
        self._last_copy.clear()
        self._next = 1
        self._spans = []
        self._total = 0

    def register(self, code: str) -> int:
        bid = self._next
        self._next += 1
        self._blocks[bid] = code
        return bid

    def has_blocks(self) -> bool:
        return bool(self._blocks)

    def copy(self, bid: int) -> Tuple[bool, str]:
        code = self._blocks.get(bid)
        if code is None:
            return False, f"No code block #{bid} in the current message."
        now = time.time()
        if now - self._last_copy.get(bid, 0.0) > RESET_SECONDS:
            self._counts[bid] = 0
        if not clipboard.copy(code):
            return False, "Clipboard unavailable on this system."
        self._counts[bid] = self._counts.get(bid, 0) + 1
        self._last_copy[bid] = now
        n = self._counts[bid]
        return True, ("Copied!" if n == 1 else f"Copied ({n}×)")


CODE_BLOCKS = CodeBlockRegistry()


def _height(console, renderable) -> int:
    try:
        from rich.segment import Segment
        segs = console.render(renderable, console.options)
        return len(list(Segment.split_lines(segs)))
    except Exception:
        return 1


def render_group(text: str, console=None, accent: str = "#0d9488",
                 registry: Optional[CodeBlockRegistry] = None) -> Group:
    
    reg = registry or CODE_BLOCKS
    reg.reset()
    parts: List = []
    line_cursor = 1
    pos = 0
    for m in FENCE_RE.finditer(text or ""):
        before = (text[pos:m.start()] or "").strip()
        if before:
            md = Markdown(before)
            parts.append(md)
            if console is not None:
                line_cursor += _height(console, md)
        lang = (m.group(1) or "").strip().split()
        lang = lang[0] if lang else "text"
        code = m.group(2).rstrip("\n")
        bid = reg.register(code)
        header = Text()
        header.append(f" ⧉ {bid} ", style=f"bold {accent}")
        header.append("click to copy", style="dim italic")
        panel = Panel(
            Syntax(code, lang, word_wrap=True),
            title=header, title_align="left",
            border_style=accent, padding=(0, 1),
        )
        parts.append(panel)
        if console is not None:
            h = _height(console, panel)
            reg._spans.append((bid, line_cursor, line_cursor + h - 1))
            line_cursor += h
        pos = m.end()
    tail = (text[pos:] or "").strip()
    if tail:
        md = Markdown(tail)
        parts.append(md)
        if console is not None:
            line_cursor += _height(console, md)
    if not parts:
        parts.append(Markdown(text or ""))
    reg._total = line_cursor - 1
    return Group(*parts)







class _Listener:
    def __init__(self, console, ranges: List[Tuple[int, int, int]]):
        self.console = console
        self.ranges = ranges
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None


_STATE: Optional[_Listener] = None
_LOCK = threading.Lock()


def _cursor_row(timeout: float = 0.4) -> Optional[int]:
    try:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return None
        if os.name == "nt":
            import msvcrt
            sys.stdout.write("\x1b[6n")
            sys.stdout.flush()
            buf = ""
            t0 = time.time()
            while time.time() - t0 < timeout:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    buf += ch
                    if ch == "R":
                        break
                else:
                    time.sleep(0.01)
        else:
            import select
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                sys.stdout.write("\x1b[6n")
                sys.stdout.flush()
                buf = ""
                t0 = time.time()
                while time.time() - t0 < timeout:
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        ch = sys.stdin.read(1)
                        buf += ch
                        if ch == "R":
                            break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        m = re.search(r"\[(\d+);(\d+)R", buf)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def arm_click_listener(console, outer_pad: int = 2) -> None:
    
    global _STATE
    stop_click_listener()
    reg = CODE_BLOCKS
    if not reg._spans:
        return
    row = _cursor_row()
    if row is None:
        return
    bottom = row - 1
    top = bottom - (reg._total + outer_pad) + 1
    ranges = [(bid, top + s, top + e) for bid, s, e in reg._spans]
    st = _Listener(console, ranges)
    with _LOCK:
        _STATE = st
    st.thread = threading.Thread(target=_listen, args=(st,), daemon=True)
    st.thread.start()


def stop_click_listener() -> None:
    global _STATE
    with _LOCK:
        st, _STATE = _STATE, None
    if st is None:
        return
    st.stop_event.set()
    try:
        sys.stdout.write("\x1b[?1000l\x1b[?1006l")
        sys.stdout.flush()
    except Exception:
        pass
    if st.thread and st.thread.is_alive():
        st.thread.join(timeout=0.3)


def _read_chars(stop_event: threading.Event):
    
    try:
        if os.name == "nt":
            import msvcrt
            while not stop_event.is_set():
                if msvcrt.kbhit():
                    yield msvcrt.getwch()
                else:
                    time.sleep(0.02)
        else:
            import select
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop_event.is_set():
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        yield sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        return


def _listen(st: _Listener) -> None:
    try:
        sys.stdout.write("\x1b[?1000h\x1b[?1006h")
        sys.stdout.flush()
        buf = ""
        deadline = time.time() + 120.0
        for ch in _read_chars(st.stop_event):
            if st.stop_event.is_set() or time.time() > deadline:
                break
            if ch == "\x1b":
                buf = "\x1b"
                continue
            if buf:
                buf += ch
                m = re.match(r"^\x1b\[<(\d+);(\d+);(\d+)([Mm])$", buf)
                if m:
                    b, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    pressed = m.group(4) == "M"
                    buf = ""
                    if pressed and b == 0:
                        for bid, y0, y1 in st.ranges:
                            if y0 <= y <= y1:
                                ok, label = CODE_BLOCKS.copy(bid)
                                style = "success" if ok else "warning"
                                st.console.print(
                                    f"[{style}]⧉ code block {bid} — {label}[/]")
                                break
                    continue
                if len(buf) > 16 or (not buf.startswith("\x1b[<") and ch.isalnum()):
                    buf = ""  
                    break
                continue
            
            break
    finally:
        try:
            sys.stdout.write("\x1b[?1000l\x1b[?1006l")
            sys.stdout.flush()
        except Exception:
            pass
        with _LOCK:
            global _STATE
            if _STATE is st:
                _STATE = None