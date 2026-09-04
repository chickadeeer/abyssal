
from __future__ import annotations
import shlex
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from . import __version__, aps_guide, clipboard, consent
from .agent import AGENT_SETTINGS_DEFAULTS, SETTING_DESCRIPTIONS
from .config import (
    APP_NAME,
    AUTONOMY_MODES,
    CONFIG_FILE,
    CONSENT_FILE,
    MODELS,
    PROMPTS_DIR,
    load_config,
    load_token,
    mask,
    save_config,
    token_source,
    transcript_path,
)
from .cowork import load_tasks
from .dependencies import packages_missing
from .skills import (delete_skill, diff_skills, list_skills, read_skill,
                     rollback_skill, write_skill)
from .sounds import PRESETS as SOUND_PRESETS
from .sounds import play_sound
from .ui import apply_visual_theme, console
from .updater import check_on_startup, perform_update
from .visual import CHOICES as VISUAL_CHOICES
from .visual import DEFAULT_VISUAL, validate as validate_visual

try:
    from dsk.api import DeepSeekError
except ImportError:
    from api import DeepSeekError  

def _on_off(val: str) -> Optional[bool]:
    v = val.lower()
    if v in ("on", "1", "true", "yes"): return True
    if v in ("off", "0", "false", "no"): return False
    return None

class CommandsMixin:
    

    
    def cmd_help(self) -> None:
        groups = [
            ("Chat", [
                ("/thinking [on|off]", "Toggle thinking mode"),
                ("/search [on|off]", "Toggle web search"),
                ("/model [name]", "Show or set model (DeepSeek provider)"),
            ]),
            ("Sessions", [
                ("/sessions", "List remote + local sessions"),
                ("/new", "Start a fresh session"),
                ("/use <#|id>", "Resume a session"),
                ("/rename <title>", "Rename current session"),
                ("/del [#|id]", "Delete a session"),
            ]),
            ("Autonomy & APS", [
                ("/autonomy [mode]", "Show or set autonomy mode"),
                ("/agent [key] [on|off]", "Agent toggles"),
                ("/aps show|edit|reset|backups|restore <n>", "APS guide"),
                ("/consent [list|set <key> on|off|reset]", "APS feature consent"),
                ("/notes [list|add <text>|clear]", "Session notes"),
            ]),
            ("Prompts", [
                ("/prompt show|add|remove|move|edit|tools|clear|stack", "Prompt segments"),
                ("/prompt save <name> / load <name>", "Prompt library"),
            ]),
            ("MCP & Skills", [
                ("/mcp [status|add|remove|refresh|deps]", "MCP servers"),
                ("/mcp-help", "APS guide + full tool reference"),
                ("/deps auto on|off · /deps check [server]", "Dependency installs"),
                ("/skills · /skill show|diff|rollback|delete|add", "Skills"),
            ]),
            ("Files & Tasks", [
                ("/upload <path> · /files [list|clear]", "File uploads"),
                ("/task add|list|run|pause|result|remove|clear", "Cowork tasks"),
            ]),
            ("Sounds & Visual", [
                ("/sounds [master on|off] · /sound <ch> …", "Sounds"),
                ("/visual [set <key> <value>]", "UI appearance"),
            ]),
            ("System", [
                ("/provider [deepseek|openai …]", "Chat backend"),
                ("/token <token> · /debug [on|off]", "Auth & logging"),
                ("/status [detail]", "Status line / full detail"),
                ("/update", "Check for updates now"),
                ("/history /save /undo /retry /copy /cc /paste /edit", "Message tools"),
                ("/exit", "Quit"),
            ]),
        ]
        for title, rows in groups:
            table = Table(title=title, header_style="bold #0d9488",
                          border_style="#115e59", padding=(0, 2))
            table.add_column("Command", style="bold #2dd4bf", min_width=44)
            table.add_column("Description")
            for cmd, desc in rows:
                table.add_row(cmd, desc)
        console.print(table)
        console.print(
            "[dim]Enter sends · Alt+Enter / Ctrl+J newline · Tab completes "
            "(2–3 levels)[/]"
        )

    
    def handle_command(self, raw: str) -> bool:
        cmd = raw.strip()
        parts = cmd.split()
        head = parts[0].lower() if parts else ""

        
        if head in ("/exit", "/quit", "/q"):
            console.print("[dim]Goodbye.[/]")
            return False
        if head in ("/help", "/h", "/?"):
            self.cmd_help()
            return True
        if head == "/version":
            console.print(f"{APP_NAME} [accent]v{__version__}[/]")
            return True
        if head == "/settings":
            console.print(
                "[info]The interactive settings screen was replaced by flat slash "
                "commands — everything lives in /help.[/]"
            )
            self.cmd_help()
            return True
        if head == "/thinking":
            self.thinking_enabled = (not self.thinking_enabled) if len(parts) == 1 \
                else parts[1].lower() in ("on", "1", "true", "yes")
            self.cfg["thinking"] = self.thinking_enabled
            save_config(self.cfg)
            console.print(f"Thinking: {'[success]on[/]' if self.thinking_enabled else '[dim]off[/]'}")
            return True
        if head in ("/search", "/websearch", "/web"):
            self.search_enabled = (not self.search_enabled) if len(parts) == 1 \
                else parts[1].lower() in ("on", "1", "true", "yes")
            self.cfg["search"] = self.search_enabled
            save_config(self.cfg)
            console.print(f"Web search: {'[success]on[/]' if self.search_enabled else '[dim]off[/]'}")
            return True
        if head == "/model":
            return self._cmd_model(parts)
        if head == "/debug":
            self.debug = (not self.debug) if len(parts) == 1 \
                else parts[1].lower() in ("on", "1", "true", "yes")
            self.cfg["debug"] = self.debug
            save_config(self.cfg)
            console.print(f"Debug: {'[warning]on[/]' if self.debug else '[dim]off[/]'}")
            return True
        if head == "/token":
            return self._cmd_token(parts)
        if head == "/provider":
            return self._cmd_provider(parts)
        if head == "/autonomy":
            return self._cmd_autonomy(parts)
        if head == "/agent":
            return self._cmd_agent(parts)
        if head == "/skills":
            self._cmd_skills_list()
            return True
        if head == "/skill":
            return self._cmd_skill(parts, cmd)
        if head == "/mcp":
            return self._cmd_mcp(parts, cmd)
        if head in ("/mcp-help", "/mcphelp"):
            self.cmd_mcp_help()
            return True
        if head == "/deps":
            return self._cmd_deps(parts)
        if head == "/sessions":
            self.cmd_sessions()
            return True
        if head == "/new":
            self.new_session()
            return True
        if head == "/use":
            if len(parts) >= 2 and self._session_index:
                self.action_use(parts[1])
            else:
                console.print("[warning]Usage: /use <#|id> (see /sessions)[/]")
            return True
        if head == "/rename":
            self.action_rename(cmd[len("/rename"):].strip())
            return True
        if head == "/del":
            self.action_delete(parts[1] if len(parts) >= 2 else None)
            return True
        if head == "/notes":
            self.cmd_notes(parts, cmd)
            return True
        if head == "/task":
            self.cmd_task(parts)
            return True
        if head == "/upload":
            self.cmd_upload(parts)
            return True
        if head == "/files":
            self.cmd_files(parts)
            return True
        if head == "/sounds":
            return self._cmd_sounds(parts)
        if head == "/sound":
            return self._cmd_sound_channel(parts, cmd)
        if head == "/prompt":
            return self._cmd_prompt(parts, cmd)
        if head == "/aps":
            return self._cmd_aps(parts)
        if head == "/consent":
            return self._cmd_consent(parts)
        if head == "/visual":
            return self._cmd_visual(parts)
        if head == "/status":
            if len(parts) > 1 and parts[1].lower() == "detail":
                self.status_detail()
            else:
                self.print_status()
            return True
        if head == "/history":
            self.cmd_history()
            return True
        if head == "/save":
            self.cmd_export(parts[1] if len(parts) > 1 else None)
            return True
        if head == "/undo":
            self.cmd_undo()
            return True
        if head == "/retry":
            self.cmd_retry()
            return True
        if head == "/copy":
            self.cmd_copy()
            return True
        if head == "/cc":
            return self._cmd_cc(parts)
        if head == "/paste":
            self.cmd_paste()
            return True
        if head == "/edit":
            return self._cmd_edit(parts, cmd)
        if head == "/update":
            check_on_startup(console, __version__)
            return True
        if head == "/clear":
            console.clear()
            self.print_banner()
            self.print_status()
            return True

        console.print(
            f"[warning]Unknown command:[/] {escape(cmd)} — try [accent]/help[/]."
        )
        return True

    
    def _cmd_model(self, parts: List[str]) -> bool:
        table = Table(border_style="#115e59", header_style="bold #0d9488", title="Models")
        table.add_column("Name", style="accent")
        table.add_column("Description")
        table.add_column("", width=2)
        for name, desc in MODELS.items():
            table.add_row(name, desc, "[success]●[/]" if name == self.model else "")
        console.print(table)
        if len(parts) > 1:
            choice = parts[1].lower()
            if choice not in MODELS:
                console.print(f"[error]Unknown model '{choice}'.[/]")
                return True
            self.model = choice
            self.cfg["model"] = choice
            save_config(self.cfg)
            console.print(f"[success]✓[/] Model set to [accent]{self.model}[/]")
            return True
        return True

    def _cmd_token(self, parts: List[str]) -> bool:
        if len(parts) < 2:
            console.print(
                f"[dim]Current token: {mask(load_token() or '')} "
                f"(source: {token_source()})[/]"
            )
            console.print("[warning]Usage: /token <new-token>[/]")
            return True
        from .config import save_token
        save_token(parts[1].strip())
        self.provider = None
        if self.authenticate() and not self.session_id:
            self.new_session(quiet=True)
        return True

    def _cmd_provider(self, parts: List[str]) -> bool:
        pcfg = self.cfg.get("provider") or {"type": "deepseek"}
        if len(parts) == 1:
            console.print(Panel(
                Text(f"type: {pcfg.get('type')}\n"
                     + (f"base_url: {pcfg.get('base_url')}\n" if pcfg.get("base_url") else "")
                     + (f"model: {pcfg.get('model')}\n" if pcfg.get("model") else ""),
                     style="dim"),
                title="[accent]Provider[/]", title_align="left",
                border_style="#0d9488", padding=(0, 1)))
            console.print(
                "[dim]/provider deepseek · /provider openai <base_url> <model> [api_key][/dim]"
            )
            return True
        kind = parts[1].lower()
        if kind == "deepseek":
            self.cfg["provider"] = {"type": "deepseek"}
            save_config(self.cfg)
            self.provider = None
            self.authenticate()
            return True
        if kind == "openai":
            if len(parts) < 4:
                console.print(
                    "[warning]Usage: /provider openai <base_url> <model> [api_key]\n"
                    "[dim]e.g. /provider openai http://localhost:11434/v1 llama3[/]"
                )
                return True
            pcfg = {
                "type": "openai",
                "base_url": parts[2],
                "model": parts[3],
                "api_key": parts[4] if len(parts) > 4 else "",
            }
            self.cfg["provider"] = pcfg
            save_config(self.cfg)
            self.provider = None
            self.authenticate()
            return True
        console.print("[error]Provider must be 'deepseek' or 'openai'.[/]")
        return True

    
    def _cmd_autonomy(self, parts: List[str]) -> bool:
        if len(parts) == 1:
            table = Table(title="Autonomy modes", border_style="#115e59",
                          header_style="bold #0d9488")
            table.add_column("Mode", style="accent")
            table.add_column("Description")
            table.add_column("", width=2)
            for key, m in AUTONOMY_MODES.items():
                table.add_row(f"{key} — {m['label']}", m["desc"],
                              "[success]●[/]" if key == self.autonomy_mode else "")
            console.print(table)
            console.print("[dim]/autonomy <mode> to switch[/]")
            return True
        key = parts[1].lower()
        if key not in AUTONOMY_MODES:
            console.print(f"[error]Unknown mode '{key}'.[/]")
            return True
        self.autonomy_mode = key
        self.cfg["autonomy"] = key
        if key != "custom":
            self.agent_settings.update(AUTONOMY_MODES[key].get("toggles", {}))
            self.cfg["agent_toggles"] = dict(self.agent_settings)
        save_config(self.cfg)
        console.print(f"[success]✓[/] Autonomy: [accent]{AUTONOMY_MODES[key]['label']}[/]")
        return True

    def _cmd_agent(self, parts: List[str]) -> bool:
        if len(parts) == 1:
            table = Table(title="Agent toggles (APS)", border_style="#115e59",
                          header_style="bold #0d9488")
            table.add_column("Key", style="accent")
            table.add_column("Value")
            table.add_column("Meaning")
            for k in AGENT_SETTINGS_DEFAULTS:
                v = self.agent_settings.get(k, False)
                table.add_row(k, "[success]on[/]" if v else "[dim]off[/]",
                              SETTING_DESCRIPTIONS.get(k, ""))
            console.print(table)
            console.print("[dim]/agent <key> on|off[/]")
            return True
        if len(parts) != 3:
            console.print("[warning]Usage: /agent <key> <on|off>[/]")
            return True
        key, val = parts[1].lower(), parts[2].lower()
        if key not in AGENT_SETTINGS_DEFAULTS:
            console.print(f"[error]Unknown toggle '{key}'. Run /agent for the list.[/]")
            return True
        new = _on_off(val)
        if new is None:
            console.print("[warning]Value must be on or off.[/]")
            return True
        self.agent_settings[key] = new
        if self.autonomy_mode != "custom":
            self.autonomy_mode = "custom"
            self.cfg["autonomy"] = "custom"
        self.cfg["agent_toggles"] = dict(self.agent_settings)
        save_config(self.cfg)
        console.print(
            f"[success]✓[/] [accent]{key}[/] = "
            f"{'[success]on[/]' if new else '[dim]off[/]'} [dim](autonomy mode → Custom)[/]"
        )
        return True

    
    def _cmd_skills_list(self) -> None:
        ss = list_skills()
        if not ss:
            console.print("[dim]No skills yet. /skill add to create one; the model "
                          "writes them with skill_write.[/]")
            return
        table = Table(title="Skills", border_style="#115e59",
                      header_style="bold #0d9488")
        table.add_column("Name", style="accent")
        table.add_column("Active", justify="right")
        table.add_column("Versions", justify="right")
        table.add_column("Description")
        for s in ss:
            table.add_row(s["name"], f"v{s.get('version', 1)}",
                          str(s.get("versions", 1)),
                          str(s.get("description", ""))[:60])
        console.print(table)

    def _cmd_skill(self, parts: List[str], cmd: str) -> bool:
        if len(parts) < 2:
            console.print("[warning]Usage: /skill show|diff|rollback|delete|add …[/]")
            return True
        sub = parts[1].lower()
        if sub == "add":
            name = Prompt.ask("Skill name").strip()
            if not name: return True
            desc = Prompt.ask("One-line description", default="").strip()
            console.print("[dim]Enter content lines — finish with a lone '.'[/]")
            lines: List[str] = []
            while True:
                try:
                    line = Prompt.ask("skill│")
                except (KeyboardInterrupt, EOFError):
                    break
                if line.strip() == ".": break
                lines.append(line)
            content = "\n".join(lines).strip()
            if not content:
                console.print("[warning]Empty content — nothing saved.[/]")
                return True
            meta = write_skill(name, content, description=desc or None,
                               note="written from the terminal")
            console.print(f"[success]✓[/] Saved skill [accent]{meta['name']}[/] v{meta['version']}")
            return True
        if len(parts) < 3:
            console.print(f"[warning]Usage: /skill {sub} <name> […][/]")
            return True
        name = parts[2]
        if sub == "show":
            meta, content = read_skill(name)
            if not meta:
                console.print(f"[error]Skill '{name}' not found.[/]")
                return True
            console.print(Panel(
                Text(content),
                title=f"[accent]{meta['name']} · v{meta.get('version')}[/]",
                title_align="left", border_style="#0d9488", padding=(0, 1)))
            return True
        if sub == "diff":
            try:
                va, vb = int(parts[3]), int(parts[4])
            except (IndexError, ValueError):
                console.print("[warning]Usage: /skill diff <name> <vA> <vB>[/]")
                return True
            ok, text = diff_skills(name, va, vb)
            console.print(Text(text, style="dim" if ok else "error"))
            return True
        if sub == "rollback":
            try:
                v = int(parts[3])
            except (IndexError, ValueError):
                console.print("[warning]Usage: /skill rollback <name> <version>[/]")
                return True
            ok, msg = rollback_skill(name, v)
            console.print(f"{'[success]✓[/]' if ok else '[error]✗[/]'} {msg}")
            return True
        if sub == "delete":
            if Confirm.ask(f"Delete skill '{name}' and ALL versions?", default=False):
                if delete_skill(name):
                    console.print(f"[success]✓[/] Deleted '{name}'")
                else:
                    console.print(f"[error]Skill '{name}' not found.[/]")
            return True
        console.print("[warning]Unknown /skill subcommand.[/]")
        return True

    
    def _cmd_mcp(self, parts: List[str], cmd: str) -> bool:
        sub = parts[1].lower() if len(parts) > 1 else "status"
        if sub in ("status", "list", "tools"):
            servers = self.mcp.list_servers()
            console.print(
                f"[mcp]MCP servers[/]: {len(servers)}   "
                f"[mcp]tools loaded[/]: {len(self.mcp.tools)}"
            )
            for name, cfg in servers.items():
                deps = ", ".join(cfg.get("dependencies") or []) or "none"
                console.print(
                    f"  [accent]{name}[/] [dim]{cfg.get('command')} "
                    f"{' '.join(cfg.get('args') or [])}[/] [dim]· deps: {deps}[/]"
                )
            for t in self.mcp.tools:
                console.print(f"  ⚙ [accent]{t['name']}[/] [dim]({t['server']}): "
                              f"{t['description'][:70]}[/]")
            return True
        if sub == "add":
            if len(parts) < 4:
                console.print("[warning]Usage: /mcp add <name> <command> [args…]\n"
                              "[dim]Then optionally: /mcp deps <name> <pkg1,pkg2>[/]")
                return True
            name = parts[2]
            command = parts[3]
            try:
                argv = shlex.split(" ".join(parts[4:]))
            except ValueError:
                argv = list(parts[4:])
            self.mcp.add_server(name, command, argv)
            console.print(f"[success]✓[/] Added [accent]{name}[/] — run /mcp refresh to load tools")
            return True
        if sub == "remove":
            if len(parts) < 3:
                console.print("[warning]Usage: /mcp remove <name>[/]")
                return True
            if self.mcp.remove_server(parts[2]):
                console.print(f"[success]✓[/] Removed [accent]{parts[2]}[/]")
            else:
                console.print(f"[error]Server '{parts[2]}' not found.[/]")
            return True
        if sub == "refresh":
            import asyncio
            from .mcp import MCP_AVAILABLE
            if not MCP_AVAILABLE:
                console.print("[error]MCP SDK missing — pip install mcp[/]")
                return True
            with console.status("[mcp]Loading MCP tools…[/]", spinner="dots"):
                tools = self._mcp_loop.run_until_complete(self.mcp.refresh_tools())
            self._next_tools_reminder_at = min(
                self._next_tools_reminder_at, len(self.messages) + 1)
            console.print(f"[success]✓[/] Loaded {len(tools)} MCP tools")
            return True
        if sub == "deps":
            if len(parts) < 4:
                console.print("[warning]Usage: /mcp deps <server> <pkg1,pkg2>[/]")
                return True
            pkgs = [p.strip() for p in parts[3].split(",") if p.strip()]
            if self.mcp.set_dependencies(parts[2], pkgs):
                console.print(f"[success]✓[/] Dependencies for [accent]{parts[2]}[/]: "
                              f"{', '.join(pkgs) or '(cleared)'}")
            else:
                console.print(f"[error]Server '{parts[2]}' not found.[/]")
            return True
        console.print("[warning]Usage: /mcp [status|add|remove|refresh|deps][/]")
        return True

    def _cmd_deps(self, parts: List[str]) -> bool:
        if len(parts) >= 3 and parts[1].lower() == "auto":
            val = _on_off(parts[2])
            if val is None:
                console.print("[warning]Usage: /deps auto on|off[/]")
                return True
            self.cfg["auto_install_deps"] = val
            save_config(self.cfg)
            console.print(
                f"[success]✓[/] Auto-install dependencies: "
                f"{'[success]on[/] — installs run without asking' if val else '[dim]off[/] — you approve each install'}"
            )
            return True
        if len(parts) >= 2 and parts[1].lower() == "check":
            targets = self.mcp.list_servers()
            if len(parts) >= 3:
                targets = {k: v for k, v in targets.items() if k == parts[2]}
            any_missing = False
            for name, cfg in targets.items():
                missing = packages_missing(cfg.get("dependencies") or [])
                if missing:
                    any_missing = True
                    console.print(f"  [accent]{name}[/]: missing {', '.join(missing)}")
            if not any_missing:
                console.print("[success]✓[/] All MCP dependencies satisfied")
            return True
        console.print(
            f"[dim]Auto-install deps: "
            f"{'on' if self.cfg.get('auto_install_deps') else 'off'}[/]"
        )
        console.print("[warning]Usage: /deps auto on|off · /deps check [server][/]")
        return True

    
    def action_use(self, ident: str) -> None:
        sid = None
        if ident.isdigit():
            try:
                sid = self._session_index[int(ident) - 1]
            except (ValueError, IndexError):
                console.print("[error]Invalid session number.[/]")
                return
        else:
            for s in self._session_index:
                if s == ident or s.startswith(ident):
                    sid = s
                    break
        if sid is None:
            console.print("[error]Session not found.[/]")
            return
        self._apply_session(sid)
        console.print(f"[success]✓[/] Resumed [accent]{sid[:12]}…[/] "
                      f"({len(self.messages)} local messages)")

    def action_rename(self, title: str) -> None:
        if not title or not self.session_id:
            console.print("[warning]Rename needs an active session and a title.[/]")
            return
        self.session_title = title
        try:
            if self.provider:
                self.provider.rename_session(self.session_id, title)
        except (DeepSeekError, Exception) as e:
            console.print(f"[warning]Remote rename failed ({e}); saved locally.[/]")
        self._save_transcript()
        console.print(f"[success]✓[/] Renamed to [accent]{title}[/]")

    def action_delete(self, ident: Optional[str]) -> None:
        if ident:
            sid = None
            if ident.isdigit() and self._session_index:
                try:
                    sid = self._session_index[int(ident) - 1]
                except (ValueError, IndexError):
                    console.print("[error]Invalid session number.[/]")
                    return
            else:
                for s in self._session_index:
                    if s == ident or s.startswith(ident):
                        sid = s
                        break
            if sid is None:
                console.print("[error]Session not found.[/]")
                return
        else:
            sid = self.session_id or ""
            if not sid:
                console.print("[error]No session selected.[/]")
                return
        if not Confirm.ask(f"Delete session [accent]{sid[:12]}…[/]?", default=False):
            return
        try:
            if self.provider:
                self.provider.delete_session(sid)
        except Exception as e:
            console.print(f"[warning]Remote delete failed: {e}[/]")
        p = transcript_path(sid)
        if p.exists():
            p.unlink()
        if sid == self.session_id:
            self.session_id = None
            self.messages.clear()
            self.parent_message_id = None
            self._session_index = []
        console.print("[success]✓[/] Deleted")

    
    def _sounds_cfg(self):
        from .config import DEFAULT_SOUNDS
        return self.cfg.setdefault("sounds", {
            "master": False,
            **{k: dict(v) if isinstance(v, dict) else v
               for k, v in DEFAULT_SOUNDS.items() if k != "master"},
        })

    def _cmd_sounds(self, parts: List[str]) -> bool:
        sc = self._sounds_cfg()
        if len(parts) >= 3 and parts[1].lower() == "master":
            val = _on_off(parts[2])
            if val is None:
                console.print("[warning]Usage: /sounds master on|off[/]")
                return True
            sc["master"] = val
            save_config(self.cfg)
            console.print(f"[success]✓[/] Master sounds: "
                          f"{'[success]on[/]' if val else '[dim]off[/]'}")
            return True
        table = Table(title="Sounds", border_style="#115e59",
                      header_style="bold #0d9488")
        table.add_column("Channel", style="accent")
        table.add_column("Enabled")
        table.add_column("Preset")
        table.add_column("File", style="dim")
        for ch in ("notify", "response", "blank"):
            conf = sc.get(ch, {})
            table.add_row(
                ch,
                "[success]on[/]" if conf.get("enabled", True) else "[dim]off[/]",
                conf.get("preset", "blip"),
                conf.get("file", "") or "—",
            )
        console.print(table)
        console.print(
            f"[dim]Master: {'on' if sc.get('master') else 'off'} — "
            f"/sounds master on|off · /sound <channel> …[/]"
        )
        return True

    def _cmd_sound_channel(self, parts: List[str], cmd: str) -> bool:
        channels = ("notify", "response", "blank")
        if len(parts) < 2 or parts[1].lower() not in channels:
            console.print("[warning]Usage: /sound <notify|response|blank> "
                          "[on|off|preset <name>|file <path>|test][/]")
            return True
        sc = self._sounds_cfg()
        ch = parts[1].lower()
        conf = sc.setdefault(ch, {"enabled": True, "preset": "blip", "file": ""})
        sub = parts[2].lower() if len(parts) > 2 else ""
        if sub == "test":
            play_sound(ch)
            console.print(f"[dim]Playing '{ch}'…[/]")
            return True
        if _on_off(sub) is not None and len(parts) == 3:
            conf["enabled"] = _on_off(sub)
            save_config(self.cfg)
            console.print(f"[success]✓[/] {ch}: "
                          f"{'[success]on[/]' if conf['enabled'] else '[dim]off[/]'}")
            return True
        if sub == "preset" and len(parts) >= 4:
            preset = parts[3].lower()
            if preset not in SOUND_PRESETS and preset != "custom":
                console.print(f"[error]Preset must be one of: "
                              f"{', '.join(list(SOUND_PRESETS) + ['custom'])}[/]")
                return True
            conf["preset"] = preset
            save_config(self.cfg)
            console.print(f"[success]✓[/] {ch} preset → {preset}")
            return True
        if sub == "file" and len(parts) >= 4:
            conf["preset"] = "custom"
            conf["file"] = " ".join(parts[3:])
            save_config(self.cfg)
            console.print(f"[success]✓[/] {ch} custom file → {conf['file']}")
            return True
        console.print("[warning]Usage: /sound <channel> [on|off|preset <name>|file <path>|test][/]")
        return True

    
    def _cmd_prompt(self, parts: List[str], cmd: str) -> bool:
        sub = parts[1].lower() if len(parts) > 1 else "show"
        segs = self.get_segments()

        if sub == "stack":
            if not segs:
                console.print("[dim]No prompt segments to stack.[/]")
                return True
            for i, s in enumerate(segs, 1):
                console.print(f"[accent]{i}[/] {str(s.get('text', ''))[:80]}")
            sel_str = Prompt.ask("Select segments to combine (e.g. 1,3,5)")
            indices = []
            for part in sel_str.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(segs):
                        indices.append(idx)
            if not indices:
                console.print("[warning]No valid segments selected.[/]")
                return True
            combined = "\n".join(str(segs[i].get("text", "")).strip() for i in indices)
            console.print(Panel(Text(combined[:600] + ("…" if len(combined) > 600 else ""), style="system"), title="[accent]Combined Preview[/]", border_style="#115e59"))
            if Confirm.ask("Replace active prompt with this combined stack?", default=True):
                self.save_segments([{"text": combined, "show_tools": True}])
                console.print("[success]✓[/] Prompt replaced with combined stack.")
            return True

        if sub in ("show", "list"):
            if not segs:
                console.print("[dim]No prompt segments. /prompt add <text> to create one.[/]")
                return True
            for i, s in enumerate(segs, 1):
                tools = "[success]tools[/]" if s.get("show_tools", True) else "[dim]no-tools[/]"
                body = str(s.get("text", ""))
                console.print(Panel(
                    Text(body[:600] + ("…" if len(body) > 600 else ""), style="system"),
                    title=f"[accent]{i}[/] · {tools}",
                    title_align="left", border_style="#115e59", padding=(0, 1)))
            console.print("[dim]/prompt add|remove <n>|move <n> up|down|edit <n> <text>|"
                          "tools <n> on|off|clear|save <name>|load <name>|stack[/]")
            return True

        if sub == "add":
            text = cmd.partition("add")[2].strip()
            if not text:
                console.print("[warning]Usage: /prompt add <text>[/]")
                return True
            segs.append({"text": text, "show_tools": True})
            self.save_segments(segs)
            console.print(f"[success]✓[/] Segment {len(segs)} added")
            return True

        if sub == "clear":
            self.save_segments([])
            self.session_notes = []
            console.print("[success]✓[/] All prompt segments and session context cleared.")
            return True

        if sub == "save":
            if len(parts) < 3:
                console.print("[warning]Usage: /prompt save <name>[/]")
                return True
            joined = self.system_prompt
            if not joined:
                console.print("[warning]Nothing to save.[/]")
                return True
            (PROMPTS_DIR / f"{parts[2]}.txt").write_text(joined, encoding="utf-8")
            console.print(f"[success]✓[/] Saved prompt library entry [accent]{parts[2]}[/]")
            return True

        if sub == "load":
            if len(parts) < 3:
                console.print("[warning]Usage: /prompt load <name>[/]")
                return True
            path = PROMPTS_DIR / f"{parts[2]}.txt"
            if not path.exists():
                names = ", ".join(p.stem for p in PROMPTS_DIR.glob("*.txt")) or "none"
                console.print(f"[error]Prompt '{parts[2]}' not found. Saved: {names}[/]")
                return True
            self.save_segments([{"text": path.read_text(encoding="utf-8"),
                                 "show_tools": True}])
            console.print(f"[success]✓[/] Loaded [accent]{parts[2]}[/] as a single segment")
            return True

        
        if sub in ("remove", "move", "edit", "tools"):
            if len(parts) < 3 or not parts[2].isdigit():
                console.print(f"[warning]Usage: /prompt {sub} <n> […][/]")
                return True
            idx = int(parts[2]) - 1
            if idx < 0 or idx >= len(segs):
                console.print("[error]Segment number out of range.[/]")
                return True
            if sub == "remove":
                segs.pop(idx)
                self.save_segments(segs)
                console.print(f"[success]✓[/] Segment {idx + 1} removed")
                return True
            if sub == "move":
                direction = parts[3].lower() if len(parts) > 3 else ""
                if direction == "up" and idx > 0:
                    segs[idx - 1], segs[idx] = segs[idx], segs[idx - 1]
                elif direction == "down" and idx < len(segs) - 1:
                    segs[idx + 1], segs[idx] = segs[idx], segs[idx + 1]
                else:
                    console.print("[warning]Usage: /prompt move <n> up|down[/]")
                    return True
                self.save_segments(segs)
                console.print(f"[success]✓[/] Segment {idx + 1} moved {direction}")
                return True
            if sub == "edit":
                text = cmd.partition(str(parts[2]))[2].strip()
                if not text:
                    console.print("[warning]Usage: /prompt edit <n> <new text>[/]")
                    return True
                segs[idx]["text"] = text
                self.save_segments(segs)
                console.print(f"[success]✓[/] Segment {idx + 1} updated")
                return True
            if sub == "tools":
                val = _on_off(parts[3]) if len(parts) > 3 else None
                if val is None:
                    console.print("[warning]Usage: /prompt tools <n> on|off[/]")
                    return True
                segs[idx]["show_tools"] = val
                self.save_segments(segs)
                console.print(f"[success]✓[/] Segment {idx + 1} MCP tool visibility: "
                              f"{'[success]on[/]' if val else '[dim]off[/]'}")
                return True

        console.print("[warning]Usage: /prompt show|add|remove|move|edit|tools|clear|save|load|stack[/]")
        return True

    
    def _cmd_aps(self, parts: List[str]) -> bool:
        sub = parts[1].lower() if len(parts) > 1 else "show"
        if sub == "show":
            from rich.markdown import Markdown
            console.print(Panel(
                Markdown(aps_guide.load_guide()),
                title="[accent]Abyssal Proposal System (APS) — guide[/]",
                title_align="left", border_style="#0d9488", padding=(0, 1)))
            console.print(f"[dim]File: {aps_guide.APS_GUIDE_FILE} · "
                          f"/aps edit · /aps reset · /aps backups · /aps restore <n>[/]")
            return True
        if sub == "edit":
            if aps_guide.edit_guide():
                console.print("[success]✓[/] APS guide edited (backup saved)")
            else:
                console.print("[error]Could not launch an editor. Set $EDITOR.[/]")
            return True
        if sub == "reset":
            aps_guide.reset_guide()
            console.print("[success]✓[/] APS guide reset to the built-in default (backup saved)")
            return True
        if sub == "backups":
            backups = aps_guide.list_backups()
            if not backups:
                console.print("[dim]No backups yet.[/]")
                return True
            for i, b in enumerate(backups, 1):
                console.print(f"  [dim]{i}.[/] {b.name}")
            console.print("[dim]/aps restore <n>[/]")
            return True
        if sub == "restore":
            if len(parts) < 3:
                console.print("[warning]Usage: /aps restore <n|filename>[/]")
                return True
            path = aps_guide.restore_backup(parts[2])
            if path:
                console.print(f"[success]✓[/] Restored from [accent]{path.name}[/]")
            else:
                console.print("[error]Backup not found.[/]")
            return True
        console.print("[warning]Usage: /aps show|edit|reset|backups|restore <n>[/]")
        return True

    
    def _cmd_consent(self, parts: List[str]) -> bool:
        data = consent.load_consent()
        sub = parts[1].lower() if len(parts) > 1 else "list"
        if sub == "list":
            table = Table(title="APS feature consent", border_style="#115e59",
                          header_style="bold #0d9488")
            table.add_column("Feature", style="accent")
            table.add_column("State")
            table.add_column("Description")
            for key, desc in consent.FEATURES.items():
                v = data.get(key)
                state = ("[success]consented[/]" if v is True
                         else "[error]denied[/]" if v == "denied"
                         else "[dim]not asked yet[/]")
                table.add_row(key, state, desc[:64])
            console.print(table)
            console.print(f"[dim]File: {CONSENT_FILE} · /consent set <key> on|off · "
                          f"/consent reset[/]")
            return True
        if sub == "set":
            if len(parts) < 4:
                console.print("[warning]Usage: /consent set <key> on|off[/]")
                return True
            key = parts[2].lower()
            if key not in consent.FEATURES:
                console.print(f"[error]Unknown feature '{key}'.[/]")
                return True
            val = _on_off(parts[3])
            if val is None:
                console.print("[warning]Value must be on or off.[/]")
                return True
            data[key] = val
            consent.save_consent(data)
            console.print(f"[success]✓[/] Consent [accent]{key}[/] = "
                          f"{'[success]on[/]' if val else '[dim]off (will ask again)[/]'}")
            return True
        if sub == "reset":
            consent.save_consent({k: False for k in consent.FEATURES})
            console.print("[success]✓[/] All consent reset — you will be asked again on first use")
            return True
        console.print("[warning]Usage: /consent [list|set <key> on|off|reset][/]")
        return True

    
    def _cmd_visual(self, parts: List[str]) -> bool:
        vis = self.visual()
        if len(parts) == 1:
            table = Table(title="Visual settings (UI chrome only)",
                          border_style="#115e59", header_style="bold #0d9488")
            table.add_column("Key", style="accent")
            table.add_column("Value")
            table.add_column("Choices")
            for k, v in vis.items():
                choices = ", ".join(VISUAL_CHOICES[k]) if k in VISUAL_CHOICES else \
                    ("hex color" if k == "accent" else "seconds" if k == "flash" else "")
                table.add_row(k, str(v), choices)
            console.print(table)
            console.print("[dim]/visual set <key> <value>[/]")
            return True
        if parts[1].lower() == "set" and len(parts) >= 4:
            key, value = parts[2].lower(), parts[3]
            try:
                norm = validate_visual(key, value)
            except ValueError as e:
                console.print(f"[error]{e}[/]")
                return True
            self.cfg.setdefault("visual", {})[key] = norm
            save_config(self.cfg)
            if key == "accent":
                apply_visual_theme(self.cfg)
            console.print(f"[success]✓[/] visual [accent]{key}[/] = {norm}")
            return True
        console.print("[warning]Usage: /visual · /visual set <key> <value>[/]")
        return True

    
    def cmd_paste(self) -> None:
        data = clipboard.paste()
        if data:
            self._next_prompt_default = data
            console.print("[success]✓[/] Clipboard loaded — it will pre-fill your next prompt.")
        else:
            console.print("[warning]Could not read clipboard. Please paste manually.[/]")

    def cmd_copy(self) -> None:
        last_assistant = next((m for m in reversed(self.messages) if m["role"] == "assistant"), None)
        if not last_assistant:
            console.print("[dim]No assistant message to copy.[/]")
            return
        text = last_assistant.get("content", "")
        if clipboard.copy(text):
            console.print("[success]✓[/] Copied last response to clipboard.")
        else:
            console.print("[error]Failed to copy to clipboard.[/]")

    def _cmd_cc(self, parts: List[str]) -> bool:
        from .codeblocks import CODE_BLOCKS
        blocks = CODE_BLOCKS._blocks
        if not blocks:
            console.print("[dim]No code blocks in the current message.[/]")
            return True
        if len(parts) < 2:
            console.print("Code blocks: " + ", ".join(f"#{b}" for b in sorted(blocks))
                          + " — /cc <n> to copy")
            return True
        try:
            bid = int(parts[1])
        except ValueError:
            console.print("[warning]Usage: /cc <block#>[/]")
            return True
        ok, label = CODE_BLOCKS.copy(bid)
        style = "success" if ok else "warning"
        console.print(f"[{style}]⧉ code block {bid} — {label}[/]")
        return True

    def cmd_retry(self) -> None:
        last_user = next((m for m in reversed(self.messages) if m["role"] == "user"), None)
        if not last_user:
            console.print("[dim]No user message to retry.[/]")
            return
        console.print(f"[info]Retrying:[/] {last_user['content'][:60]}...")
        idx = len(self.messages) - 1 - self.messages[::-1].index(last_user)
        self.messages = self.messages[:idx]
        if self.messages:
            last_assistant = next((m for m in reversed(self.messages) if m["role"] == "assistant"), None)
            if last_assistant:
                self.parent_message_id = last_assistant.get("server_id") or last_assistant.get("message_id")
            else:
                self.parent_message_id = None
        else:
            self.parent_message_id = None
        self.stream_response(last_user["content"])

    def _cmd_edit(self, parts: List[str], cmd: str) -> bool:
        if len(parts) < 3 or not parts[1].isdigit():
            console.print("[warning]Usage: /edit <message#> <new text>[/]")
            return True
        msg_number = int(parts[1])
        new_text = cmd.partition(str(parts[1]))[2].strip()
        self.cmd_edit(msg_number, new_text)
        return True

    def cmd_edit(self, msg_number: int, new_text: str) -> None:
        msg_idx = msg_number - 1
        if msg_idx < 0 or msg_idx >= len(self.messages):
            console.print("[error]Message number out of range.[/]")
            return
        msg = self.messages[msg_idx]
        if msg["role"] != "user":
            console.print("[warning]Can only edit user messages.[/]")
            return
        if not new_text:
            console.print("[warning]Empty text.[/]")
            return
        msg_id = msg.get("message_id") or msg.get("server_id")
        edit_fn = getattr(self.provider, "edit_message", None)
        if not msg_id or not self.provider or edit_fn is None:
            
            self.messages = self.messages[:msg_idx]
            self.parent_message_id = None
            self.stream_response(new_text)
            return
        try:
            edit_fn(self.session_id, msg_id, new_text,
                    self.thinking_enabled, self.search_enabled)
        except Exception as e:
            console.print(f"[error]Edit failed: {e}[/]")
            return
        self.messages = self.messages[:msg_idx]
        if self.messages:
            last_assistant = next((m for m in reversed(self.messages) if m["role"] == "assistant"), None)
            if last_assistant:
                self.parent_message_id = last_assistant.get("server_id") or last_assistant.get("message_id")
            else:
                self.parent_message_id = None
        else:
            self.parent_message_id = None
        self.stream_response(new_text)

    def cmd_undo(self) -> None:
        last_user_idx = -1
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i]["role"] == "user":
                last_user_idx = i
                break
        if last_user_idx == -1:
            console.print("[dim]Nothing to undo.[/]")
            return
        self.messages = self.messages[:last_user_idx]
        if self.messages:
            last_assistant = next((m for m in reversed(self.messages) if m["role"] == "assistant"), None)
            if last_assistant:
                self.parent_message_id = last_assistant.get("server_id") or last_assistant.get("message_id")
            else:
                self.parent_message_id = None
        else:
            self.parent_message_id = None
        self._save_transcript()
        console.print("[success]✓[/] Undo successful.")

    def cmd_history(self) -> None:
        if not self.messages:
            console.print("[dim]No messages in this session yet.[/]")
            return
        for i, m in enumerate(self.messages, 1):
            if m["role"] == "tool":
                console.print(f"[mcp]{i}. Tool[/]: {m.get('tool')} → {str(m.get('result', ''))[:100]}")
                continue
            role, style = ("You", "user") if m["role"] == "user" else ("Abyssal", "accent")
            preview = m["content"][:140].replace("\n", " ")
            console.print(f"[{style}]{i}. {role}[/]: {preview}{'…' if len(m['content']) > 140 else ''}")

    def cmd_export(self, name: Optional[str] = None) -> None:
        if not self.messages:
            console.print("[dim]Nothing to export yet.[/]")
            return
        name = name or datetime.now().strftime("abyssal_%Y%m%d_%H%M%S")
        path = Path.cwd() / f"{name}.md"
        lines = [
            f"# Abyssal conversation — {self.session_title or self.session_id or 'untitled'}",
            "",
            f"_Exported {datetime.now().isoformat()}_",
            "",
        ]
        for m in self.messages:
            role = {
                "user": "**You**",
                "assistant": "**Abyssal**",
                "tool": "**Tool**",
            }.get(m["role"], m["role"])
            lines.append(f"## {role}\n{m.get('content', m.get('result', ''))}\n")
        path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[success]✓[/] Exported → [accent]{path}[/]")

    def status_detail(self) -> None:
        self.print_status()
        _tasks = load_tasks()
        _pend = sum(1 for t in _tasks if t.get("status") == "pending")
        agent_state = ", ".join(
            f"{k}={'on' if v else 'off'}" for k, v in self.agent_settings.items())
        consent_state = ", ".join(
            f"{k}={'on' if v is True else 'denied' if v == 'denied' else '?'}"
            for k, v in consent.load_consent().items())
        pcfg = self.cfg.get("provider") or {}
        console.print(
            f"  [dim]provider[/]: {pcfg.get('type', 'deepseek')}"
            + (f" ({pcfg.get('base_url')})" if pcfg.get("base_url") else "") + "\n"
            f"  [dim]token[/]: {mask(load_token() or '')}  [dim](source: {token_source()})[/]\n"
            f"  [dim]autonomy mode[/]: {self.autonomy_mode}\n"
            f"  [dim]prompt segments[/]: {len(self.get_segments())}\n"
            f"  [dim]messages this session[/]: {len(self.messages)}\n"
            f"  [dim]next MCP reference re-injection[/]: at message {self._next_tools_reminder_at}\n"
            f"  [dim]scheduled tasks[/]: {len(_tasks)} total ({_pend} pending)\n"
            f"  [dim]session notes[/]: {len(self.session_notes)}\n"
            f"  [dim]pending uploaded files[/]: {len(self.pending_file_ids)}\n"
            f"  [dim]agent toggles[/]: {agent_state}\n"
            f"  [dim]consent[/]: {consent_state}\n"
            f"  [dim]visual[/]: {self.visual()}\n"
            f"  [dim]auto-install deps[/]: {self.cfg.get('auto_install_deps', False)}\n"
            f"  [dim]config[/]: {CONFIG_FILE}"
        )