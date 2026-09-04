
from __future__ import annotations

import importlib.util
import subprocess
import sys
from typing import Dict, List

from rich.prompt import Confirm

from .config import load_config


_IMPORT_NAMES: Dict[str, str] = {
    "pillow": "PIL",
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn",
}


def _import_name(pkg: str) -> str:
    return _IMPORT_NAMES.get(pkg.lower().strip(), pkg.strip().replace("-", "_"))


def packages_missing(packages: List[str]) -> List[str]:
    missing: List[str] = []
    for pkg in packages or []:
        pkg = (pkg or "").strip()
        if not pkg:
            continue
        try:
            if importlib.util.find_spec(_import_name(pkg)) is None:
                missing.append(pkg)
        except (ImportError, ValueError):
            missing.append(pkg)
    return missing


def ensure_dependencies(packages: List[str], console) -> bool:
    
    pkgs = [p for p in (packages or []) if (p or "").strip()]
    if not pkgs:
        return True
    missing = packages_missing(pkgs)
    if not missing:
        return True
    auto = bool(load_config().get("auto_install_deps", False))
    if not auto:
        console.print("[mcp]MCP server needs packages that are not installed:[/]")
        for p in missing:
            console.print(f"  • [accent]{p}[/]")
        try:
            ok = Confirm.ask("Install them now with pip?", default=False)
        except (KeyboardInterrupt, EOFError):
            ok = False
        if not ok:
            console.print("[warning]Skipped — the server/tool may fail.[/]")
            return False
    try:
        with console.status("[mcp]Installing dependencies…[/]", spinner="dots"):
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", *missing],
                capture_output=True, text=True, timeout=600,
            )
        if proc.returncode != 0:
            console.print(f"[error]pip failed: {proc.stderr.strip()[-400:]}[/]")
            return False
        console.print(f"[success]✓[/] Installed: {', '.join(missing)}")
        return True
    except Exception as e:
        console.print(f"[error]Dependency install failed: {e}[/]")
        return False