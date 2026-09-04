from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from .config import (
    GLOBAL_INSTRUCTIONS_FILE,
    TASKS_FILE,
    TASK_INTERVAL_CHOICES,
    TOOL_RESULT_MAX_CHARS,
    ensure_dirs,
    load_config,
    load_mcp_config,
    load_token,
)
from .providers import make_provider
from .ui import console

_TASKS_LOCK = threading.RLock()


def load_tasks() -> List[Dict[str, Any]]:
    ensure_dirs()
    with _TASKS_LOCK:
        if TASKS_FILE.exists():
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    ensure_dirs()
    with _TASKS_LOCK:
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
        except OSError:
            pass


def load_global_instructions() -> str:
    
    try:
        if GLOBAL_INSTRUCTIONS_FILE.exists():
            return GLOBAL_INSTRUCTIONS_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _parse_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _fmt_dt(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "—"
    try:
        return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(iso_str)[:16]


def compute_next_run(task: Dict[str, Any], base: Optional[datetime] = None) -> Optional[datetime]:
    
    now = base or datetime.now()
    st = task.get("schedule_type")
    if st == "once":
        return None
    if st == "interval":
        mins = int(task.get("interval_minutes") or 60)
        return now + timedelta(minutes=mins)
    run_at = task.get("run_at")
    if not run_at:
        return None
    try:
        ra = datetime.fromisoformat(run_at)
    except (TypeError, ValueError):
        return None
    if st == "daily":
        cand = datetime.combine(now.date(), ra.time())
        if cand <= now:
            cand += timedelta(days=1)
        return cand
    if st == "weekly":
        cand = ra
        while cand <= now:
            cand += timedelta(weeks=1)
        return cand
    return None


def new_task(*, prompt: str, model: str, thinking: bool, search: bool,
             mcp_enabled: bool, schedule_type: str,
             interval_minutes: Optional[int] = None,
             run_at: Optional[datetime] = None,
             output_file: str = "", chain_task_id: str = "",
             system_prompt: str = "",
             selected_tools: Optional[List[str]] = None) -> Dict[str, Any]:
    now = datetime.now()
    task: Dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "prompt": prompt,
        "model": model,
        "thinking_enabled": bool(thinking),
        "search_enabled": bool(search),
        "system_prompt": system_prompt or "",
        "mcp_enabled": bool(mcp_enabled),
        "selected_tools": selected_tools or [],
        "schedule_type": schedule_type,          
        "interval_minutes": interval_minutes,
        "run_at": _iso(run_at),
        "last_run": None,
        "next_run": None,
        "status": "pending",                     
        "result": None,
        "output_file": output_file or "",
        "chain_task_id": chain_task_id or "",
    }
    if schedule_type == "once":
        task["next_run"] = _iso(run_at or now + timedelta(minutes=1))
    elif schedule_type == "interval":
        task["next_run"] = _iso(now + timedelta(minutes=int(interval_minutes or 60)))
    else:
        task["next_run"] = _iso(compute_next_run(task, now))
    return task


def find_task(tasks: List[Dict[str, Any]], ident: str) -> Optional[Dict[str, Any]]:
    
    ident = (ident or "").strip()
    if not ident:
        return None
    matches = [t for t in tasks if t.get("id") == ident or t.get("id", "").startswith(ident)]
    return matches[0] if len(matches) == 1 else None


def _schedule_label(task: Dict[str, Any]) -> str:
    st = task.get("schedule_type", "once")
    if st == "interval":
        return f"every {task.get('interval_minutes') or 60}m"
    if st == "daily":
        try:
            return "daily " + datetime.fromisoformat(task["run_at"]).strftime("%H:%M")
        except Exception:
            return "daily"
    if st == "weekly":
        return "weekly " + _fmt_dt(task.get("run_at"))
    return "once @ " + _fmt_dt(task.get("next_run") or task.get("run_at"))


def vault_root() -> Optional[Path]:
    
    try:
        cfg = load_mcp_config()
    except Exception:
        return None
    for name, scfg in (cfg.get("mcpServers", {}) or {}).items():
        hay = " ".join([
            str(name),
            str(scfg.get("command", "")),
            " ".join(str(a) for a in (scfg.get("args") or [])),
        ]).lower()
        if "filesystem" not in hay and "vault" not in hay:
            continue
        for arg in reversed(scfg.get("args") or []):
            try:
                p = Path(str(arg)).expanduser()
                if p.is_dir():
                    return p
            except OSError:
                continue
    return None


def resolve_output_path(out: str) -> Path:
    
    p = Path(out).expanduser()
    if p.is_absolute():
        return p
    root = vault_root()
    if root:
        return root / p
    return Path.cwd() / p


def _notify_sound() -> None:
    try:
        from .sounds import play_sound
        play_sound("notify")
    except Exception:
        try:
            print("\a", flush=True)
        except Exception:
            pass


def _ask_datetime(label: str, default: Optional[str] = None) -> Optional[datetime]:
    for _ in range(3):
        try:
            s = Prompt.ask(label, default=default) if default else Prompt.ask(label)
        except (KeyboardInterrupt, EOFError):
            return None
        dt = _parse_dt(s or "")
        if dt:
            return dt
        console.print("[warning]Could not parse — use YYYY-MM-DD HH:MM.[/]")
    return None


def _ask_time(label: str, default: str = "09:00"):
    for _ in range(3):
        try:
            s = Prompt.ask(label, default=default)
        except (KeyboardInterrupt, EOFError):
            return None
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(s.strip(), fmt).time()
            except ValueError:
                pass
        console.print("[warning]Use HH:MM format.[/]")
    return None


class TaskScheduler:
    
    CHECK_INTERVAL = 30
    MAX_CHAIN_DEPTH = 10

    def __init__(self, mcp: Optional[Any] = None) -> None:
        self._stop = threading.Event()
        self._exec_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self.mcp = mcp

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="cowork-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._stop.wait(self.CHECK_INTERVAL)
            if self._stop.is_set():
                break
            try:
                self.check_due_tasks()
            except Exception as e:
                console.print(f"[warning]Scheduler error: {e}[/]")

    def check_due_tasks(self) -> None:
        now = datetime.now()
        for task in load_tasks():
            if task.get("status") in ("paused", "running"):
                continue
            nr = task.get("next_run")
            if not nr:
                continue
            try:
                nr_dt = datetime.fromisoformat(nr)
            except (TypeError, ValueError):
                continue
            if now >= nr_dt:
                self.execute_task(task["id"])

    
    def execute_task(self, task_id: str, context_result: Optional[str] = None) -> None:
        
        if not self._exec_lock.acquire(blocking=False):
            console.print("[warning]Task runner is busy with another task — try again shortly.[/]")
            return
        try:
            current_id: Optional[str] = task_id
            ctx = context_result
            depth = 0
            while current_id and depth <= self.MAX_CHAIN_DEPTH:
                ok, result = self._run_single(current_id, ctx)
                if not ok:
                    break
                tasks = load_tasks()
                task = next((t for t in tasks if t["id"] == current_id), None)
                nxt = (task or {}).get("chain_task_id") or None
                current_id = nxt
                ctx = result
                depth += 1
                if current_id:
                    console.print(f"[mcp]⛓ Chaining → task {current_id[:8]}…[/]")
            if current_id and depth > self.MAX_CHAIN_DEPTH:
                console.print("[warning]Task chain depth limit reached — stopping chain.[/]")
        finally:
            self._exec_lock.release()

    def _run_single(self, task_id: str,
                    context_result: Optional[str] = None) -> Tuple[bool, str]:
        tasks = load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task is None:
            console.print(f"[error]Task '{task_id[:8]}…' not found.[/]")
            return False, ""
        if task.get("status") == "running":
            console.print(f"[dim]Task {task_id[:8]} is already running — skipped.[/]")
            return False, ""
        console.print(
            f"[mcp]⚙[/] [accent]Cowork[/]: running task [bold]{task['id'][:8]}[/] "
            f"— {task.get('prompt', '')[:60]}"
        )
        prompt = task.get("prompt", "")
        if context_result:
            prompt += (
                '\n<context result="previous task">\n'
                + context_result[:TOOL_RESULT_MAX_CHARS]
                + "\n</context>"
            )
        task["status"] = "running"
        save_tasks(tasks)

        token = load_token()
        result_text = ""
        ok = False
        if not token and (load_config().get("provider") or {}).get("type", "deepseek") == "deepseek":
            task["result"] = "Failed: no ABYSSAL_TOKEN / DEEPSEEK_TOKEN available (use /token)."
        else:
            system_blocks: List[str] = []
            gi = load_global_instructions()
            if gi:
                system_blocks.append(gi)
            if (task.get("system_prompt") or "").strip():
                system_blocks.append(task["system_prompt"].strip())
            if task.get("mcp_enabled") and self.mcp and self.mcp.tools:
                selected = task.get("selected_tools")
                if selected:
                    help_block = self.mcp.get_help_block_for_tools(selected)
                else:
                    help_block = self.mcp.get_help_block()
                system_blocks.append(help_block)
            final_prompt = prompt
            if system_blocks:
                final_prompt = ("<system>\n" + "\n\n".join(system_blocks) + "\n</system>\n" + prompt)
            try:
                cfg = load_config()
                provider = make_provider(cfg, token=token, debug=False)
                session_id = provider.create_session()
                stream = provider.chat_completion(
                    chat_session_id=session_id,
                    prompt=final_prompt,
                    parent_message_id=None,
                    model_type=task.get("model") or "default",
                    thinking_enabled=bool(task.get("thinking_enabled")),
                    search_enabled=bool(task.get("search_enabled")),
                )
                buf: List[str] = []
                for chunk in stream:
                    if chunk.get("type") == "text":
                        buf.append(chunk.get("content", ""))
                result_text = "".join(buf).strip()
                ok = True
                task["result"] = result_text or "(empty response)"
            except Exception as e:
                task["result"] = f"Failed: {e}"

        now = datetime.now()
        task["last_run"] = now.isoformat()
        task["status"] = "done" if ok else "failed"
        task["next_run"] = None if task.get("schedule_type") == "once" \
            else _iso(compute_next_run(task, now))
        save_tasks(tasks)

        
        if ok and task.get("output_file"):
            try:
                path = resolve_output_path(task["output_file"])
                path.parent.mkdir(parents=True, exist_ok=True)
                md = (
                    f"# Cowork task — {task.get('prompt', '')[:60]}\n"
                    f"_Run: {now.strftime('%Y-%m-%d %H:%M:%S')} · "
                    f"model: {task.get('model', 'default')} · "
                    f"schedule: {_schedule_label(task)}_\n\n"
                    f"{result_text}\n"
                )
                path.write_text(md, encoding="utf-8")
                console.print(f"[success]✓[/] Output saved → [accent]{path}[/]")
            except OSError as e:
                console.print(f"[warning]Could not write output file: {e}[/]")

        
        if ok:
            console.print(Panel(
                Text(f"✓ Task complete: {task.get('prompt', '')[:60]}", style="success"),
                title="[success]Cowork[/]", title_align="left",
                border_style="#14b8a6", padding=(0, 1)))
            _notify_sound()
        else:
            console.print(Panel(
                Text(f"✗ Task failed: {task.get('prompt', '')[:60]}\n"
                     f"{str(task.get('result', ''))[:200]}", style="error"),
                title="[error]Cowork[/]", title_align="left",
                border_style="red", padding=(0, 1)))
        return ok, result_text