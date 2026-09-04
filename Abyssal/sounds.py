from __future__ import annotations

import ctypes
import os
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from .config import DEFAULT_SOUNDS, load_config


PRESETS: Dict[str, str] = {
    "abyss-chime": "Abyss Chime — soft two-tone surface ping",
    "deep-ping":   "Deep Ping — low single sonar pulse",
    "blip":        "Blip — short, bright UI tick",
    "sonar-pulse": "Sonar Pulse — descending three-tone sweep",
}
_SEQUENCES: Dict[str, List[Tuple[int, int]]] = {
    "abyss-chime": [(880, 140), (1318, 240)],
    "deep-ping":   [(440, 280)],
    "blip":        [(1250, 80)],
    "sonar-pulse": [(1568, 110), (1046, 110), (698, 200)],
}


def _sounds_cfg() -> Dict:
    cfg = load_config().get("sounds") or {}
    out: Dict = {k: (dict(v) if isinstance(v, dict) else v)
                 for k, v in DEFAULT_SOUNDS.items()}
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def channel_settings(channel: str) -> Dict:
    
    s = _sounds_cfg()
    base = {"enabled": True, "preset": "blip", "file": ""}
    ch = s.get(channel) or {}
    return {"master": bool(s.get("master", True)), **base, **ch}


def _play_file(path: str) -> bool:
    p = Path(path).expanduser()
    if not p.exists():
        return False
    try:
        if os.name == "nt":
            
            SND_FILENAME = 0x00020000
            SND_ASYNC = 0x0001
            ret = ctypes.windll.winmm.sndPlaySoundW(str(p),
                                                    SND_FILENAME | SND_ASYNC)
            return bool(ret)
        for cmd in (("afplay",), ("paplay",), ("aplay",),
                    ("ffplay", "-nodisp", "-autoexit")):
            try:
                subprocess.Popen([*cmd, str(p)],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return True
            except OSError:
                continue
    except Exception:
        pass
    return False


def _beep_sequence(seq: List[Tuple[int, int]]) -> None:
    if os.name == "nt":
        try:
            
            beep = ctypes.windll.kernel32.Beep
            beep.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            for freq, ms in seq:
                beep(freq, ms)
            return
        except Exception:
            pass
    try:
        print("\a", flush=True)
    except Exception:
        pass


def _worker(channel: str) -> None:
    try:
        s = channel_settings(channel)
        if not s.get("master") or not s.get("enabled"):
            return
        preset = s.get("preset") or "blip"
        if preset == "custom":
            if s.get("file") and _play_file(s["file"]):
                return
            preset = "deep-ping"  
        _beep_sequence(_SEQUENCES.get(preset, _SEQUENCES["blip"]))
    except Exception:
        pass


def play_sound(channel: str) -> None:
    
    threading.Thread(target=_worker, args=(channel,), daemon=True).start()