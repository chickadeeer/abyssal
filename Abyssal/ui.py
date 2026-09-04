from __future__ import annotations

from typing import Any, Dict

from rich.align import Align
from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from .config import APP_NAME, APP_VERSION




def build_theme(accent: str = "#0d9488") -> Theme:
    return Theme({
        "info": accent,
        "warning": "yellow",
        "error": "bold red",
        "success": "#14b8a6",
        "thinking": "dim italic #64748b",
        "search": "bold #2dd4bf",
        "user": "bold #5eead4",
        "system": "dim italic #99f6e4",
        "accent": accent,
        "mcp": "bold #14b8a6",
        "dim": "dim",
    })


THEME = build_theme()
console = Console(theme=THEME, highlight=True)


def apply_visual_theme(cfg: Dict[str, Any]) -> None:
    
    vis = cfg.get("visual") or {}
    accent = vis.get("accent", "#0d9488")
    try:
        console._theme = build_theme(accent)
    except Exception:
        pass





def print_banner() -> None:
    banner = Text(
        "\n"
        "  ▄▄▄▄   ▄▄                            ▄▄ \n"
        "▄██▀▀██▄ ██                            ██ \n"
        "███  ███ ████▄ ██ ██ ▄█▀▀▀ ▄█▀▀▀  ▀▀█▄ ██ \n"
        "███▀▀███ ██ ██ ██▄██ ▀███▄ ▀███▄ ▄█▀██ ██ \n"
        "███  ███ ████▀  ▀██▀ ▄▄▄█▀ ▄▄▄█▀ ▀█▄██ ██ \n"
        "                 ██                       \n"
        "               ▀▀▀\n",
        style="bold #0d9488",
    )
    console.print(Align.center(banner))
    console.print(
        Align.center(
            Text(
                f"{APP_NAME} v{APP_VERSION} — Abyssal Proposal System (APS)",
                style="dim italic #115e59",
            )
        )
    )
    console.print()