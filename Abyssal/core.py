from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from prompt_toolkit.key_binding import KeyBindings
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .agent import AGENT_SETTINGS_DEFAULTS
from .config import (
    AUTONOMY_MODES,
    MCP_HELP_INTERVAL,
    MODELS,
    all_local_transcripts,
    load_config,
    load_token,
    mask,
    save_config,
    save_token,
    token_source,
    transcript_path,
)
from .cowork import load_tasks, vault_root
from .mcp import MCPManager
from .providers import make_provider
from .skills import list_skills, skills_summary_block
from .ui import apply_visual_theme, console, print_banner
from .visual import get_visual
from . import aps_guide, consent

try:
    from dsk.api import AuthenticationError, DeepSeekError
except ImportError:
    from api import AuthenticationError, DeepSeekError  


class BaseCLI:
    

    def __init__(
        self,
        token: Optional[str] = None,
        debug: bool = False,
        model: Optional[str] = None,
        resume_session: Optional[str] = None,
    ):
        self.cfg = load_config()
        self.debug = debug or self.cfg.get("debug", False)
        self.model = model or self.cfg.get("model", "default")
        self.thinking_enabled = self.cfg.get("thinking", False)
        self.search_enabled = self.cfg.get("search", False)
        self.provider = None
        self.session_id: Optional[str] = None
        self.session_title: str = ""
        self.parent_message_id: Optional[int] = None
        self.messages: List[Dict[str, Any]] = []
        self._session_index: List[str] = []
        self._resume_target = resume_session
        self._cancelled = False
        self._next_prompt_default = ""
        self.mcp = MCPManager()
        self.taskman = None
        self._next_tools_reminder_at = MCP_HELP_INTERVAL

        
        self.autonomy_mode = self.cfg.get("autonomy", "human-needed")
        if self.autonomy_mode not in AUTONOMY_MODES:
            self.autonomy_mode = "human-needed"
        self.agent_settings: Dict[str, bool] = dict(AGENT_SETTINGS_DEFAULTS)
        self.agent_settings.update(self.cfg.get("agent_toggles", {}))
        preset = AUTONOMY_MODES[self.autonomy_mode]
        if self.autonomy_mode != "custom":
            self.agent_settings.update(preset.get("toggles", {}))
        self.session_notes: List[str] = []
        self._mcp_rejected_plugins: set = set()
        self._exit_requested = False

        
        self._mcp_loop = asyncio.new_event_loop()

        
        self.pending_file_ids: List[str] = []
        self.uploaded_files: List[Dict[str, Any]] = []

        
        aps_guide.ensure_guide()
        consent.load_consent()
        apply_visual_theme(self.cfg)

        if token:
            save_token(token.strip())

        self.kb = KeyBindings()

        @self.kb.add("c-j")
        @self.kb.add("escape", "enter")
        def _newline(event):
            event.app.current_buffer.insert_text("\n")

        @self.kb.add("enter")
        def _submit(event):
            event.app.current_buffer.validate_and_handle()

        @self.kb.add("c-v")
        def _paste(event):
            try:
                from . import clipboard
                data = clipboard.paste()
                if data:
                    event.app.current_buffer.insert_text(data)
            except Exception:
                pass

        self.prompt_session = None

    
    def visual(self) -> Dict[str, Any]:
        return get_visual(self.cfg)

    
    def get_segments(self) -> List[Dict[str, Any]]:
        segs = self.cfg.get("prompt_segments")
        if not isinstance(segs, list):
            return []
        return [s for s in segs if isinstance(s, dict)]

    def save_segments(self, segs: List[Dict[str, Any]]) -> None:
        self.cfg["prompt_segments"] = segs
        save_config(self.cfg)

    @property
    def system_prompt(self) -> str:
        
        return "\n\n".join(
            str(s.get("text", "")).strip() for s in self.get_segments()
            if str(s.get("text", "")).strip()
        ).strip()

    
    def print_banner(self) -> None:
        print_banner()

    def status_line(self) -> Text:
        parts = [
            f"[accent]session[/]: {self.session_id[:8]}…" if self.session_id else "[dim]no session[/]",
            f"[accent]provider[/]: {getattr(self.provider, 'name', '—') if self.provider else '—'}",
            f"[accent]model[/]: {self.model}",
            f"[accent]thinking[/]: {'[success]on[/]' if self.thinking_enabled else '[dim]off[/]'}",
            f"[search]web[/]: {'[success]on[/]' if self.search_enabled else '[dim]off[/]'}",
        ]
        mode = AUTONOMY_MODES.get(self.autonomy_mode, {})
        parts.append(f"[dim]auto: {mode.get('label', self.autonomy_mode)}[/]")
        if self.mcp.tools:
            parts.append(f"[mcp]mcp[/]: {len(self.mcp.tools)} tools")
        n_skills = len(list_skills())
        if n_skills:
            parts.append(f"[dim]skills: {n_skills}[/]")
        if self.pending_file_ids:
            parts.append(f"[accent]files[/]: {len(self.pending_file_ids)} pending")
        n_segs = len(self.get_segments())
        if n_segs:
            parts.append(f"[system]prompt[/]: {n_segs} segment(s)")
        if self.session_notes:
            parts.append(f"[dim]notes: {len(self.session_notes)}[/]")
        tasks = load_tasks()
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        running = sum(1 for t in tasks if t.get("status") == "running")
        if pending > 0 or running > 0:
            task_str = []
            if pending > 0:
                task_str.append(f"{pending} pending")
            if running > 0:
                task_str.append(f"{running} running")
            parts.append(f"[warning]{', '.join(task_str)} tasks[/]")
        v_root = vault_root()
        if v_root:
            parts.append(f"[dim]vault: {v_root}[/]")
        parts.append(f"debug: {'[warning]on[/]' if self.debug else '[dim]off[/]'}")
        return Text.from_markup("  │  ".join(parts))

    def print_status(self) -> None:
        console.print(Rule(self.status_line(), style="#115e59"))

    
    def authenticate(self) -> bool:
        ptype = (self.cfg.get("provider") or {}).get("type", "deepseek")
        if ptype == "openai":
            provider = make_provider(self.cfg, debug=self.debug)
            try:
                with console.status("[accent]Verifying local endpoint…[/]", spinner="dots"):
                    provider.verify()
            except Exception as e:
                console.print(f"[error]Provider check failed: {e}[/]")
                console.print("[dim]Fix it with /provider openai <base_url> <model> [api_key][/dim]")
                return False
            self.provider = provider
            pcfg = self.cfg.get("provider", {})
            console.print(
                f"[success]✓[/] Connected to OpenAI-compatible endpoint "
                f"[accent]{pcfg.get('base_url')}[/] · model [accent]{pcfg.get('model')}[/]")
            return True
        
        for _ in range(3):
            token = load_token()
            if not token:
                console.print("[info]No ABYSSAL_TOKEN / DEEPSEEK_TOKEN found in env or .env files.[/]")
                token = Prompt.ask("[accent]Paste your Abyssal auth token[/]").strip()
                if not token:
                    console.print("[error]A token is required.[/]")
                    continue
                path = save_token(token)
                console.print(f"[success]✓[/] Token saved to [accent]{path}[/] (mode 600)")
            provider = make_provider(self.cfg, token=token, debug=self.debug)
            self.provider = provider
            console.print(
                f"[success]✓[/] Authenticated  [dim](source: {token_source()}, {mask(token or '')})[/]"
            )
            return True
        return False

    
    def new_session(self, quiet: bool = False) -> bool:
        if not self.provider:
            return False
        with console.status("[accent]Creating session…[/]", spinner="dots"):
            try:
                self.session_id = self.provider.create_session()
            except DeepSeekError as e:
                console.print(f"[error]Failed to create session: {e}[/]")
                return False
            except Exception as e:
                console.print(f"[error]Failed to create session: {e}[/]")
                return False
        self.parent_message_id = None
        self.messages.clear()
        self.session_title = ""
        self._next_tools_reminder_at = MCP_HELP_INTERVAL
        self.session_notes = []
        self._mcp_rejected_plugins = set()
        if not quiet:
            console.print(f"[success]✓[/] New session [accent]{self.session_id[:12]}…[/]")
        return True

    def _apply_session(self, session_id: str) -> None:
        self.session_id = session_id
        t = json.loads(transcript_path(session_id).read_text(encoding="utf-8")) \
            if transcript_path(session_id).exists() else {}
        self.messages = t.get("messages", [])
        self.parent_message_id = t.get("parent_message_id")
        self.session_title = t.get("title", "")
        self._next_tools_reminder_at = len(self.messages) + MCP_HELP_INTERVAL
        self.session_notes = []
        self._mcp_rejected_plugins = set()

    def _save_transcript(self) -> None:
        if not self.session_id:
            return
        data = {
            "session_id": self.session_id,
            "title": self.session_title,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "parent_message_id": self.parent_message_id,
            "messages": self.messages,
            "updated_at": datetime.now().isoformat(),
        }
        try:
            transcript_path(self.session_id).write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def cmd_sessions(self) -> None:
        if not self.provider:
            return
        with console.status("[accent]Fetching sessions…[/]", spinner="dots"):
            try:
                remote = self.provider.list_sessions()
            except Exception as e:
                console.print(f"[error]Could not list sessions: {e}[/]")
                return
        local = all_local_transcripts()
        table = Table(
            title="Chat Sessions",
            border_style="#115e59",
            header_style="bold #0d9488",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("ID", style="accent")
        table.add_column("Title")
        table.add_column("Updated", style="dim")
        table.add_column("", width=2)
        rows, seen = [], set()
        for s in remote:
            sid = str(s.get("id") or s.get("session_id") or "")
            if not sid:
                continue
            seen.add(sid)
            rows.append({
                "id": sid,
                "title": s.get("title") or s.get("name") or "",
                "updated": s.get("updated_at") or s.get("create_time") or "",
            })
        for sid, t in local.items():
            if sid not in seen:
                rows.append({
                    "id": sid,
                    "title": t.get("title", "") + " [dim](local only)[/]",
                    "updated": t.get("updated_at", ""),
                })
        rows.sort(key=lambda r: str(r["updated"]), reverse=True)
        self._session_index = [r["id"] for r in rows]
        if not rows:
            console.print("[dim]No sessions yet. Type a message to start one.[/]")
            return
        for i, r in enumerate(rows, 1):
            ts = r["updated"]
            if isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts).strftime("%Y-%m-%d %H:%M")
            elif isinstance(ts, str) and ts:
                ts = ts[:16].replace("T", " ")
            marker = "[success]●[/]" if r["id"] == self.session_id else ""
            table.add_row(
                str(i),
                r["id"][:16] + "…",
                r["title"][:48] or "[dim]untitled[/]",
                str(ts),
                marker,
            )
        console.print(table)
        console.print("[dim]Resume: /use <#> · Rename: /rename <title> · Delete: /del <#>[/]")

    
    def _aps_block(self) -> str:
        s = self.agent_settings
        mode = AUTONOMY_MODES.get(self.autonomy_mode, {})

        def state(key: str) -> str:
            return "ENABLED" if s.get(key) else "disabled"

        header = "\n".join([
            "# ABYSSAL PROPOSAL SYSTEM (APS) — RUNTIME STATE",
            f"AUTONOMY MODE: {mode.get('label', self.autonomy_mode)} — {mode.get('desc', '')}",
            "",
            "APS feature states (controlled by the human via /agent and /autonomy):",
            f"- confirm every tool call: {state('confirm-tools')}",
            f"- proposals need approval: {state('confirm-proposals')}",
            f"- MCP plugin proposals: {state('allow-mcp-proposals')}",
            f"- system-prompt proposals: {state('allow-system-proposals')}",
            f"- new-session requests: {state('allow-model-new')}",
            f"- human-input pauses: {state('allow-model-pause')}",
            f"- structured question forms: {state('allow-model-questions')}",
            "",
            "Any feature that also requires one-time user consent will be "
            "blocked with an explanation until the human grants it.",
        ])
        footer = "\n".join([
            "All MCP servers run in ephemeral mode: the process is launched, "
            "the tool runs, then the process is torn down immediately.",
        ])
        return f"{header}\n\n{aps_guide.load_guide()}\n\n{footer}"

    
    def build_final_prompt(self, user_prompt: str) -> str:
        
        if self.parent_message_id is None and not self.messages:
            blocks: List[str] = []
            segs = self.get_segments()
            for seg in segs:
                text = str(seg.get("text", "")).strip()
                if text:
                    blocks.append(text)
            blocks.append(self._aps_block())
            show_tools = any(bool(s.get("show_tools", True)) for s in segs) if segs else True
            if show_tools:
                short = self.mcp.get_short_block()
                if short:
                    blocks.append(short)
            skills = skills_summary_block()
            if skills:
                blocks.append(skills)
            if blocks:
                return "<system>\n" + "\n\n".join(blocks) + f"\n</system>\n{user_prompt}"
        return user_prompt

    def _maybe_attach_tools_reminder(self, prompt: str) -> str:
        
        if len(self.messages) >= self._next_tools_reminder_at:
            self._next_tools_reminder_at = len(self.messages) + MCP_HELP_INTERVAL
            console.print(f"[mcp]ⓘ Re-injecting MCP tool reference (every {MCP_HELP_INTERVAL} messages)[/]")
            return prompt + "\n<tools_reminder>\n" + self.mcp.get_help_block() + "\n</tools_reminder>"
        return prompt