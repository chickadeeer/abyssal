from __future__ import annotations

import asyncio
import difflib
import re
import sys
import uuid
from typing import Any, Dict, List, Tuple

from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from . import consent
from .agent import (
    AGENT_SETTINGS_DEFAULTS,
    SETTING_DESCRIPTIONS,
    strip_model_control_blocks,
)
from .config import (
    CONFIG_DIR,
    PROMPTS_DIR,
    TOOL_RESULT_MAX_CHARS,
    save_config,
)
from .mcp import MCP_AVAILABLE
from .patching import apply_unified_patch
from .questions import ask_questions, normalize_questions
from .ui import console


class AgentMixin:
    

    def cmd_notes(self, parts: List[str], cmd: str) -> None:
        
        sub = parts[1].lower() if len(parts) > 1 else "list"
        if sub == "add":
            text = cmd.partition("add")[2].strip()
            if not text:
                console.print("[warning]Usage: /notes add <text>[/]")
                return
            self.session_notes.append(text)
            console.print(f"[success]✓[/] Note saved [dim]({len(self.session_notes)} this session)[/]")
        elif sub == "clear":
            n = len(self.session_notes)
            self.session_notes = []
            console.print(f"[success]✓[/] Cleared {n} session note(s)")
        elif sub in ("list", "show"):
            if not self.session_notes:
                console.print("[dim]No session notes.[/]")
                return
            for i, note in enumerate(self.session_notes, 1):
                console.print(f"[dim]{i}.[/] {escape(note)}")
        else:
            console.print("[warning]Usage: /notes [list | add <text> | clear][/]")

    def cmd_mcp_help(self) -> None:
        
        from rich.markdown import Markdown
        console.print(Panel(
            Markdown(self._aps_block()),
            title="[accent]Abyssal Proposal System (APS)[/]",
            title_align="left",
            border_style="#0d9488",
            padding=(0, 1),
        ))
        console.print(Panel(
            Markdown(self.mcp.get_help_block()),
            title="[mcp]MCP tool reference[/]",
            title_align="left",
            border_style="#14b8a6",
            padding=(0, 1),
        ))

    @staticmethod
    def _render_diff_panel(old_code: str, new_code: str, title: str) -> Panel:
        
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile="before", tofile="after", lineterm=""
        )
        diff_text = Text()
        for line in diff:
            if line.startswith("+++") or line.startswith("---"):
                diff_text.append(line.rstrip() + "\n", style="bold dim")
            elif line.startswith("@@"):
                diff_text.append(line.rstrip() + "\n", style="cyan")
            elif line.startswith("+"):
                diff_text.append(line.rstrip() + "\n", style="bold green")
            elif line.startswith("-"):
                diff_text.append(line.rstrip() + "\n", style="bold red")
            else:
                diff_text.append(line.rstrip() + "\n", style="dim")
        return Panel(
            diff_text,
            title=title,
            title_align="left",
            border_style="#0d9488",
            padding=(0, 1),
        )

    
    def _handle_questions(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        if not self.agent_settings.get("allow-model-questions"):
            return False, (
                "Structured questions are disabled. The user can enable them with "
                "/agent allow-model-questions on."
            )
        if not consent.request_consent("questions", console):
            return False, (
                "The user has not consented to structured question forms. They can "
                "grant it with /consent set questions on. Ask in plain prose instead."
            )
        try:
            qs = normalize_questions(data)
        except ValueError as e:
            return False, (
                f"Your [QUESTIONS] block was invalid: {e}. Send a single JSON object "
                "with a 'questions' list; each item needs 'text' and may have "
                "'choices', 'allow_text', 'blocking' and 'default'."
            )
        return True, ask_questions(qs)

    
    def _handle_mcp_proposal(self, prop: Dict[str, Any]) -> Tuple[bool, str]:
        
        name = str(prop.get("name") or "").strip() or f"plugin_{uuid.uuid4().hex[:6]}"
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:48] or "plugin"
        reason = str(prop.get("reason") or "(no reason given)").strip()
        code = str(prop.get("code") or "")
        command = str(prop.get("command") or "").strip()
        args = prop.get("args") or []
        if not isinstance(args, list):
            args = [str(args)]
        deps_raw = prop.get("dependencies") or []
        if not isinstance(deps_raw, list):
            deps_raw = [str(deps_raw)]
        dependencies = [str(d).strip() for d in deps_raw if str(d).strip()]

        if name in self._mcp_rejected_plugins:
            return False, (
                f"MCP plugin '{name}' was already declined by the user this session. "
                "Do not propose it again unless the user asks for it."
            )
        if not self.agent_settings.get("allow-mcp-proposals"):
            return False, (
                "MCP plugin proposals are disabled "
                "(/agent allow-mcp-proposals on to enable)."
            )
        if not consent.request_consent("mcp-proposals", console):
            return False, (
                "The user has not consented to MCP plugin proposals. They can grant "
                "it with /consent set mcp-proposals on."
            )
        if not MCP_AVAILABLE:
            return False, (
                "MCP SDK is not installed in this environment (pip install mcp), "
                "so the proposal cannot be loaded."
            )

        body_parts: List[Any] = [Text(reason, style="dim italic")]
        if dependencies:
            body_parts.append(
                Text(f"pip dependencies: {', '.join(dependencies)} "
                     "(installed with your consent before launch)", style="dim"))
        if code:
            body_parts.append(Syntax(code, "python", line_numbers=True, word_wrap=True))
        elif command:
            body_parts.append(
                Text(f"command: {command} {' '.join(str(a) for a in args)}", style="dim"))

        need_confirm = self.agent_settings.get("confirm-proposals", True)
        if need_confirm:
            console.print(Panel(
                Group(*body_parts),
                title=f"[mcp]Proposed NEW MCP plugin: {escape(name)}[/]",
                title_align="left",
                border_style="#0d9488",
                padding=(0, 1),
            ))
            try:
                choice = Prompt.ask(
                    "Approve this NEW MCP plugin?",
                    choices=["yes", "no", "later"],
                )
            except (KeyboardInterrupt, EOFError):
                choice = "later"
        else:
            choice = "yes"
            console.print(
                f"[mcp]Autonomous mode — auto-approving NEW plugin [accent]{escape(name)}[/]")

        if choice == "later":
            return False, (
                f"The user deferred MCP plugin '{name}'. "
                "You may propose it again later in this session."
            )
        if choice == "no":
            self._mcp_rejected_plugins.add(name)
            return False, (
                f"The user declined MCP plugin '{name}'. "
                "Do not propose it again this session."
            )

        
        if code:
            plugin_dir = CONFIG_DIR / "plugins"
            plugin_dir.mkdir(exist_ok=True)
            path = plugin_dir / f"{safe_name}.py"
            try:
                path.write_text(code, encoding="utf-8")
            except OSError as e:
                return False, f"Could not write plugin file: {e}"
            command, args = sys.executable, [str(path)]
        if not command:
            return False, "The proposal needs either a 'code' field or a 'command' field."

        self.mcp.add_server(name, command, [str(a) for a in args],
                            dependencies=dependencies)
        try:
            with console.status("[mcp]Loading proposed MCP plugin…[/]", spinner="dots"):
                asyncio.run(self.mcp.refresh_tools())
        except Exception as e:
            self.mcp.remove_server(name)
            return False, f"MCP plugin '{name}' failed to load and was removed: {e}"
        self._next_tools_reminder_at = min(
            self._next_tools_reminder_at, len(self.messages) + 1)
        new_tools = [t["name"] for t in self.mcp.tools if t["server"] == name]
        if new_tools:
            return True, (
                f"MCP plugin '{name}' approved and loaded. "
                f"Tools: {', '.join(new_tools)}."
            )
        return True, (
            f"MCP plugin '{name}' approved and registered, "
            "but it exposed no tools (check the server output)."
        )

    def _handle_mcp_edit_proposal(self, prop: Dict[str, Any]) -> Tuple[bool, str]:
        
        name = str(prop.get("name") or "").strip()
        reason = str(prop.get("reason") or "(no reason given)").strip()
        new_code = str(prop.get("code") or "")
        patch = str(prop.get("patch") or "")
        if not name:
            return False, "MCP_EDIT_PROPOSAL requires a 'name' field identifying the plugin to edit."
        if not new_code and not patch:
            return False, (
                "MCP_EDIT_PROPOSAL requires either a 'patch' field (preferred: a unified "
                "diff against the current source, obtained via mcp_read_plugin) or a 'code' "
                "field with the complete updated source."
            )
        if not self.agent_settings.get("allow-mcp-proposals"):
            return False, (
                "MCP plugin proposals (including edits) are disabled "
                "(/agent allow-mcp-proposals on to enable)."
            )
        if not consent.request_consent("mcp-edits", console):
            return False, (
                "The user has not consented to MCP plugin edits. They can grant it "
                "with /consent set mcp-edits on."
            )
        if name in self._mcp_rejected_plugins:
            return False, (
                f"MCP plugin '{name}' was already declined by the user this session. "
                "Do not propose edits to it unless the user asks."
            )
        plugin_path = self.mcp.get_plugin_path(name)
        if plugin_path is None:
            return False, (
                f"Cannot edit '{name}': it is not a Python-based plugin managed by this CLI, "
                "or the source file could not be located."
            )
        try:
            old_code = plugin_path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Could not read current plugin source for '{name}': {e}"

        if patch:
            ok, resolved, err = apply_unified_patch(old_code, patch)
            if not ok:
                return False, err
            new_code = resolved
            edit_kind = "patch"
        else:
            edit_kind = "full rewrite"

        diff_panel = self._render_diff_panel(
            old_code, new_code,
            title=f"[mcp]Proposed EDIT ({edit_kind}): {escape(name)} ({plugin_path.name})[/]",
        )
        need_confirm = self.agent_settings.get("confirm-proposals", True)
        if need_confirm:
            console.print(diff_panel)
            console.print(Text(f"Reason: {reason}", style="dim italic"))
            try:
                choice = Prompt.ask(
                    "Apply this edit to the MCP plugin?",
                    choices=["yes", "no", "later"],
                )
            except (KeyboardInterrupt, EOFError):
                choice = "later"
        else:
            choice = "yes"
            console.print(
                f"[mcp]Autonomous mode — auto-applying edit to [accent]{escape(name)}[/]")

        if choice == "later":
            return False, (
                f"The user deferred the edit to '{name}'. "
                "You may propose it again later in this session."
            )
        if choice == "no":
            self._mcp_rejected_plugins.add(name)
            return False, (
                f"The user declined the edit to '{name}'. "
                "Do not propose edits to it again this session."
            )
        try:
            plugin_path.write_text(new_code, encoding="utf-8")
        except OSError as e:
            return False, f"Could not write updated plugin source for '{name}': {e}"
        try:
            with console.status(f"[mcp]Reloading edited plugin '{name}'…[/]", spinner="dots"):
                asyncio.run(self.mcp.refresh_tools())
        except Exception as e:
            return False, (
                f"Plugin '{name}' was updated on disk but failed to reload: {e}. "
                "The file has been written; you may need to fix and re-propose."
            )
        self._next_tools_reminder_at = min(
            self._next_tools_reminder_at, len(self.messages) + 1)
        new_tools = [t["name"] for t in self.mcp.tools if t["server"] == name]
        if new_tools:
            return True, (
                f"Edit to '{name}' applied and reloaded. "
                f"Tools: {', '.join(new_tools)}."
            )
        return True, (
            f"Edit to '{name}' applied and reloaded, "
            "but it currently exposes no tools."
        )

    def _handle_system_proposal(self, prop: Dict[str, Any]) -> Tuple[bool, str]:
        
        reason = str(prop.get("reason") or "(no reason given)").strip()
        proposed = str(prop.get("prompt") or "").strip()
        if not proposed:
            return False, "SYSTEM_PROPOSAL needs a non-empty 'prompt' field."
        if not self.agent_settings.get("allow-system-proposals"):
            return False, (
                "System-prompt proposals are disabled "
                "(/agent allow-system-proposals on to enable)."
            )
        if not consent.request_consent("system-proposals", console):
            return False, (
                "The user has not consented to system-prompt proposals. They can "
                "grant it with /consent set system-proposals on."
            )
        need_confirm = self.agent_settings.get("confirm-proposals", True)
        if need_confirm:
            body = Group(
                Text(f"Reason: {reason}", style="dim italic"),
                Rule(style="dim"),
                Text(proposed),
            )
            console.print(Panel(
                body,
                title="[system]Proposed system prompt[/]",
                title_align="left",
                border_style="#115e59",
                padding=(0, 1),
            ))
            try:
                choice = Prompt.ask(
                    "Apply this system prompt?",
                    choices=["yes", "no", "later"],
                )
            except (KeyboardInterrupt, EOFError):
                choice = "later"
        else:
            choice = "yes"
            console.print("[system]Autonomous mode — auto-applying system prompt change[/]")

        if choice == "later":
            return False, "The user deferred the system-prompt change. You may ask again later."
        if choice == "no":
            return False, "The user declined the system-prompt change."

        self.save_segments([{"text": proposed, "show_tools": True}])
        return True, (
            "System prompt updated (applies to new conversations; prompt segments "
            "are managed with /prompt). Note: the model can never switch models "
            "mid-conversation."
        )

    def _handle_new_session_request(self, reason: str) -> Tuple[bool, str]:
        
        if not self.agent_settings.get("allow-model-new"):
            return False, (
                "New-session requests are disabled "
                "(/agent allow-model-new on to enable)."
            )
        if not consent.request_consent("new-session", console):
            return False, (
                "The user has not consented to model-requested new sessions. They "
                "can grant it with /consent set new-session on. Continue in this session."
            )
        try:
            ok = Confirm.ask(
                f"[mcp]Model requests a NEW session[/] [dim]({reason or 'no reason given'}). "
                f"Current context will be lost.[/] Allow?",
                default=False,
            )
        except (KeyboardInterrupt, EOFError):
            ok = False
        if not ok:
            return False, "The user declined to start a new session. Continue in this one."
        if not self.new_session():
            return False, "Failed to create a new session."
        return True, (
            "New session created. All previous context is gone; "
            "the APS guide has been re-stated."
        )

    def _handle_needs_input(self, question: str, prior_feedback: str) -> str:
        
        if not consent.request_consent("needs-input", console):
            return (
                prior_feedback + "\n"
                "[HUMAN_RESPONSE]\n"
                "(The user has not consented to model-initiated pauses. Continue "
                "without pausing; they can grant it with /consent set needs-input on.)\n"
                "[/HUMAN_RESPONSE]"
            )
        console.print(Panel(
            Text(
                (question or "The model needs your input.").strip(),
                style="warning",
            ),
            title="[warning]Model paused — human input needed[/]",
            title_align="left",
            border_style="yellow",
            padding=(0, 1),
        ))
        try:
            reply = Prompt.ask("[accent]Your answer[/]").strip()
        except (KeyboardInterrupt, EOFError):
            reply = ""
        self.messages.append({
            "role": "user",
            "content": reply or "(no answer given)",
            "message_id": None,
        })
        parts: List[str] = []
        if prior_feedback:
            parts.append(prior_feedback)
        parts.append(
            f'[HUMAN_RESPONSE to="{(question or "")[:120]}"]\n'
            f"{reply or '(The user gave no answer.)'}\n"
            f"[/HUMAN_RESPONSE]"
        )
        return "\n".join(parts)