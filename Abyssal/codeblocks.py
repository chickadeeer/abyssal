

from __future__ import annotations
import contextlib
import os
import re
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text

from . import clipboard

FENCE_START = re.compile(r"```([^\n`]*)\n")
TOOL_CALL_START = re.compile(r"\[TOOL_CALL:\s*([A-Za-z0-9_.\-]+)\s*\]")
RESET_SECONDS = 10.0

_COPY_LABELS = [
    "Copied once!", "Copied twice!", "Copied thrice!", "Copied quarice!",
    "Copied quintice!", "Copied sextice!", "Copied septice!", "Copied octice!",
    "Copied nifice!", "Copied dentice!", "Copied elventice!", "Copied duodentice!",
    "Copied thirteentice!", "Copied fourteentice!", "Copied fifteentice!",
    "Copied sixteentice!", "Copied seventeentice!", "Copied eighteentice!",
    "Copied nineteentice!", "Copied twentice!", "Copied twentice-once!",
    "Copied twentice-twice!", "Copied twentice-thrice!", "Copied twentice-quarice!",
    "Copied twentice-quintice!", "Copied twentice-sextice!", "Copied twentice-septice!",
    "Copied twentice-octice!", "Copied twentice-nifice!", "Copied thirtice!",
    "Copied thirtice-once!", "Copied thirtice-twice!", "Copied thirtice-thrice!",
    "Copied thirtice-quarice!", "Copied thirtice-quintice!", "Copied thirtice-sextice!",
    "Copied thirtice-septice!", "Copied thirtice-octice!", "Copied thirtice-nifice!",
    "Copied fortice!", "Copied fortice-once!", "Copied fortice-twice!",
    "Copied fortice-thrice!", "Copied fortice-quarice!", "Copied fortice-quintice!",
    "Copied fortice-sextice!", "Copied fortice-septice!", "Copied fortice-octice!",
    "Copied fortice-nifice!", "Copied fiftice!", "Copied fiftice-once!",
    "Copied fiftice-twice!", "Copied fiftice-thrice!", "Copied fiftice-quarice!",
    "Copied fiftice-quintice!", "Copied fiftice-sextice!", "Copied fiftice-septice!",
    "Copied fiftice-octice!", "Copied fiftice-nifice!", "Copied sixtice!",
    "Copied sixtice-once!", "Copied sixtice-twice!", "Copied sixtice-thrice!",
    "Copied sixtice-quarice!", "Copied sixtice-quintice!", "Copied sixtice-sextice!",
    "Copied sixtice-septice!", "Copied sixtice-octice!", "Copied sixtice-nifice!",
    "Copied seventice!", "Copied seventice-once!", "Copied seventice-twice!",
    "Copied seventice-thrice!", "Copied seventice-quarice!", "Copied seventice-quintice!",
    "Copied seventice-sextice!", "Copied seventice-septice!", "Copied seventice-octice!",
    "Copied seventice-nifice!", "Copied eightice!", "Copied eightice-once!",
    "Copied eightice-twice!", "Copied eightice-thrice!", "Copied eightice-quarice!",
    "Copied eightice-quintice!", "Copied eightice-sextice!", "Copied eightice-septice!",
    "Copied eightice-octice!", "Copied eightice-nifice!", "Copied nintice!",
    "Copied nintice-once!", "Copied nintice-twice!", "Copied nintice-thrice!",
    "Copied nintice-quarice!", "Copied nintice-quintice!", "Copied nintice-sextice!",
    "Copied nintice-septice!", "Copied nintice-octice!", "Copied nintice-nifice!"
]


def find_blocks(text: str):
    blocks = []
    pos = 0
    while pos < len(text):
        m_fence = FENCE_START.search(text, pos)
        m_tool = TOOL_CALL_START.search(text, pos)

        starts = []
        if m_fence: starts.append(('fence', m_fence))
        if m_tool: starts.append(('tool', m_tool))

        if not starts: break

        starts.sort(key=lambda x: x[1].start())
        btype, m = starts[0]

        start_idx = m.start()
        content_start = m.end()

        if btype == 'fence':
            end_idx = text.find("```", content_start)
            if end_idx != -1:
                is_closed = True
                content = text[content_start:end_idx]
                block_end = end_idx + 3
            else:
                is_closed = False
                content = text[content_start:]
                block_end = len(text)
            blocks.append({
                'type': 'fence',
                'lang': (m.group(1) or "").strip().split()[0] if (m.group(1) or "").strip() else "text",
                'content': content,
                'is_closed': is_closed,
                'start': start_idx,
                'end': block_end,
            })
            pos = block_end if is_closed else len(text)
        else:
            end_idx = text.find("[/TOOL_CALL]", content_start)
            if end_idx != -1:
                is_closed = True
                content = text[content_start:end_idx]
                block_end = end_idx + 12
            else:
                is_closed = False
                content = text[content_start:]
                block_end = len(text)
            blocks.append({
                'type': 'tool',
                'name': m.group(1).strip(),
                'content': content,
                'is_closed': is_closed,
                'start': start_idx,
                'end': block_end,
            })
            pos = block_end if is_closed else len(text)
    return blocks


class CodeBlockRegistry:
    def __init__(self) -> None:
        self._blocks: Dict[int, str] = {}
        self._types: Dict[int, str] = {}
        self._meta: Dict[int, str] = {}
        self._start_times: Dict[int, float] = {}
        self._end_times: Dict[int, float] = {}
        self._closed: Dict[int, bool] = {}
        self._counts: Dict[int, int] = {}
        self._last_copy: Dict[int, float] = {}
        self._next = 1
        self._spans: List[Tuple[int, int, int]] = []  
        self._total = 0
        self._idx_to_bid: Dict[int, int] = {}

    def clear_all(self) -> None:
        self._blocks.clear()
        self._types.clear()
        self._meta.clear()
        self._start_times.clear()
        self._end_times.clear()
        self._closed.clear()
        self._counts.clear()
        self._last_copy.clear()
        self._next = 1
        self._spans = []
        self._total = 0
        self._idx_to_bid.clear()

    def reset(self) -> None:
        self._spans = []
        self._total = 0

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
        if n <= len(_COPY_LABELS):
            label = _COPY_LABELS[n-1]
        else:
            label = f"Copied ({n}×)"
        return True, label


CODE_BLOCKS = CodeBlockRegistry()


def _height(console, renderable) -> int:
    try:
        from rich.segment import Segment
        segs = console.render(renderable, console.options)
        return len(list(Segment.split_lines(segs)))
    except Exception:
        return 1


def render_group(text: str, console=None, accent: str = "#0d9488",
                 registry: Optional[CodeBlockRegistry] = None, 
                 show_stream_ui: bool = True,
                 vis: Optional[Dict] = None) -> Group:
    
    reg = registry or CODE_BLOCKS
    reg.reset()
    vis = vis or {}
    cb_mode = vis.get("codeblocks", "normal")
    tc_mode = vis.get("tool_calls", "tab")

    parts: List = []
    line_cursor = 1
    current_pos = 0
    blocks = find_blocks(text)

    for b in blocks:
        before = text[current_pos:b['start']].strip()
        if before:
            md = Markdown(before)
            parts.append(md)
            if console: line_cursor += _height(console, md)

        bid = reg._idx_to_bid.get(b['start'])
        if bid is None:
            bid = reg._next
            reg._next += 1
            reg._idx_to_bid[b['start']] = bid
            reg._start_times[bid] = time.time()
            reg._blocks[bid] = b['content']
            reg._types[bid] = b['type']
            reg._meta[bid] = b.get('lang') or b.get('name')

        is_closed = b['is_closed']
        if is_closed and bid not in reg._end_times:
            reg._end_times[bid] = time.time()
        reg._closed[bid] = is_closed

        if b['type'] == 'fence':
            if cb_mode == "compact":
                preview = b['content'].replace("\n", " ")[:60]
                header = Text(f"▣ {reg._meta[bid]} ", style="dim")
                header.append(preview, style="dim")
                panel = Panel(header, border_style=accent, padding=(0, 1))
            else:
                header = Text()
                if show_stream_ui:
                    if not is_closed:
                        elapsed = time.time() - reg._start_times[bid]
                        header.append(f" ⧉ {bid} ", style=f"bold {accent}")
                        header.append("streaming ", style="dim italic")
                        header.append(f"{elapsed:.1f}s", style="yellow")
                    else:
                        duration = reg._end_times[bid] - reg._start_times[bid]
                        header.append(" ✓ ", style="bold green")
                        header.append(f"⧉ {bid} ", style=f"bold {accent}")
                        header.append(f"{duration:.2f}s", style="dim")
                else:
                    header.append(f" ⧉ {bid} ", style=f"bold {accent}")
                    header.append("click to copy", style="dim italic")

                content_renderable = Syntax(b['content'], reg._meta[bid], word_wrap=True)
                if not is_closed and show_stream_ui:
                    spinner = Spinner("dots", style=accent)
                    content_renderable = Group(content_renderable, spinner)

                panel = Panel(
                    content_renderable,
                    title=header, title_align="left",
                    border_style=accent, padding=(0, 1),
                )
            parts.append(panel)
            if console:
                h = _height(console, panel)
                reg._spans.append((bid, line_cursor, line_cursor + h - 1))
                line_cursor += h

        else: 
            if tc_mode == "compact":
                preview = b['content'].replace("\n", " ")[:60]
                header = Text(f"⚙ {reg._meta[bid]}(", style="dim")
                header.append(preview, style="dim")
                header.append(")", style="dim")
                panel = Panel(header, border_style="#14b8a6", padding=(0, 1))
            else:
                header = Text()
                if show_stream_ui:
                    if not is_closed:
                        elapsed = time.time() - reg._start_times[bid]
                        header.append(f" ⚙ {reg._meta[bid]} ", style="bold #14b8a6")
                        header.append("executing ", style="dim italic")
                        header.append(f"{elapsed:.1f}s", style="yellow")
                    else:
                        duration = reg._end_times[bid] - reg._start_times[bid]
                        header.append(" ✓ ", style="bold green")
                        header.append(f"⚙ {reg._meta[bid]} ", style="bold #14b8a6")
                        header.append(f"{duration:.2f}s", style="dim")
                else:
                    header.append(f" ⚙ {reg._meta[bid]} ", style="bold #14b8a6")

                content_renderable = Syntax(b['content'], "json", word_wrap=True)
                if not is_closed and show_stream_ui:
                    spinner = Spinner("dots", style="#14b8a6")
                    content_renderable = Group(content_renderable, spinner)

                panel = Panel(
                    content_renderable,
                    title=header, title_align="left",
                    border_style="#14b8a6", padding=(0, 1),
                )
            parts.append(panel)
            if console:
                h = _height(console, panel)
                line_cursor += h

        current_pos = b['end']

    tail = text[current_pos:].strip()
    if tail:
        md = Markdown(tail)
        parts.append(md)
        if console: line_cursor += _height(console, md)

    if not parts:
        parts.append(Markdown(text or ""))

    reg._total = line_cursor - 1
    return Group(*parts)





@contextlib.contextmanager
def _vt_console_modes():
    
    old_in_mode = None
    old_out_mode = None
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        stdin = kernel32.GetStdHandle(-10)
        stdout = kernel32.GetStdHandle(-11)
        in_mode = ctypes.c_uint()
        out_mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(stdin, ctypes.byref(in_mode)):
            old_in_mode = in_mode.value
            kernel32.SetConsoleMode(stdin, old_in_mode | 0x0200)  
        if kernel32.GetConsoleMode(stdout, ctypes.byref(out_mode)):
            old_out_mode = out_mode.value
            kernel32.SetConsoleMode(stdout, old_out_mode | 0x0004)  
    try:
        yield
    finally:
        if os.name == "nt" and (old_in_mode is not None or old_out_mode is not None):
            import ctypes
            kernel32 = ctypes.windll.kernel32
            stdin = kernel32.GetStdHandle(-10)
            stdout = kernel32.GetStdHandle(-11)
            if old_in_mode is not None:
                kernel32.SetConsoleMode(stdin, old_in_mode)
            if old_out_mode is not None:
                kernel32.SetConsoleMode(stdout, old_out_mode)





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
                    if ch == "R": break
                else:
                    time.sleep(0.01)
        else:
            import select, termios, tty
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
                        if ch == "R": break
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
    if not reg._spans: return

    with _vt_console_modes():
        row = _cursor_row()
        if row is None: return
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
    if st is None: return
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
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            STD_INPUT_HANDLE = -10
            h_stdin = kernel32.GetStdHandle(STD_INPUT_HANDLE)

            KEY_EVENT = 0x0001

            class KEY_EVENT_RECORD(ctypes.Structure):
                _fields_ = [
                    ("bKeyDown", wintypes.BOOL),
                    ("wRepeatCount", wintypes.WORD),
                    ("wVirtualKeyCode", wintypes.WORD),
                    ("wVirtualScanCode", wintypes.WORD),
                    ("uChar", ctypes.c_wchar),
                    ("dwControlKeyState", wintypes.DWORD),
                ]

            class INPUT_RECORD_UNION(ctypes.Union):
                _fields_ = [
                    ("KeyEvent", KEY_EVENT_RECORD),
                ]

            class INPUT_RECORD(ctypes.Structure):
                _fields_ = [
                    ("EventType", wintypes.WORD),
                    ("Event", INPUT_RECORD_UNION),
                ]

            buf = (INPUT_RECORD * 64)()
            num_read = wintypes.DWORD(0)

            while not stop_event.is_set():
                ok = kernel32.ReadConsoleInputW(
                    h_stdin, buf, 64, ctypes.byref(num_read)
                )
                if not ok or num_read.value == 0:
                    time.sleep(0.02)
                    continue
                for i in range(num_read.value):
                    rec = buf[i]
                    if rec.EventType == KEY_EVENT and rec.Event.KeyEvent.bKeyDown:
                        ch = rec.Event.KeyEvent.uChar
                        if ch:
                            yield ch
        else:
            import select, termios, tty
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
    with _vt_console_modes():
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
                        
                        if pressed and (b & 3) in (0, 1, 2):
                            for bid, y0, y1 in st.ranges:
                                if y0 <= y <= y1:
                                    ok, label = CODE_BLOCKS.copy(bid)
                                    style = "success" if ok else "warning"
                                    st.console.print(f"[{style}]⧉ code block {bid} — {label}[/]")
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