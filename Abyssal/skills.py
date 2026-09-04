from __future__ import annotations

import difflib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import SKILLS_DIR


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", (name or "").strip())[:48]


def _skill_dir(name: str) -> Path:
    return SKILLS_DIR / _safe_name(name)


def _load_meta(d: Path) -> Optional[Dict[str, Any]]:
    p = d / "skill.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_meta(d: Path, meta: Dict[str, Any]) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "skill.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_version(d: Path, version: int) -> Tuple[str, bool]:
    p = d / f"v{version}.md"
    if not p.exists():
        return "", False
    try:
        return p.read_text(encoding="utf-8"), True
    except OSError:
        return "", False


def list_skills() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not SKILLS_DIR.exists():
        return out
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta = _load_meta(d)
        if meta:
            out.append(meta)
    return out


def get_skill(name: str) -> Optional[Dict[str, Any]]:
    d = _skill_dir(name)
    meta = _load_meta(d)
    if not meta:
        return None
    content, _ = _read_version(d, int(meta.get("version") or 1))
    meta = dict(meta)
    meta["content"] = content
    return meta


def read_skill(name: str) -> Tuple[Optional[Dict[str, Any]], str]:
    meta = get_skill(name)
    if not meta:
        return None, ""
    return meta, meta.get("content", "")


def write_skill(name: str, content: str, description: Optional[str] = None,
                note: str = "") -> Dict[str, Any]:
    
    name = (name or "").strip()
    d = _skill_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    meta = _load_meta(d)
    now = datetime.now().isoformat()
    if meta is None:
        meta = {
            "name": name,
            "description": (description or "").strip(),
            "version": 0,
            "versions": 0,
            "created_at": now,
            "updated_at": now,
            "history": [],
        }
    new_version = int(meta.get("versions") or 0) + 1
    (d / f"v{new_version}.md").write_text(content, encoding="utf-8")
    if description is not None:
        meta["description"] = description.strip()
    meta["versions"] = new_version
    meta["version"] = new_version
    meta["updated_at"] = now
    meta.setdefault("history", []).append(
        {"version": new_version, "note": note or "updated", "at": now})
    _save_meta(d, meta)
    return meta


def rollback_skill(name: str, version: int) -> Tuple[bool, str]:
    d = _skill_dir(name)
    meta = _load_meta(d)
    if not meta:
        return False, f"Skill '{name}' not found."
    _, ok = _read_version(d, version)
    if not ok:
        return False, f"Skill '{name}' has no version v{version}."
    now = datetime.now().isoformat()
    meta["version"] = version
    meta["updated_at"] = now
    meta.setdefault("history", []).append(
        {"version": version, "note": f"rollback to v{version}", "at": now})
    _save_meta(d, meta)
    return True, f"Skill '{name}' rolled back to v{version}."


def diff_skills(name: str, va: int, vb: int) -> Tuple[bool, str]:
    d = _skill_dir(name)
    meta = _load_meta(d)
    if not meta:
        return False, f"Skill '{name}' not found."
    a, oka = _read_version(d, va)
    b, okb = _read_version(d, vb)
    if not oka:
        return False, f"Skill '{name}' has no version v{va}."
    if not okb:
        return False, f"Skill '{name}' has no version v{vb}."
    diff = difflib.unified_diff(
        a.splitlines(), b.splitlines(),
        fromfile=f"{name} v{va}", tofile=f"{name} v{vb}", lineterm="")
    return True, "\n".join(diff) or "(versions are identical)"


def delete_skill(name: str) -> bool:
    d = _skill_dir(name)
    if not d.exists():
        return False
    shutil.rmtree(d, ignore_errors=True)
    return True


def skills_summary_block() -> str:
    
    skills = list_skills()
    if not skills:
        return ""
    lines = [
        "# SKILLS LIBRARY",
        "Reusable context written from past tasks. Read the relevant skill "
        "BEFORE starting a matching task (skill_read). When you learn "
        "something reusable, write it down with skill_write.",
    ]
    for s in skills:
        lines.append(
            f"- {s['name']} (v{s.get('version', 1)}): "
            f"{str(s.get('description', ''))[:120]}")
    return "\n".join(lines)