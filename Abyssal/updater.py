

from __future__ import annotations
import io
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple
import requests
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

REPO = "chickadeeer/abyssal"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/refs/heads/main"
ZIP_URL = f"https://codeload.github.com/{REPO}/zip/refs/heads/main"
CHANGELOG_URL = "https://raw.githubusercontent.com/chickadeeer/abyssalinfo/refs/heads/main/changes"


REPLACE_ITEMS = ("Abyssal", "dsk", "requirements.txt", "run.bat", "LICENSE", "README.md", "version", "CHANGELOG.md")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _version_tuple(v: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", (v or "").strip())
    return tuple(int(n) for n in nums) or (0,)

def _read_local_version() -> Optional[str]:
    
    version_file = PROJECT_ROOT / "version"
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip().lstrip("v")
        except OSError:
            pass
    return None

def remote_version(timeout: float = 5.0) -> Optional[str]:
    
    try:
        r = requests.get(f"{RAW_BASE}/version", timeout=timeout)
        if r.status_code == 200 and r.text.strip():
            return r.text.strip().lstrip("v")
    except Exception:
        pass
    return None

def fetch_changelog(timeout: float = 5.0) -> Optional[str]:
    
    try:
        r = requests.get(CHANGELOG_URL, timeout=timeout)
        if r.status_code == 200 and r.text.strip():
            return r.text.strip()
    except Exception:
        pass
    return None

def check_on_startup(console, current_version: str = None) -> None:
    
    local_ver = _read_local_version() or current_version
    if not local_ver:
        return
    try:
        rv = remote_version()
        if not rv:
            return
        if _version_tuple(rv) <= _version_tuple(local_ver):
            return
            
        changelog = fetch_changelog()
        repo_url = f"https://github.com/{REPO}"
        
        body = Text()
        body.append(f"Abyssal v{rv} is available (you are on v{local_ver}).\n", style="bold")
        if changelog:
            body.append("\n")
            body.append(changelog, style="accent")
        else:
            body.append("\n(Could not fetch changelog)\n", style="dim")
            
        body.append(f"\nLook at the repo here for changes: {repo_url}\n", style="accent")
        
        console.print(Panel(body, title="[accent]Update available[/]",
                            title_align="left", border_style="#0d9488", padding=(0, 1)))
        try:
            ok = Confirm.ask(
                "Update now? [warning]Local modifications to app files will be overwritten[/]",
                default=False)
        except (KeyboardInterrupt, EOFError):
            ok = False
        if ok:
            perform_update(console)
    except Exception:
        return  

def perform_update(console) -> bool:
    try:
        with console.status("[accent]Downloading main branch…[/]", spinner="dots"):
            r = requests.get(ZIP_URL, timeout=120)
            r.raise_for_status()
        tmp = Path(tempfile.mkdtemp(prefix="abyssal-update-"))
        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                z.extractall(tmp)
            roots = [p for p in tmp.iterdir() if p.is_dir()]
            if not roots:
                console.print("[error]Unexpected archive layout.[/]")
                return False
            src_root = roots[0]
            for item in REPLACE_ITEMS:
                src = src_root / item
                if not src.exists():
                    continue
                dest = PROJECT_ROOT / item
                if src.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            
            for pycache in PROJECT_ROOT.rglob("__pycache__"):
                if pycache.is_dir():
                    shutil.rmtree(pycache, ignore_errors=True)
            console.print(Panel(
                Text("Update complete. Restart Abyssal to run the new version.\n"
                     "Your sessions, skills, config and plugins were not touched.",
                     style="success"),
                title="[success]Abyssal updated[/]", title_align="left",
                border_style="#14b8a6", padding=(0, 1)))
            return True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        console.print(f"[error]Update failed: {e}[/]")
        return False