from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm
from rich.spinner import Spinner
from rich.text import Text

from . import codeblocks, consent
from .agent import (
    MCP_EDIT_PROPOSAL_RE,
    MCP_PROPOSAL_RE,
    NEEDS_INPUT_RE,
    NEW_SESSION_RE,
    QUESTIONS_RE,
    SYSTEM_PROPOSAL_RE,
    parse_json_blocks,
    parse_plain_blocks,
    strip_model_control_blocks,
)
from .config import (
    BLANK_MAX_RETRIES,
    BLANK_RETRY_SECONDS,
    MAX_TOOL_ITERATIONS,
    RATE_MAX_RETRIES,
    RATE_RETRY_SECONDS,
    TOOL_RESULT_MAX_CHARS,
)
from .mcp import MCP_AVAILABLE, parse_tool_calls
from .skills import (
    diff_skills,
    list_skills,
    read_skill,
    rollback_skill,
    write_skill,
)
from .sounds import play_sound
from .ui import console

try:
    from dsk.api import APIError, AuthenticationError, NetworkError, RateLimitError
except ImportError:
    from api import APIError, AuthenticationError, NetworkError, RateLimitError  


class ChatMixin:
    

    
    def _box(self):
        return box.SQUARE if self.visual().get("border") == "square" else box.ROUNDED

    def _title(self, base: str) -> str:
        ts = self.visual().get("timestamps", "off")
        if ts == "off":
            return base
        fmt = "%H:%M" if ts == "time" else "%Y-%m-%d %H:%M"
        return f"{base} · {datetime.now().strftime(fmt)}"

    
    def _upload_file_tool(self, args: Dict[str, Any]) -> Tuple[bool, str]:
        if not self.provider:
            return False, "Not authenticated. Provide a token/provider via /token or /provider."
        if not getattr(self.provider, "supports_uploads", False):
            return False, (
                f"The '{self.provider.name}' provider does not support file uploads. "
                "Switch with /provider deepseek."
            )
        path_str = str(args.get("path") or "").strip()
        if not path_str:
            return False, "deepseek_upload_file requires arguments: {\"path\": \"...\"}."
        path = Path(path_str).expanduser()
        if not path.exists():
            return False, f"File not found: {path}"
        if not path.is_file():
            return False, f"Not a file: {path}"
        try:
            with console.status(f"[mcp]⚙ Uploading {path.name}…[/]", spinner="dots"):
                file_id = self.provider.upload_file(
                    str(path),
                    model_type=self.model,
                    thinking_enabled=self.thinking_enabled,
                )
        except Exception as e:
            return False, f"Upload failed: {e}"
        self.pending_file_ids.append(file_id)
        self.uploaded_files.append({
            "id": file_id,
            "path": str(path),
            "name": path.name,
            "uploaded_at": datetime.now().isoformat(),
        })
        return True, (
            f"Uploaded file: {path.name}\n"
            f"file_id: {file_id}\n"
            "The file will be attached to the next completion request."
        )

    
    def _read_plugin_tool(self, args: Dict[str, Any]) -> Tuple[bool, str]:
        name = str(args.get("name") or "").strip()
        if not name:
            return False, 'mcp_read_plugin requires arguments: {"name": "plugin_name"}.'
        path = self.mcp.get_plugin_path(name)
        if path is None:
            servers = ", ".join(self.mcp.list_servers()) or "(none)"
            return False, (
                f"Plugin '{name}' not found or not a Python plugin. "
                f"Configured servers: {servers}."
            )
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Could not read plugin source: {e}"
        numbered = "\n".join(
            f"{i:4d} │ {line}" for i, line in enumerate(source.splitlines(), 1))
        return True, (
            f"Source of MCP plugin '{name}' ({path}) — {len(source.splitlines())} lines.\n"
            "To edit surgically, send [MCP_EDIT_PROPOSAL] with a 'patch' field containing a "
            "unified diff against EXACTLY this content.\n" + numbered
        )

    
    def _skill_tool(self, name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        if name == "skills_list":
            ss = list_skills()
            if not ss:
                return True, (
                    "No skills exist yet. Create one with skill_write when you learn "
                    "something reusable for future tasks. You can also search LobeHub "
                    "via the lobehub-skills MCP server."
                )
            return True, "Available skills:\n" + "\n".join(
                f"- {s['name']} (v{s.get('version', 1)}, {s.get('versions', 1)} version(s)): "
                f"{str(s.get('description', ''))[:160]}" for s in ss
            )
        if name == "skill_read":
            skill_name = str(args.get("name") or "").strip()
            if not skill_name:
                return False, 'skill_read requires {"name": "..."}.'
            meta, content = read_skill(skill_name)
            if not meta:
                return False, f"Skill '{skill_name}' not found. Use skills_list to see what exists."
            return True, (
                f"# skill: {meta['name']} — active v{meta.get('version')} "
                f"of {meta.get('versions')}\n"
                f"description: {meta.get('description', '')}\n{content}"
            )
        if name == "skill_diff":
            skill_name = str(args.get("name") or "").strip()
            try:
                va = int(args.get("version_a") or args.get("a") or 0)
                vb = int(args.get("version_b") or args.get("b") or 0)
            except (TypeError, ValueError):
                return False, 'skill_diff requires {"name": "...", "version_a": N, "version_b": M}.'
            ok, text = diff_skills(skill_name, va, vb)
            return ok, text
        if name == "skill_write":
            skill_name = str(args.get("name") or "").strip()
            content = str(args.get("content") or "")
            if not skill_name or not content.strip():
                return False, 'skill_write requires {"name": "...", "content": "..."}.'
            if not consent.request_consent("skill-writes", console):
                return False, (
                    "The user has not consented to skill writes. They can grant it with "
                    "/consent set skill-writes on."
                )
            description = args.get("description")
            note = str(args.get("note") or "").strip()
            existing, _ = read_skill(skill_name)
            verb = "update" if existing else "create"
            if self.agent_settings.get("confirm-proposals", True):
                console.print(Panel(
                    Group(
                        Text(f"skill: {skill_name}  ({verb} → "
                             f"v{(existing or {}).get('versions', 0) + 1})"),
                        Text(str(description or (existing or {}).get("description", "")),
                             style="dim italic"),
                        Text(content[:2000], style="dim"),
                    ),
                    title="[accent]Skill write proposed[/]",
                    title_align="left", border_style="#0d9488",
                    box=self._box(), padding=(0, 1),
                ))
                try:
                    ok = Confirm.ask(f"Write skill '{skill_name}'?", default=True)
                except (KeyboardInterrupt, EOFError):
                    ok = False
                if not ok:
                    return False, f"The user declined to write skill '{skill_name}'."
            meta = write_skill(skill_name, content,
                               description=str(description) if description is not None else None,
                               note=note or "written by the model")
            return True, (
                f"Skill '{meta['name']}' saved as v{meta['version']} "
                f"(active). It will be listed on the first turn of future sessions."
            )
        if name == "skill_rollback":
            skill_name = str(args.get("name") or "").strip()
            try:
                version = int(args.get("version") or 0)
            except (TypeError, ValueError):
                return False, 'skill_rollback requires {"name": "...", "version": N}.'
            if self.agent_settings.get("confirm-proposals", True):
                try:
                    ok = Confirm.ask(
                        f"Roll skill '{skill_name}' back to v{version}?", default=False)
                except (KeyboardInterrupt, EOFError):
                    ok = False
                if not ok:
                    return False, f"The user declined the rollback of '{skill_name}'."
            ok, msg = rollback_skill(skill_name, version)
            return ok, msg
        return False, f"Unknown skill tool '{name}'."

    
    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        
        if name == "mcp_help":
            return True, self.mcp.get_full_block()
        
        if name == "deepseek_upload_file":
            return self._upload_file_tool(args)
        
        if name == "mcp_read_plugin":
            return self._read_plugin_tool(args)
        
        if name in ("skills_list", "skill_read", "skill_write",
                    "skill_rollback", "skill_diff"):
            return self._skill_tool(name, args)
        if not MCP_AVAILABLE:
            return False, "MCP SDK not installed (pip install mcp)."
        try:
            with console.status(f"[mcp]⚙ Running {name}…[/]", spinner="dots"):
                result = asyncio.run(self.mcp.call_tool(name, args))
            return True, result
        except KeyError as e:
            return False, f"{e}. Call mcp_help to see available tools."
        except Exception as e:
            return False, f"Tool execution failed: {e}"

    @staticmethod
    def _tool_result_prompt(results: List[Tuple[str, bool, str]]) -> str:
        blocks = []
        for name, ok, text in results:
            truncated = text[:TOOL_RESULT_MAX_CHARS]
            if len(text) > TOOL_RESULT_MAX_CHARS:
                truncated += "\n…(output truncated)"
            blocks.append(
                f'[TOOL_RESULT tool="{name}" status="{"ok" if ok else "error"}"]\n'
                f"{truncated}\n"
                f"[/TOOL_RESULT]"
            )
        return (
            "\n".join(blocks)
            + "\nProcess these tool results and continue the task. "
            "If you need another tool, call it now using the exact "
            "[TOOL_CALL: name] {json} [/TOOL_CALL] syntax."
        )

    
    def _show_tool_call(self, name: str, args: Dict[str, Any]) -> None:
        mode = self.visual().get("tool_calls", "tab")
        preview = json.dumps(args, ensure_ascii=False)
        if mode == "hidden":
            console.print(f"[dim]▸ tool: {escape(name)} (hidden — /visual set tool_calls tab)[/]")
        elif mode == "raw":
            console.print(f"[mcp]⚙ tool[/]: [accent]{name}[/] [dim]{preview[:120]}[/]")
        elif mode == "inline":
            console.print(f"[mcp]⚙[/] [accent]{escape(name)}[/] [dim]{preview[:120]}[/]")
        else:  
            console.print(Panel(
                Text(preview[:400], style="dim"),
                title=f"[mcp]⚙[/] [accent]{escape(name)}[/]",
                title_align="left", border_style="#14b8a6",
                box=self._box(), padding=(0, 1),
            ))

    def _show_tool_result(self, name: str, ok: bool, result: str) -> None:
        mode = self.visual().get("tool_calls", "tab")
        if mode == "hidden":
            return
        state = "[success]ok[/]" if ok else "[error]error[/]"
        preview = escape(result[:200].replace("\n", " "))
        if len(result) > 200:
            preview += "…"
        console.print(f"[mcp]  ↳[/] {state} [dim]{preview}[/]")

    
    @staticmethod
    def _wait_with_countdown(seconds: int, label: str) -> None:
        try:
            with Live(console=console, refresh_per_second=4, transient=True) as live:
                for remain in range(seconds, 0, -1):
                    live.update(Text(f"⏳ {label} — retrying in {remain}s …",
                                     style="warning"))
                    time.sleep(1)
        except Exception:
            time.sleep(seconds)

    
    def _stream_once(self, prompt: str, ref_file_ids: Optional[List[str]] = None) -> Optional[str]:
        
        vis = self.visual()
        thinking_buf: List[str] = []
        answer_buf: List[str] = []
        search_info: Optional[Dict[str, Any]] = None
        pending_parent: Optional[int] = None
        rate_retries = 0
        blank_retries = 0
        transient_attempt = 0
        max_transient = 10

        def render() -> Group:
            parts: List[Any] = []
            if thinking_buf and vis.get("thinking", "panel") != "hidden":
                think_text = Text("".join(thinking_buf), style="thinking")
                if vis.get("thinking") == "inline":
                    parts.append(think_text)
                else:
                    parts.append(Panel(
                        think_text,
                        title="[thinking]Thinking[/]",
                        title_align="left", border_style="#115e59",
                        box=self._box(), padding=(0, 1),
                    ))
            if search_info and vis.get("search", "inline") != "hidden":
                q = ", ".join(str(x) for x in (search_info.get("queries") or [])) or "…"
                n = len(search_info.get("results") or [])
                line = Text(f"🔍 Searching: {q}  →  {n} results", style="search")
                if vis.get("search") == "panel":
                    parts.append(Panel(line, title="[search]Web search[/]",
                                       title_align="left", border_style="#2dd4bf",
                                       box=self._box(), padding=(0, 1)))
                else:
                    parts.append(line)
            if answer_buf:
                display_answer = strip_model_control_blocks("".join(answer_buf))
                parts.append(Panel(
                    codeblocks.render_group(display_answer, console=console,
                                            accent=vis.get("accent", "#0d9488")),
                    title=self._title("[accent]Abyssal[/]"),
                    title_align="left", border_style="#0d9488",
                    box=self._box(), padding=(0, 1),
                ))
            if not parts:
                parts.append(Spinner("dots", text=" Waiting for the model…", style="accent"))
            return Group(*parts)

        while True:
            received_any = False
            got_rate_limited = False
            pending_parent = None
            transient_attempt += 1
            try:
                with Live(console=console, refresh_per_second=12, transient=False) as live:
                    last_draw = 0.0

                    def draw(force: bool = False) -> None:
                        nonlocal last_draw
                        now = time.monotonic()
                        if force or now - last_draw >= 0.08:
                            live.update(render())
                            last_draw = now

                    draw(force=True)
                    stream = self.provider.chat_completion(
                        chat_session_id=self.session_id,
                        prompt=prompt,
                        parent_message_id=self.parent_message_id,
                        model_type=self.model,
                        thinking_enabled=self.thinking_enabled,
                        search_enabled=self.search_enabled,
                        ref_file_ids=ref_file_ids or None,
                    )
                    for chunk in stream:
                        ctype = chunk.get("type")
                        if ctype == "thinking":
                            thinking_buf.append(chunk.get("content", ""))
                            received_any = True
                        elif ctype == "search":
                            search_info = chunk
                            received_any = True
                        elif ctype == "text":
                            answer_buf.append(chunk.get("content", ""))
                            received_any = True
                        elif ctype == "meta":
                            pending_parent = chunk.get("response_message_id")
                        draw()
                    draw(force=True)
            except KeyboardInterrupt:
                self._cancelled = True
                console.print("\n[warning]Generation cancelled.[/]")
                answer = "".join(answer_buf)
                if answer.strip() and pending_parent is not None:
                    self.parent_message_id = pending_parent
                return answer or None
            except AuthenticationError:
                console.print("\n[error]Session auth expired. Use /token (DeepSeek) or /provider.[/]")
                return None
            except RateLimitError:
                got_rate_limited = True
            except (NetworkError, APIError) as e:
                if received_any or transient_attempt >= max_transient:
                    console.print(f"\n[error]{e}[/]")
                    return None
                wait = 2 ** transient_attempt
                console.print(
                    f"\n[warning]Transient error — retrying in {wait}s "
                    f"({transient_attempt}/{max_transient})[/]")
                time.sleep(wait)
                continue

            if got_rate_limited:
                if rate_retries < RATE_MAX_RETRIES:
                    rate_retries += 1
                    console.print(
                        f"\n[warning]Rate limit reached [dim](account-wide — switching "
                        f"sessions won't help, we just wait it out)[/] "
                        f"retry {rate_retries}/{RATE_MAX_RETRIES}[/]")
                    self._wait_with_countdown(
                        RATE_RETRY_SECONDS,
                        f"Rate limited ({rate_retries}/{RATE_MAX_RETRIES})")
                    continue
                console.print(Panel(
                    Text(
                        "Still rate limited after 3 retries (15s each). Skipping this "
                        "turn — the limit is account-wide, so resend your message "
                        "manually in a little while.",
                        style="error"),
                    title="[error]Rate limit[/]", title_align="left",
                    border_style="red", box=self._box(), padding=(0, 1)))
                return None

            answer = "".join(answer_buf)
            if not answer.strip():
                if blank_retries < BLANK_MAX_RETRIES:
                    blank_retries += 1
                    console.print(
                        f"\n[warning]Blank response — retrying "
                        f"({blank_retries}/{BLANK_MAX_RETRIES})[/]")
                    self._wait_with_countdown(
                        BLANK_RETRY_SECONDS,
                        f"Blank response ({blank_retries}/{BLANK_MAX_RETRIES})")
                    continue
                console.print(Panel(
                    Text("Ten blank responses in a row — skipping this turn. "
                         "Resend your message to try again.", style="error"),
                    title="[error]Blank response[/]", title_align="left",
                    border_style="red", box=self._box(), padding=(0, 1)))
                return None

            
            if pending_parent is not None:
                self.parent_message_id = pending_parent
            return answer

    
    def stream_response(self, user_prompt: str) -> None:
        if not self.provider:
            return
        if not self.session_id and not self.new_session():
            return
        self._cancelled = False
        codeblocks.stop_click_listener()

        prompt_to_send = self.build_final_prompt(user_prompt)
        prompt_to_send = self._maybe_attach_tools_reminder(prompt_to_send)

        console.print()
        console.print(
            Panel(
                Text(user_prompt, style="user"),
                title=self._title("[user]You[/]"),
                title_align="left", border_style="#115e59",
                box=self._box(), padding=(0, 1),
            )
        )
        self.messages.append({"role": "user", "content": user_prompt, "message_id": None})

        
        file_ids = self.pending_file_ids[:]
        if file_ids:
            console.print(f"[info]Attaching {len(file_ids)} uploaded file(s) to this request.[/]")
        answer = self._stream_once(prompt_to_send, ref_file_ids=file_ids or None)
        if answer is not None:
            consumed = set(file_ids)
            self.pending_file_ids = [
                fid for fid in self.pending_file_ids
                if fid not in consumed
            ]
        elif not self._cancelled:
            play_sound("blank")

        
        iteration = 0
        while answer and not self._cancelled and iteration < MAX_TOOL_ITERATIONS:
            calls = parse_tool_calls(answer)
            mcp_props = parse_json_blocks(MCP_PROPOSAL_RE, answer)
            mcp_edit_props = parse_json_blocks(MCP_EDIT_PROPOSAL_RE, answer)
            sys_props = parse_json_blocks(SYSTEM_PROPOSAL_RE, answer)
            new_reqs = parse_plain_blocks(NEW_SESSION_RE, answer)
            pause_reqs = parse_plain_blocks(NEEDS_INPUT_RE, answer)
            question_reqs = parse_json_blocks(QUESTIONS_RE, answer)

            bad_mcp = max(0, len(MCP_PROPOSAL_RE.findall(answer)) - len(mcp_props))
            bad_mcp_edit = max(0, len(MCP_EDIT_PROPOSAL_RE.findall(answer)) - len(mcp_edit_props))
            bad_sys = max(0, len(SYSTEM_PROPOSAL_RE.findall(answer)) - len(sys_props))
            bad_q = max(0, len(QUESTIONS_RE.findall(answer)) - len(question_reqs))

            disabled_notes: List[str] = []
            if (mcp_props or mcp_edit_props) and not self.agent_settings.get("allow-mcp-proposals"):
                disabled_notes.append(
                    "MCP plugin proposals (create & edit) are disabled "
                    "(/agent allow-mcp-proposals on to enable)."
                )
            if sys_props and not self.agent_settings.get("allow-system-proposals"):
                disabled_notes.append(
                    "System-prompt proposals are disabled "
                    "(/agent allow-system-proposals on to enable)."
                )
            if new_reqs and not self.agent_settings.get("allow-model-new"):
                disabled_notes.append(
                    "New-session requests are disabled "
                    "(/agent allow-model-new on to enable)."
                )
            if pause_reqs and not self.agent_settings.get("allow-model-pause"):
                disabled_notes.append(
                    "Human-input pauses are disabled "
                    "(/agent allow-model-pause on to enable)."
                )
            if question_reqs and not self.agent_settings.get("allow-model-questions"):
                disabled_notes.append(
                    "Structured questions are disabled "
                    "(/agent allow-model-questions on to enable)."
                )

            if (
                not calls
                and not mcp_props
                and not mcp_edit_props
                and not sys_props
                and not new_reqs
                and not pause_reqs
                and not question_reqs
                and not bad_mcp
                and not bad_mcp_edit
                and not bad_sys
                and not bad_q
            ):
                break

            self.messages.append({
                "role": "assistant",
                "content": answer,
                "server_id": self.parent_message_id,
                "message_id": self.parent_message_id,
            })
            followups: List[str] = []

            
            if calls:
                results: List[Tuple[str, bool, str]] = []
                for call in calls:
                    self._show_tool_call(call["name"], call["arguments"])
                    if self.agent_settings.get("confirm-tools"):
                        try:
                            allowed = Confirm.ask(
                                f"[mcp]Run tool[/] [accent]{escape(call['name'])}[/]?",
                                default=True)
                        except (KeyboardInterrupt, EOFError):
                            allowed = False
                        if not allowed:
                            results.append((call["name"], False,
                                            "The user declined to run this tool."))
                            console.print("[mcp]  ↳[/] [warning]declined[/]")
                            continue
                    ok, result = self._execute_tool(call["name"], call["arguments"])
                    self._show_tool_result(call["name"], ok, result)
                    self.messages.append({
                        "role": "tool",
                        "tool": call["name"],
                        "arguments": call["arguments"],
                        "result": result,
                    })
                    results.append((call["name"], ok, result))
                followups.append(self._tool_result_prompt(results))

            
            for prop in mcp_props:
                ok, fb = self._handle_mcp_proposal(prop)
                followups.append(
                    f'[MCP_PROPOSAL_RESULT name="{prop.get("name", "?")}" '
                    f'status="{"accepted" if ok else "not-accepted"}"]\n'
                    f"{fb}\n[/MCP_PROPOSAL_RESULT]"
                )

            
            for prop in mcp_edit_props:
                ok, fb = self._handle_mcp_edit_proposal(prop)
                followups.append(
                    f'[MCP_EDIT_PROPOSAL_RESULT name="{prop.get("name", "?")}" '
                    f'status="{"accepted" if ok else "not-accepted"}"]\n'
                    f"{fb}\n[/MCP_EDIT_PROPOSAL_RESULT]"
                )

            
            for prop in sys_props:
                ok, fb = self._handle_system_proposal(prop)
                followups.append(
                    f'[SYSTEM_PROPOSAL_RESULT status="{"applied" if ok else "not-applied"}"]\n'
                    f"{fb}\n[/SYSTEM_PROPOSAL_RESULT]"
                )

            
            for reason in new_reqs:
                ok, fb = self._handle_new_session_request(reason)
                followups.append(
                    f'[NEW_SESSION_RESULT status="{"granted" if ok else "denied"}"]\n'
                    f"{fb}\n[/NEW_SESSION_RESULT]"
                )

            
            for qdata in question_reqs:
                ok, fb = self._handle_questions(qdata)
                if ok:
                    followups.append(fb)
                else:
                    followups.append(
                        '[QUESTIONS_RESULT status="not-asked"]\n'
                        f"{fb}\n[/QUESTIONS_RESULT]"
                    )

            
            if bad_mcp:
                followups.append(
                    "Your [MCP_PROPOSAL] block was not valid JSON. The body must be a "
                    "single JSON object; put multi-line Python in the \"code\" field "
                    "as a JSON string (escape newlines as \\n)."
                )
            if bad_mcp_edit:
                followups.append(
                    "Your [MCP_EDIT_PROPOSAL] block was not valid JSON. The body must be "
                    "a single JSON object with \"name\", \"reason\", and either \"patch\" "
                    "(preferred) or \"code\" fields. Escape newlines as \\n."
                )
            if bad_sys:
                followups.append(
                    "Your [SYSTEM_PROPOSAL] block was not valid JSON. The body must be "
                    "a single JSON object with \"reason\" and \"prompt\" fields."
                )
            if bad_q:
                followups.append(
                    "Your [QUESTIONS] block was not valid JSON. The body must be a single "
                    "JSON object: {\"questions\": [{\"text\": \"...\", \"choices\": [...], "
                    "\"blocking\": true, \"default\": \"...\"}, ...]}."
                )
            if disabled_notes:
                followups.append("\n".join(disabled_notes))

            iteration += 1
            if self._exit_requested:
                self._save_transcript()
                return

            
            if pause_reqs:
                prompt_next = self._handle_needs_input(pause_reqs[0], "\n".join(followups))
            elif followups:
                prompt_next = "\n".join(followups)
            else:
                break

            if not self.session_id and not self.new_session(quiet=True):
                break

            prompt_next = self.build_final_prompt(prompt_next)
            next_file_ids = self.pending_file_ids[:]
            if next_file_ids:
                console.print(
                    f"[info]Attaching {len(next_file_ids)} uploaded file(s) to the next request.[/]"
                )
            answer = self._stream_once(prompt_next, ref_file_ids=next_file_ids or None)
            if answer is not None:
                consumed = set(next_file_ids)
                self.pending_file_ids = [
                    fid for fid in self.pending_file_ids
                    if fid not in consumed
                ]
            elif not self._cancelled:
                play_sound("blank")

        if answer:
            self.messages.append({
                "role": "assistant",
                "content": answer,
                "server_id": self.parent_message_id,
                "message_id": self.parent_message_id,
            })
        if not self.session_title:
            self.session_title = user_prompt[:48]
        self._save_transcript()
        if answer and not self._cancelled:
            play_sound("response")
            codeblocks.arm_click_listener(console)
        console.print()