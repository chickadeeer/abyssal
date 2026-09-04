
from __future__ import annotations

import json
from typing import Any, Dict

from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from .config import CONSENT_FILE, ensure_dirs

FEATURES: Dict[str, str] = {
    "mcp-proposals": "The model may propose brand-new MCP plugins. On approval their code is written to disk and loaded.",
    "mcp-edits": "The model may propose edits to existing MCP plugins (shown as a diff).",
    "system-proposals": "The model may propose changes to your prompt segments / system prompt.",
    "new-session": "The model may request a fresh session. ALL current context is lost.",
    "needs-input": "The model may pause the loop and ask you a direct question.",
    "questions": "The model may show structured multi-question forms ([QUESTIONS]).",
    "skill-writes": "The model may write or update skills in your local skills library.",
}


def load_consent() -> Dict[str, Any]:
    ensure_dirs()
    if CONSENT_FILE.exists():
        try:
            data = json.loads(CONSENT_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**{k: False for k in FEATURES}, **data}
        except Exception:
            pass
    fresh = {k: False for k in FEATURES}
    save_consent(fresh)
    return fresh


def save_consent(data: Dict[str, Any]) -> None:
    ensure_dirs()
    CONSENT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_consented(key: str) -> bool:
    return load_consent().get(key) is True


def request_consent(key: str, console) -> bool:
    
    if key not in FEATURES:
        return True
    data = load_consent()
    val = data.get(key)
    if val is True:
        return True
    if val == "denied":
        return False
    console.print(Panel(
        Text(FEATURES[key]),
        title=f"[accent]APS feature consent — {key}[/]",
        title_align="left", border_style="#0d9488", padding=(0, 1),
    ))
    try:
        ok = Confirm.ask(f"Allow the model to use [accent]{key}[/]?", default=False)
    except (KeyboardInterrupt, EOFError):
        ok = False
    data[key] = True if ok else "denied"
    save_consent(data)
    if not ok:
        console.print(
            f"[dim]Declined. You can change this later with "
            f"/consent set {key} on[/]")
    return ok