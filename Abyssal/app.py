from __future__ import annotations

import argparse
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle

from . import __version__
from . import aps_guide, codeblocks, consent
from .agent_actions import AgentMixin
from .chat import ChatMixin
from .commands import CommandsMixin
from .completion import CommandCompleter
from .config import APP_NAME, HISTORY_FILE
from .core import BaseCLI
from .cowork import TaskScheduler, load_tasks
from .files import FileCommandsMixin
from .mcp import MCP_AVAILABLE
from .task_commands import TaskCommandsMixin
from .ui import console
from .updater import check_on_startup


class AbyssalCLI(
    FileCommandsMixin,
    TaskCommandsMixin,
    CommandsMixin,
    AgentMixin,
    ChatMixin,
    BaseCLI,
):
    

    def run(self) -> None:
        self.print_banner()

        
        check_on_startup(console, __version__)

        if not self.authenticate():
            sys.exit(1)

        if MCP_AVAILABLE and self.mcp.list_servers():
            try:
                with console.status("[mcp]Loading MCP tools…[/]", spinner="dots"):
                    self._mcp_loop.run_until_complete(self.mcp.refresh_tools())
                console.print(f"[mcp]✓[/] {len(self.mcp.tools)} MCP tools ready")
            except Exception:
                pass

        
        self.taskman = TaskScheduler(mcp=self.mcp)
        self.taskman.start()
        console.print(
            f"[dim]Cowork scheduler started — {len(load_tasks())} task(s) on file, "
            f"checking every {TaskScheduler.CHECK_INTERVAL}s[/]"
        )

        
        sounds_cfg = self.cfg.get("sounds") or {}
        if not sounds_cfg.get("master") and not self.cfg.get("_sounds_notice_shown"):
            console.print(
                "[dim]Sounds are disabled by default — enable them with "
                "[accent]/sounds master on[/][/]")
            self.cfg["_sounds_notice_shown"] = True
            from .config import save_config
            save_config(self.cfg)

        if self._resume_target:
            self._apply_session(self._resume_target)
            console.print(f"[success]✓[/] Resumed session [accent]{self._resume_target[:12]}…[/]")
        else:
            self.new_session(quiet=True)

        
        
        self.prompt_session = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            completer=CommandCompleter(self),
            style=PTStyle.from_dict({
                "prompt": "#0d9488 bold",
                "input": "#ffffff",
            }),
            key_bindings=self.kb,
            multiline=True,
            mouse_support=False,
        )

        self.print_status()
        console.print(
            "[dim]Type /help for every command · /thinking · /search · /exit quits[/]\n")

        while True:
            try:
                
                codeblocks.stop_click_listener()
                default_text = getattr(self, "_next_prompt_default", "")
                if default_text:
                    self._next_prompt_default = ""
                    user_input = self.prompt_session.prompt(
                        HTML("<ansicyan><b>›</b></ansicyan> "),
                        default=default_text,
                    ).strip()
                else:
                    user_input = self.prompt_session.prompt(
                        HTML("<ansicyan><b>›</b></ansicyan> ")
                    ).strip()
                if not user_input:
                    continue
                if user_input.startswith("/"):
                    if not self.handle_command(user_input):
                        break
                    if self._exit_requested:
                        break
                    continue
                self.stream_response(user_input)
                if self._exit_requested:
                    break
            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted — type /exit to quit.[/]")
                continue
            except EOFError:
                console.print("\n[dim]Goodbye.[/]")
                break

        
        try:
            self._mcp_loop.close()
        finally:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="abyssal",
        description=f"{APP_NAME} — official-grade terminal client",
    )
    parser.add_argument("--token", "-t", help="Auth token (saved to .env)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--thinking", action="store_true", help="Start with thinking enabled")
    parser.add_argument("--search", "--websearch", action="store_true", help="Start with web search enabled")
    parser.add_argument("--model", "-m", help="Model type (default / expert / vision)")
    parser.add_argument("--session", "-s", help="Resume a specific session ID")
    parser.add_argument("--version", "-v", action="version", version=f"{APP_NAME} {__version__}")
    args = parser.parse_args()

    cli = AbyssalCLI(
        token=args.token,
        debug=args.debug,
        model=args.model,
        resume_session=args.session,
    )
    if args.thinking:
        cli.thinking_enabled = True
    if args.search:
        cli.search_enabled = True
    try:
        cli.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[bold red]Fatal: {e}[/]")
        if args.debug:
            console.print_exception()
        sys.exit(1)