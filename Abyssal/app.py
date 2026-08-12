from __future__ import annotations
_A=True
import argparse,asyncio,sys
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle
from.import __version__
from.agent_actions import AgentMixin
from.chat import ChatMixin
from.commands import CommandsMixin
from.completion import CommandCompleter
from.config import APP_NAME,HISTORY_FILE
from.core import BaseCLI
from.cowork import TaskScheduler,load_tasks
from.files import FileCommandsMixin
from.mcp import MCP_AVAILABLE
from.task_commands import TaskCommandsMixin
from.ui import console
class AbyssalCLI(FileCommandsMixin,TaskCommandsMixin,CommandsMixin,AgentMixin,ChatMixin,BaseCLI):
	def run(A):
		D='<ansicyan><b>›</b></ansicyan> ';A.print_banner()
		if not A.authenticate():sys.exit(1)
		if MCP_AVAILABLE and A.mcp.list_servers():
			try:
				with console.status('[mcp]Loading MCP tools…[/]',spinner='dots'):asyncio.run(A.mcp.refresh_tools())
				console.print(f"[mcp]✓[/] {len(A.mcp.tools)} MCP tools ready")
			except Exception:pass
		A.taskman=TaskScheduler(mcp=A.mcp);A.taskman.start();console.print(f"[dim]Cowork scheduler started — {len(load_tasks())} task(s) on file, checking every {TaskScheduler.CHECK_INTERVAL}s[/]")
		if A._resume_target:A._apply_session(A._resume_target);console.print(f"[success]✓[/] Resumed session [accent]{A._resume_target[:12]}…[/]")
		else:A.new_session(quiet=_A)
		A.prompt_session=PromptSession(history=FileHistory(str(HISTORY_FILE)),auto_suggest=AutoSuggestFromHistory(),completer=CommandCompleter(A),style=PTStyle.from_dict({'prompt':'#0d9488 bold','input':'#ffffff'}),key_bindings=A.kb,multiline=_A,mouse_support=_A);A.print_status();console.print('[dim]Type /settings for the menu · /thinking · /search · /exit quits[/]\n')
		while _A:
			try:
				C=getattr(A,'_next_prompt_default','')
				if C:A._next_prompt_default='';B=A.prompt_session.prompt(HTML(D),default=C).strip()
				else:B=A.prompt_session.prompt(HTML(D)).strip()
				if not B:continue
				if B.startswith('/'):
					if not A.handle_command(B):break
					if A._exit_requested:break
					continue
				A.stream_response(B)
				if A._exit_requested:break
			except KeyboardInterrupt:console.print('\n[dim]Interrupted — type /exit to quit.[/]');continue
			except EOFError:console.print('\n[dim]Goodbye.[/]');break
def main():
	D='store_true';A=argparse.ArgumentParser(prog='abyssal',description=f"{APP_NAME} — official-grade terminal client");A.add_argument('--token','-t',help='Auth token (saved to .env)');A.add_argument('--debug',action=D,help='Enable debug logging');A.add_argument('--thinking',action=D,help='Start with thinking enabled');A.add_argument('--search','--websearch',action=D,help='Start with web search enabled');A.add_argument('--model','-m',help='Model type (default / expert / custom)');A.add_argument('--session','-s',help='Resume a specific session ID');A.add_argument('--version','-v',action='version',version=f"{APP_NAME} {__version__}");B=A.parse_args();C=AbyssalCLI(token=B.token,debug=B.debug,model=B.model,resume_session=B.session)
	if B.thinking:C.thinking_enabled=_A
	if B.search:C.search_enabled=_A
	try:C.run()
	except KeyboardInterrupt:pass
	except Exception as E:
		console.print(f"[bold red]Fatal: {E}[/]")
		if B.debug:console.print_exception()
		sys.exit(1)